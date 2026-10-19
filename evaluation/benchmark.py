"""Benchmark pathology foundation models for colorectal tissue classification and train the app's linear head.

For each backbone:
  1. extract frozen features of a class-balanced NCT-CRC-HE-100K sample (Macenko-normalised + original NONORM
     colours), plus one stain/flip-augmented copy of every training image;
  2. train a multinomial logistic-regression head (weight decay picked on a 15% validation split), then fit a
     temperature on the validation split;
  3. test on ALL of CRC-VAL-HE-7K (7,180 images, 50 patients never seen in training);
  4. run the same robustness conditions as the original MedVisionAI `robustness.py` (same 200 images per class,
     same seeds, same scikit-image HED perturbation) so results compare directly with the ConvNeXt v3 model.

Usage:
  python evaluation/benchmark.py --train data/nct_train_*.parquet --test data/CRC-VAL-HE-7K \
         --backbones phikon lunit_vits8 --out reports
Writes reports/benchmark_<backbone>.json and models/crc_head_<backbone>.pt.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from glob import glob

import numpy as np
import torch
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from medvision.classifier.foundation import (BACKBONES, CLASS_NAMES, CODES, TUMOR_INDEX,  # noqa: E402
                                             LinearHead, load_backbone)

RGB_FROM_HED = np.array([[0.65, 0.70, 0.29], [0.07, 0.99, 0.11], [0.27, 0.57, 0.78]])
HED_FROM_RGB = np.linalg.inv(RGB_FROM_HED)


# ----------------------------------------------------------------------------- data
def load_train(paths):
    import pyarrow.parquet as pq
    imgs, ys = [], []
    for p in paths:
        t = pq.read_table(p)
        for d, y in zip(t.column("image").to_pylist(), t.column("label").to_pylist()):
            imgs.append(Image.open(io.BytesIO(d["bytes"])).convert("RGB"))
            ys.append(int(y))
        print(f"loaded {p}: {t.num_rows} images", flush=True)
    return imgs, np.array(ys)


def train_augment(im, rng):
    """Stain jitter (numpy HED, a different implementation from the scikit-image test perturbation) + flips."""
    arr = np.asarray(im, dtype=np.float32) / 255
    od = -np.log(np.clip(arr, 1e-6, 1))
    s = rng.uniform(0.0, 0.2)
    hed = od.reshape(-1, 3) @ HED_FROM_RGB
    hed = hed * rng.uniform(1 - s, 1 + s, 3) + rng.uniform(-s, s, 3) * 0.1
    out = Image.fromarray((np.clip(np.exp(-(hed @ RGB_FROM_HED)).reshape(arr.shape), 0, 1) * 255).astype(np.uint8))
    if rng.random() < 0.5:
        out = out.transpose(Image.FLIP_LEFT_RIGHT)
    return out.rotate(90 * int(rng.integers(4)))


def jpeg(im, q):
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=q)
    return Image.open(io.BytesIO(buf.getvalue())).convert("RGB")


def hed_jitter(img, rng, sigma, bias):     # identical to the original robustness.py (scikit-image)
    from skimage.color import hed2rgb, rgb2hed
    hed = rgb2hed(np.asarray(img.convert("RGB")) / 255.0)
    a = rng.uniform(1 - sigma, 1 + sigma, 3)
    b = rng.uniform(-bias, bias, 3)
    return Image.fromarray((np.clip(hed2rgb(hed * a + b), 0, 1) * 255).astype(np.uint8))


CONDITIONS = {
    "stain shift, mild": lambda im, r: hed_jitter(im, r, 0.05, 0.05),
    "stain shift, strong": lambda im, r: hed_jitter(im, r, 0.15, 0.15),
    "JPEG quality 40": lambda im, r: jpeg(im, 40),
    "blur": lambda im, r: im.filter(ImageFilter.GaussianBlur(1.5)),
    "web-like (mild shift + downscale + JPEG 60)": lambda im, r: jpeg(
        hed_jitter(im, r, 0.05, 0.05).resize((150, 150), Image.BILINEAR).resize(im.size, Image.BILINEAR), 60),
}


def load_test(folder):
    files, ys = [], []
    for k, code in enumerate(CODES):
        fs = sorted(glob(os.path.join(folder, code, "*.tif")))
        files += fs
        ys += [k] * len(fs)
    return files, np.array(ys)


def robustness_subset(folder, per_class=200, seed=0):
    """Same images as the original robustness.py (same sampling code and seed)."""
    rng = np.random.default_rng(seed)
    files, ys = [], []
    for k, code in enumerate(CODES):
        fs = sorted(glob(os.path.join(folder, code, "*.tif")))
        fs = [fs[i] for i in sorted(rng.choice(len(fs), size=min(per_class, len(fs)), replace=False))]
        files += fs
        ys += [k] * len(fs)
    return files, np.array(ys)


# ----------------------------------------------------------------------------- features & head
@torch.inference_mode()
def extract(model, transform, images, batch=64, label=""):
    out, t0 = [], time.time()
    for i in range(0, len(images), batch):
        chunk = [im if isinstance(im, Image.Image) else Image.open(im).convert("RGB") for im in images[i:i + batch]]
        out.append(model(torch.stack([transform(im) for im in chunk])))
        if (i // batch) % 20 == 0:
            done = i + len(chunk)
            print(f"  {label} {done}/{len(images)} ({done / (time.time() - t0):.1f} img/s)", flush=True)
    return torch.cat(out).float()


def fit_head(Xtr, ytr, Xva, yva, n_classes=9):
    mean, std = Xtr.mean(0), Xtr.std(0) + 1e-6
    best = None
    for wd in (1e-4, 1e-3, 1e-2, 1e-1):
        head = LinearHead(Xtr.shape[1], n_classes)
        head.mean.copy_(mean)
        head.std.copy_(std)
        opt = torch.optim.LBFGS(head.fc.parameters(), lr=1, max_iter=500, history_size=20,
                                line_search_fn="strong_wolfe")
        yt = torch.as_tensor(ytr)

        def closure():
            opt.zero_grad()
            loss = torch.nn.functional.cross_entropy(head(Xtr), yt) + wd * head.fc.weight.pow(2).sum()
            loss.backward()
            return loss
        opt.step(closure)
        with torch.no_grad():
            acc = (head(Xva).argmax(1).numpy() == yva).mean()
        print(f"  weight decay {wd:g}: validation accuracy {acc:.4f}", flush=True)
        if best is None or acc > best[0]:
            best = (acc, wd, head)
    acc, wd, head = best
    # temperature scaling on the validation split
    with torch.no_grad():
        logits = head.fc((Xva - head.mean) / head.std)
    t = torch.zeros((), requires_grad=True)
    opt = torch.optim.LBFGS([t], lr=0.1, max_iter=200, line_search_fn="strong_wolfe")
    yv = torch.as_tensor(yva)

    def tclosure():
        opt.zero_grad()
        loss = torch.nn.functional.cross_entropy(logits / t.exp(), yv)
        loss.backward()
        return loss
    opt.step(tclosure)
    head.temperature.fill_(float(t.exp()))
    return head, {"weight_decay": wd, "val_accuracy": float(acc), "temperature": float(head.temperature)}


def metrics(probs, y):
    pred = probs.argmax(1)
    k = len(CLASS_NAMES)
    cm = np.zeros((k, k), int)
    for a, b in zip(y, pred):
        cm[a, b] += 1
    recall = cm.diagonal() / np.maximum(cm.sum(1), 1)
    precision = cm.diagonal() / np.maximum(cm.sum(0), 1)
    f1 = 2 * precision * recall / np.maximum(precision + recall, 1e-9)
    # tumour AUROC (rank-based, one-vs-rest)
    s, pos = probs[:, TUMOR_INDEX], y == TUMOR_INDEX
    order = s.argsort()
    ranks = np.empty(len(s))
    ranks[order] = np.arange(1, len(s) + 1)
    auc = (ranks[pos].sum() - pos.sum() * (pos.sum() + 1) / 2) / (pos.sum() * (~pos).sum())
    return {"accuracy_9class": float((pred == y).mean()), "macro_f1_9class": float(f1.mean()),
            "balanced_accuracy": float(recall.mean()), "tumor_recall": float(recall[TUMOR_INDEX]),
            "tumor_precision": float(precision[TUMOR_INDEX]), "tumor_auroc": float(auc),
            "per_class_recall": {CLASS_NAMES[i]: round(float(r), 4) for i, r in enumerate(recall)},
            "confusion_matrix": cm.tolist()}


def short(m):
    return {k: round(v, 4) for k, v in m.items() if isinstance(v, float)}



# ----------------------------------------------------------------------------- main
def cached(cache, name, fn):
    path = os.path.join(cache, name + ".npy")
    if os.path.isfile(path):
        return torch.from_numpy(np.load(path))
    out = fn()
    np.save(path, out.numpy())
    return out


def subsample(y, per_class, rng):
    if not per_class:
        return np.arange(len(y))
    return np.sort(np.concatenate([rng.choice(np.flatnonzero(y == k), size=min(per_class, int((y == k).sum())),
                                              replace=False) for k in np.unique(y)]))


def v3_baseline(path, versions, y):
    """The previous MedVisionAI colorectal model (ConvNeXt-Tiny, 64 px) on exactly the same images."""
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(path))))
    from medvision_modules import LoadedModel
    lm = LoadedModel.from_path("crc", "multiclass", path)
    res = {}
    for c, ims in versions.items():
        p = np.concatenate([lm.probs_batch(ims[i:i + 128]) for i in range(0, len(ims), 128)])
        m = metrics(p, y)
        res[c] = {k: round(m[k], 4) for k in ("accuracy_9class", "macro_f1_9class", "tumor_recall",
                                             "tumor_precision", "tumor_auroc")}
        print("v3", c, res[c], flush=True)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", nargs="+", required=True)
    ap.add_argument("--test", required=True)
    ap.add_argument("--backbones", nargs="*", default=["phikon"])
    ap.add_argument("--train-per-class", type=int, default=0, help="per class AND stain-variant file; 0 = all")
    ap.add_argument("--aug-frac", type=float, default=0.33, help="share of training images also used augmented")
    ap.add_argument("--test-per-class", type=int, default=100, help="CRC-VAL-HE-7K images per class (seed 0)")
    ap.add_argument("--v3", help="path to model_v3_convnext_tiny_stainrobust.pt for the baseline")
    ap.add_argument("--cache", default=os.path.join(ROOT, "evaluation", ".cache"))
    ap.add_argument("--out", default=os.path.join(ROOT, "reports"))
    a = ap.parse_args()
    torch.manual_seed(0)
    os.makedirs(a.out, exist_ok=True)
    os.makedirs(a.cache, exist_ok=True)
    rng = np.random.default_rng(0)

    paths = sorted(set(sum((glob(p) for p in a.train), [])))
    imgs, ys = [], []
    for p in paths:                                   # balanced per class within each stain variant
        im, y = load_train([p])
        keep = subsample(y, a.train_per_class, rng)
        imgs += [im[i] for i in keep]
        ys.append(y[keep])
    train_imgs, ytrain = imgs, np.concatenate(ys)
    aug_idx = subsample(ytrain, int(a.aug_frac * len(ytrain) / 9), rng)
    aug_imgs = [train_augment(train_imgs[i], rng) for i in aug_idx]
    perm = rng.permutation(len(train_imgs))
    n_val = int(0.15 * len(perm))
    val_idx, tr_idx = perm[:n_val], perm[n_val:]
    aug_keep = np.isin(aug_idx, tr_idx)              # augmented copies of validation images are not used

    test_files, ytest = robustness_subset(a.test, a.test_per_class)
    test_imgs = [Image.open(f).convert("RGB") for f in test_files]
    versions = {"original": test_imgs}
    for c, fn in CONDITIONS.items():
        r = np.random.default_rng(1)
        versions[c] = [fn(im, r) for im in test_imgs]
    tag = f"tr{a.train_per_class}_aug{a.aug_frac}_te{a.test_per_class}"
    print(f"train {len(train_imgs)} + {int(aug_keep.sum())} augmented, validation {n_val}, "
          f"test {len(test_imgs)} x {len(versions)} conditions", flush=True)

    comparison_path = os.path.join(a.out, "model_comparison.json")
    comparison = json.load(open(comparison_path)) if os.path.isfile(comparison_path) else {}
    comparison["setup"] = {
        "test_data": f"CRC-VAL-HE-7K (50 patients not in training), {a.test_per_class} images per class, seed 0, "
                     "same sampling code as the original robustness.py",
        "conditions": ["original"] + list(CONDITIONS),
        "training_data": f"NCT-CRC-HE-100K sample: {len(train_imgs)} images ({a.train_per_class or 'all'} per class "
                         f"per stain variant, normalised + original colours) + {int(aug_keep.sum())} stain/flip "
                         "augmented copies; 15% held out for validation"}
    if a.v3:
        comparison["ConvNeXt-Tiny v3 (previous MedVisionAI model)"] = {
            "params_millions": 28, "input": "64 px", "results": v3_baseline(a.v3, versions, ytest)}
        json.dump(comparison, open(comparison_path, "w"), indent=1)

    for key in a.backbones:
        spec = BACKBONES[key]
        print(f"\n=== {spec.title} ===", flush=True)
        t0 = time.time()
        model, transform = load_backbone(key)
        F_train = cached(a.cache, f"{key}_train_{tag}", lambda: extract(model, transform, train_imgs, label="train"))
        F_aug = cached(a.cache, f"{key}_aug_{tag}", lambda: extract(model, transform, aug_imgs, label="train-aug"))
        Xtr = torch.cat([F_train[tr_idx], F_aug[aug_keep]])
        ytr = np.concatenate([ytrain[tr_idx], ytrain[aug_idx[aug_keep]]])
        head, fit = fit_head(Xtr, ytr, F_train[val_idx], ytrain[val_idx])
        res, full = {}, None
        for c, ims in versions.items():
            name = "".join(ch if ch.isalnum() else "_" for ch in c)[:24]
            feats = cached(a.cache, f"{key}_test_{name}_{tag}", lambda: extract(model, transform, ims, label=c))
            with torch.no_grad():
                p = torch.softmax(head(feats), 1).numpy()
            m = metrics(p, ytest)
            full = full or m
            res[c] = {k: round(m[k], 4) for k in ("accuracy_9class", "macro_f1_9class", "tumor_recall",
                                                 "tumor_precision", "tumor_auroc")}
            print(key, c, res[c], flush=True)
        comparison[spec.title] = {"params_millions": spec.params_m, "input": "224 px", "licence": spec.licence,
                                  "head_fit": fit, "results": res}
        json.dump(comparison, open(comparison_path, "w"), indent=1)
        report = {"backbone": spec.title, "hub_id": spec.hub_id, "params_millions": spec.params_m,
                  "licence": spec.licence, "pretraining": spec.pretraining,
                  "training": {"data": comparison["setup"]["training_data"], **fit},
                  "test_original": {"n": int(len(ytest)), **full}, "robustness": res,
                  "seconds": round(time.time() - t0)}
        json.dump(report, open(os.path.join(a.out, f"benchmark_{key}.json"), "w"), indent=1)
        torch.save({"backbone": key, "head": head.state_dict(), "class_names": CLASS_NAMES, "codes": CODES,
                    "meta": {"backbone": spec.title, "hub_id": spec.hub_id, "licence": spec.licence,
                             "pretraining": spec.pretraining, "training": report["training"],
                             "test": {k: round(v, 4) for k, v in full.items() if isinstance(v, float)},
                             "test_setup": comparison["setup"]["test_data"], "robustness": res}},
                   os.path.join(ROOT, "models", f"crc_head_{key}.pt"))
        print(f"saved head and report for {key} ({report['seconds']} s)", flush=True)


if __name__ == "__main__":
    main()
