"""medvision_modules.py: one interface for every MedVisionAI module (colorectal tissue, lymph node metastasis).

Each module is a ConvNeXt/ResNet/EfficientNet classifier. This file loads the checkpoint, predicts,
draws a Grad-CAM heatmap and runs a simple "hide the evidence" stress test. It is not a medical device.
Research prototype only. Not for clinical use.
"""
import json
import os

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from torchvision import models

import medvision_infer as mvi


def _multiclass_model(arch, n_classes):
    if arch == "convnext_tiny":
        m = models.convnext_tiny(weights=None)
        m.classifier[2] = nn.Linear(m.classifier[2].in_features, n_classes)
    elif arch == "resnet50":
        m = models.resnet50(weights=None)
        m.fc = nn.Linear(m.fc.in_features, n_classes)
    else:
        raise mvi.InferenceError(f"Unsupported architecture in checkpoint: {arch}")
    return m


class LoadedModel:
    """A trained module ready for prediction and explanation."""

    def __init__(self, key, model, arch, size, names, tumor_index, threshold, meta, source, results=None):
        self.key, self.arch, self.size = key, arch, int(size)
        self.names, self.tumor_index, self.threshold = list(names), int(tumor_index), threshold
        self.meta, self.source, self.results = meta or {}, source, results or {}
        self.model = model.to("cpu").eval()
        self.transform = mvi.eval_transform(self.size)

    # ---- loading
    @classmethod
    def from_path(cls, key, kind, path, results_path=None):
        if not os.path.isfile(path):
            raise mvi.InferenceError(f"Checkpoint file not found: {path}")
        try:
            ck = torch.load(path, map_location="cpu", weights_only=True)
        except Exception as e:
            raise mvi.InferenceError(f"Could not read checkpoint '{path}': {e}") from e
        results = {}
        if results_path and os.path.isfile(results_path):
            try:
                results = json.load(open(results_path))
            except Exception:
                results = {}
        if kind == "binary":                         # written by the PCam notebook (medvision_infer.save_checkpoint)
            if "state_dict" not in ck:
                raise mvi.InferenceError("This file is not a binary-module checkpoint.")
            model = mvi.build_model(ck["arch"], pretrained=False)
            sd = {k: (v.float() if v.is_floating_point() else v) for k, v in ck["state_dict"].items()}
            model.load_state_dict(sd)
            names = list(ck["class_names"])
            return cls(key, model, ck["arch"], ck["img_size"], names, int(ck["cancer_index"]),
                       float(ck["threshold"]), ck.get("meta", {}), os.path.abspath(path), results)
        if kind == "multiclass":                     # written by train_v2.py
            if "state" not in ck:
                raise mvi.InferenceError("This file is not a multi-class checkpoint.")
            names = list(ck["names"])
            model = _multiclass_model(ck["arch"], len(names))
            sd = {k: (v.float() if v.is_floating_point() else v) for k, v in ck["state"].items()}
            try:
                model.load_state_dict(sd)
            except RuntimeError as e:
                raise mvi.InferenceError(f"Checkpoint weights do not match the architecture: {e}") from e
            tumor = [i for i, n in enumerate(names) if "adenocarcinoma" in n.lower()]
            if not tumor:
                raise mvi.InferenceError("No tumor class found in the class names.")
            return cls(key, model, ck["arch"], ck["size"], names, tumor[0], None, {}, os.path.abspath(path), results)
        raise ValueError(f"Unknown module kind: {kind}")

    @classmethod
    def from_hub(cls, key, kind, repo_id, filename, results_path=None):
        try:
            from huggingface_hub import hf_hub_download
        except ImportError as e:
            raise mvi.InferenceError("Install huggingface_hub: pip install huggingface_hub") from e
        try:
            path = hf_hub_download(repo_id=repo_id, filename=filename)
        except Exception as e:
            raise mvi.InferenceError(f"Could not download '{filename}' from '{repo_id}': {e}") from e
        obj = cls.from_path(key, kind, path, results_path)
        obj.source = f"hf://{repo_id}/{filename}"
        return obj

    # ---- prediction helpers
    @torch.no_grad()
    def probs_batch(self, imgs):
        x = torch.stack([self.transform(i) for i in imgs])
        return torch.softmax(self.model(x).float(), 1).numpy()

    def decide(self, probs):
        """Predicted class index. Binary modules use the validation-chosen threshold, multi-class use argmax."""
        if self.threshold is not None:
            return self.tumor_index if probs[self.tumor_index] >= self.threshold else 1 - self.tumor_index
        return int(np.argmax(probs))

    def cam(self, img, class_index):
        engine = mvi.GradCAM(self.model, mvi.gradcam_layer(self.model, self.arch))
        try:
            cam, _ = engine(self.transform(img).unsqueeze(0), class_index=class_index)
        finally:
            engine.remove()
        return cam[0]

    def _upsample(self, cam):
        t = torch.from_numpy(np.ascontiguousarray(cam))[None, None].float()
        return F.interpolate(t, size=(self.size, self.size), mode="bilinear", align_corners=False)[0, 0].numpy()

    @staticmethod
    def _fill(img_arr, mask):
        out = img_arr.copy()
        out[mask] = img_arr.reshape(-1, 3).mean(0).astype(np.uint8)    # neutral average colour
        return Image.fromarray(out)

    # ---- full analysis used by the app
    def analyze(self, source, area=0.25, n_random=6, seed=0):
        img = mvi.load_image(source)
        probs = self.probs_batch([img])[0]
        pred = self.decide(probs)
        cam = self.cam(img, pred)
        up = self._upsample(cam)
        base = np.asarray(img.resize((self.size, self.size)))

        # stress test: hide the area the heatmap points at, and compare with hiding random areas of equal size
        masked_img, hidden = None, None
        if up.max() > 0:
            mask = up >= np.quantile(up, 1 - area)
            masked_img = self._fill(base, mask)
            hidden = self.probs_batch([masked_img])[0]
        rng = np.random.default_rng(seed)
        side = max(2, int(round(self.size * np.sqrt(area))))
        randoms = []
        for _ in range(n_random):
            y, x = rng.integers(0, self.size - side + 1, 2)
            m = np.zeros((self.size, self.size), dtype=bool)
            m[y:y + side, x:x + side] = True
            randoms.append(self._fill(base, m))
        rand_probs = self.probs_batch(randoms) if randoms else None

        weights = up / up.sum() if up.sum() > 0 else None
        if weights is not None:
            ys, xs = np.mgrid[0:self.size, 0:self.size]
            cy, cx = float((weights * ys).sum() / self.size), float((weights * xs).sum() / self.size)
        else:
            cy = cx = 0.5
        return {
            "image": img, "overlay": mvi.overlay_heatmap(img, cam), "probs": probs, "pred": pred,
            "hidden_probs": hidden, "hidden_image": masked_img,
            "random_probs": rand_probs, "cam_center": (cy, cx), "area": area,
        }
