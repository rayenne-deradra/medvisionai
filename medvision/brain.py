"""Brain tumour MRI analysis (BRISC 2025): CNN classification, U-Net lesion segmentation, classical radiomics and a
0-100 triage risk score.

Models (braintumor/models):
  cnn_classifier.pt      5-fold EfficientNet-B0 ensemble (test accuracy 99.3%, 1,000 BRISC test slices)
  cnn_*.pt               single EfficientNet-B0, ConvNeXt-Tiny and ResNet-18 backbones, compared on every image
  seg_unet_small.pt      256 x 256 U-Net for the lesion mask (horizontal-flip test-time augmentation)
  *.joblib               classical tumour / no-tumour classifiers on 7 engineered image features

Research prototype only. Not a medical device. Not for diagnosis.
"""
from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

from .config import BRAIN_DIR

MODELS_DIR = BRAIN_DIR / "models"
SAMPLES_DIR = BRAIN_DIR / "samples"
REPORTS_DIR = BRAIN_DIR / "reports"
GRAPHS_DIR = BRAIN_DIR / "graphs"

CLASS_LABELS = ["glioma", "meningioma", "pituitary", "no_tumor"]
CLASS_NAMES = {"glioma": "Glioma", "meningioma": "Meningioma", "pituitary": "Pituitary tumour", "no_tumor": "No tumour"}
PLANE_CODES = {"unknown": 0, "axial": 1, "coronal": 2, "sagittal": 3}
CLASS_RISK_WEIGHTS = {"no_tumor": 0, "meningioma": 12, "pituitary": 18, "glioma": 25}
BACKBONES = {   # key -> (title, checkpoint)
    "ensemble": ("EfficientNet-B0 · 5-fold ensemble", "cnn_classifier.pt"),
    "efficientnet_b0": ("EfficientNet-B0 · single", "cnn_efficientnet_b0.pt"),
    "convnext_tiny": ("ConvNeXt-Tiny", "cnn_convnext_tiny.pt"),
    "resnet18": ("ResNet-18", "cnn_resnet18.pt"),
}
CLASSICAL_MODELS = {
    "Random Forest": "best_classical_model.joblib",
    "Random Forest (tuned)": "best_classical_model_tuned_best.joblib",
    "Gradient Boosting": "gradient_boosting.joblib",
    "SVM": "svm.joblib",
    "Decision Tree": "decision_tree.joblib",
    "Logistic Regression": "logistic_regression.joblib",
}
FINDING_NO_TUMOR = "No brain tumour detected"
FINDING_NOT_ASSESSED = "Not assessed"


class BrainModelError(RuntimeError):
    """Readable problem loading or running the brain MRI models."""


@dataclass
class BrainSettings:
    backbone: str = "ensemble"          # model whose prediction is reported; all four are always compared
    plane: str = "auto"                 # "auto" | "axial" | "coronal" | "sagittal"
    threshold: float = 0.35             # U-Net probability threshold for the lesion mask
    use_tta: bool = True                # horizontal-flip test-time augmentation for the classifiers
    force_out_of_scope: bool = False    # run the models even on images that do not look like an MRI slice


@dataclass
class BrainResult:
    report: dict
    images: dict[str, np.ndarray]       # original, overlay, probability, saliency (RGB uint8)


# ----------------------------------------------------------------------------- image checks and features
def assess_mri_input(img: Image.Image) -> dict:
    """Brain MRI slices are grayscale. A clearly coloured image (an H&E slide, a photo) is out of scope."""
    small = img.convert("RGB")
    small.thumbnail((256, 256))
    rgb = np.asarray(small, dtype=np.float32) / 255.0
    colourfulness = float((rgb.max(-1) - rgb.min(-1)).mean())
    warnings: list[str] = []
    if colourfulness > 0.08:
        image_type, applicable = "colour image", False
        warnings.append("The image is in colour, but brain MRI slices are grayscale. It may be a histology slide "
                        "or a photograph: use Colorectal tissue analysis for H&E images.")
    else:
        image_type, applicable = "grayscale MRI-like", True
        if colourfulness > 0.03:
            warnings.append("The image has some colour (annotations or a tinted export); results may be less reliable.")
    if min(img.size) < 128:
        warnings.append("The image is small (under 128 px), so detail is limited.")
    return {"image_type": image_type, "applicable": applicable, "colourfulness": round(colourfulness, 3),
            "warnings": warnings}


def parse_plane(filename: str, selected: str) -> str:
    if selected and selected != "auto":
        return selected
    tokens = [t for t in Path(filename).stem.lower().replace("-", "_").split("_") if t]
    for plane, names in (("axial", {"axial", "ax"}), ("coronal", {"coronal", "cor", "co"}),
                         ("sagittal", {"sagittal", "sag", "sa"})):
        if any(t in names for t in tokens):
            return plane
    return "axial"          # most BRISC slices are axial; the page shows the assumption


def _normalize(value: float, bounds: list[float]) -> float:
    lo, hi = bounds
    return 0.0 if hi <= lo else float(np.clip((value - lo) / (hi - lo), 0.0, 1.0))


def _shannon_entropy(gray: np.ndarray) -> float:
    hist = np.bincount(gray.ravel(), minlength=256).astype(np.float64)
    p = hist[hist > 0] / max(hist.sum(), 1.0)
    return float(-(p * np.log2(p)).sum())


# ----------------------------------------------------------------------------- engine
class BrainEngine:
    """Loads every brain model once (a few hundred MB of weights, CPU is enough)."""

    def __init__(self) -> None:
        try:
            import cv2  # noqa: F401  (fail early with a readable message)
            import joblib
            import torch
        except ImportError as e:
            raise BrainModelError(f"A package for brain MRI analysis is missing ({e.name}). "
                                  "Run: pip install -r requirements.txt") from e
        if not (MODELS_DIR / "cnn_classifier.pt").exists():
            raise BrainModelError(f"Brain MRI models not found in {MODELS_DIR}.")
        self.torch = torch
        self.ranges = json.loads((BRAIN_DIR / "feature_ranges.json").read_text())["ranges"]
        # The classical pipelines were saved with scikit-learn 1.6; a model that cannot be unpickled with the
        # installed version (e.g. Gradient Boosting after sklearn's loss-module move) is skipped, not fatal.
        self.classical, self.classical_skipped = {}, []
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for name, fname in CLASSICAL_MODELS.items():
                try:
                    self.classical[name] = _sklearn_compat(joblib.load(MODELS_DIR / fname))
                except Exception:
                    self.classical_skipped.append(name)
        self.classical_features = (list(next(iter(self.classical.values()))["features"]) if self.classical
                                   else [])

        # trusted local checkpoints that contain metadata next to the weights, hence weights_only=False
        ens = torch.load(MODELS_DIR / "cnn_classifier.pt", map_location="cpu", weights_only=False)
        self.class_labels = list(ens.get("class_names", CLASS_LABELS))
        self.input_size = tuple(ens.get("input_size", [224, 224]))
        self.ensemble = [(self._build(m["backbone_name"], m["state_dict"]), float(m.get("weight", 1.0)))
                         for m in ens["models"]]
        self.singles = {}
        for key, (_, fname) in BACKBONES.items():
            if key != "ensemble" and (MODELS_DIR / fname).exists():
                ck = torch.load(MODELS_DIR / fname, map_location="cpu", weights_only=False)
                self.singles[key] = self._build(key, {k: v.float() if v.is_floating_point() else v
                                                      for k, v in ck["state_dict"].items()})

        seg = torch.load(MODELS_DIR / "seg_unet_small.pt", map_location="cpu", weights_only=False)
        self.seg_threshold = float(seg.get("threshold", 0.35))
        self.seg_tta = bool(seg.get("use_tta", True))
        self.seg_size = tuple(seg.get("input_size", [256, 256]))
        self.seg_model = _unet_small()
        self.seg_model.load_state_dict(seg["state_dict"])
        self.seg_model.eval()

    def _build(self, backbone: str, state_dict: dict):
        from torch import nn
        from torchvision import models

        n = len(self.class_labels)
        if backbone == "resnet18":
            m = models.resnet18(weights=None)
            m.fc = nn.Linear(m.fc.in_features, n)
        elif backbone == "efficientnet_b0":
            m = models.efficientnet_b0(weights=None)
            m.classifier[1] = nn.Linear(m.classifier[1].in_features, n)
        elif backbone == "convnext_tiny":
            m = models.convnext_tiny(weights=None)
            m.classifier[2] = nn.Linear(m.classifier[2].in_features, n)
        else:
            raise BrainModelError(f"Unsupported backbone: {backbone}")
        m.load_state_dict(state_dict)
        return m.eval()

    # ---------------------------------------------------------------- model steps
    def _tensor(self, img: Image.Image):
        from torchvision import transforms

        t = transforms.Compose([transforms.Resize(self.input_size), transforms.ToTensor(),
                                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
        return t(img).unsqueeze(0)

    def _probs(self, model, x, tta: bool) -> np.ndarray:
        p = self.torch.softmax(model(x), 1)
        if tta:
            p = (p + self.torch.softmax(model(self.torch.flip(x, dims=[3])), 1)) / 2
        return p[0].numpy()

    def classify(self, img: Image.Image, tta: bool) -> dict[str, np.ndarray]:
        x = self._tensor(img)
        with self.torch.no_grad():
            total = sum(w for _, w in self.ensemble)
            out = {"ensemble": sum(self._probs(m, x, tta) * w for m, w in self.ensemble) / total}
            for key, m in self.singles.items():
                out[key] = self._probs(m, x, tta)
        return out

    def saliency(self, img: Image.Image) -> np.ndarray:
        """Input-gradient saliency of the first ensemble member for its predicted class (values 0..1)."""
        import cv2

        model = self.ensemble[0][0]
        x = self._tensor(img).requires_grad_(True)
        with self.torch.enable_grad():
            logits = model(x)
            logits[0, logits.argmax(1)[0]].backward()
        g = cv2.GaussianBlur(x.grad.detach().abs().amax(1)[0].numpy(), (11, 11), 0)
        return (g - g.min()) / (g.max() - g.min() + 1e-8)

    def segment(self, img: Image.Image, threshold: float) -> np.ndarray:
        """Lesion probability map at the segmentation input size (values 0..1)."""
        arr = np.asarray(img.resize(self.seg_size), dtype=np.float32) / 255.0
        x = self.torch.from_numpy(arr.transpose(2, 0, 1).copy()).unsqueeze(0)
        with self.torch.no_grad():
            logits = self.seg_model(x)
            if self.seg_tta:
                logits = (logits + self.torch.flip(self.seg_model(self.torch.flip(x, dims=[3])), dims=[3])) / 2
            return self.torch.sigmoid(logits)[0, 0].numpy()

    def classical_support(self, features: dict[str, float]) -> list[dict]:
        import pandas as pd

        row = pd.DataFrame([{k: float(features[k]) for k in self.classical_features}])
        out = []
        for name, bundle in self.classical.items():
            pipe = bundle.get("pipeline")
            model, data = (pipe, row) if pipe is not None else (bundle["model"], row.to_numpy(dtype=np.float32))
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    pred = int(model.predict(data)[0])
                    prob = float(model.predict_proba(data)[0, 1]) if hasattr(model, "predict_proba") else float(pred)
            except Exception:
                continue
            out.append({"model": name, "label": "tumour" if pred == 1 else "no tumour", "tumor_probability": round(prob, 4)})
        return out

    # ---------------------------------------------------------------- full analysis
    def analyze(self, img: Image.Image, settings: BrainSettings, filename: str) -> BrainResult:
        import cv2

        img = img.convert("RGB")
        w, h = img.size
        check = assess_mri_input(img)
        plane = parse_plane(filename, settings.plane)
        base = {"modality": "brain_mri", "filename": filename,
                "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                "image_size": (w, h), "plane": plane, "input_check": check, "model": MODEL_INFO}
        rgb = np.asarray(img)
        if not check["applicable"] and not settings.force_out_of_scope:
            report = base | {"finding": FINDING_NOT_ASSESSED, "applicable": False, "predicted_class": None,
                             "predicted_probability": None, "confidence": "Not assessed",
                             "confidence_reasons": check["warnings"] + ["No prediction was made because the image "
                                                                        "is outside the brain MRI domain."],
                             "backbones": {}, "classical": [], "segmentation": None, "risk": None, "features": {}}
            return BrainResult(report, {"original": rgb})

        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        probs = self.classify(img, settings.use_tta)
        key = settings.backbone if settings.backbone in probs else "ensemble"
        p = probs[key]
        top = int(p.argmax())
        label = self.class_labels[top]
        backbones = {k: {"title": BACKBONES[k][0], "predicted_class": self.class_labels[int(v.argmax())],
                         "probability": round(float(v.max()), 4),
                         "probabilities": {c: round(float(x), 4) for c, x in zip(self.class_labels, v)}}
                     for k, v in probs.items()}

        prob_small = self.segment(img, settings.threshold)
        prob_map = cv2.resize(prob_small, (w, h), interpolation=cv2.INTER_LINEAR)
        mask = (cv2.resize((prob_small > settings.threshold).astype(np.uint8), (w, h),
                           interpolation=cv2.INTER_NEAREST) > 0).astype(np.uint8)
        sal = cv2.resize(self.saliency(img), (w, h), interpolation=cv2.INTER_LINEAR)

        area_pct = float(mask.mean() * 100)
        inside = float(gray[mask == 1].mean()) if mask.any() else None
        outside = float(gray[mask == 0].mean()) if (mask == 0).any() else None
        contrast = inside - outside if inside is not None and outside is not None else 0.0
        entropy, blur = _shannon_entropy(gray), float(cv2.Laplacian(gray, cv2.CV_64F).var())
        std = float(gray.std())
        quality = (0.4 * _normalize(blur, self.ranges["blur_score"]) + 0.3 * _normalize(entropy, self.ranges["image_entropy"])
                   + 0.3 * _normalize(std, self.ranges["image_std_intensity"])) * 100
        features = {"image_mean_intensity": float(gray.mean()), "image_std_intensity": std, "image_entropy": entropy,
                    "blur_score": blur, "edge_density": float(cv2.Canny(gray, 100, 200).mean() / 255.0),
                    "image_quality_score": quality, "plane_code": float(PLANE_CODES.get(plane, 0))}
        classical = self.classical_support(features)

        # triage score: lesion burden (50) + intensity contrast (30) + tumour type (25), capped at 100
        score = (_normalize(area_pct, self.ranges["tumor_area_percent"]) * 50
                 + _normalize(contrast, self.ranges["intensity_contrast"]) * 30 + CLASS_RISK_WEIGHTS.get(label, 8))
        score = float(np.clip(score, 0, 100))
        if label == "no_tumor":
            score = min(score, 18.0)
        size = ("none" if area_pct <= 0 or label == "no_tumor" else "small" if area_pct <= 1.5
                else "medium" if area_pct <= 5 else "large")
        level, priority = (("low", "Routine neuroimaging review") if score <= 33.33 else
                           ("medium", "Specialist neuroradiology review") if score <= 66.66 else
                           ("high", "Urgent neuro-oncology review"))

        agree = sum(b["predicted_class"] == label for b in backbones.values())
        conf_p = float(p[top])
        lvl = 2 if conf_p >= 0.9 else 1 if conf_p >= 0.7 else 0
        reasons = [f"{BACKBONES[key][0]} gives {conf_p:.1%} to {CLASS_NAMES[label].lower()}.",
                   f"{agree} of {len(backbones)} CNN backbones agree on this class."]
        if agree < len(backbones):
            lvl = max(0, lvl - 1)
        if label != "no_tumor" and area_pct == 0:
            reasons.append("The classifier sees a tumour but the U-Net found no lesion above the threshold; "
                           "try a lower segmentation threshold.")
            lvl = max(0, lvl - 1)
        tumour_votes = sum(c["label"] == "tumour" for c in classical)
        reasons.append(f"Classical radiomics: {tumour_votes} of {len(classical)} models predict a tumour "
                       "(image-level features only, weaker evidence).")
        if check["warnings"]:
            reasons += check["warnings"]
            lvl = max(0, lvl - 1)
        if not check["applicable"]:
            reasons.append("Analysis was forced on an image outside the brain MRI domain; interpret with caution.")
        if settings.plane == "auto" and plane == "axial" and "ax" not in filename.lower():
            reasons.append("Anatomical plane not in the file name, so axial was assumed for the classical models; "
                           "set it in Analysis settings if needed.")

        mask_u8 = mask.astype(np.uint8)
        morph = {"bbox_area_px": 0, "compactness": None, "centroid": None}
        if mask.any():          # shape of the largest lesion component
            contours, _ = cv2.findContours(mask_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            big = max(contours, key=cv2.contourArea)
            bx, by, bw, bh = cv2.boundingRect(big)
            perimeter = cv2.arcLength(big, True)
            m = cv2.moments(mask_u8)
            morph = {"bbox_area_px": int(bw * bh),
                     "compactness": round(float(4 * np.pi * cv2.contourArea(big) / (perimeter ** 2 + 1e-8)), 3),
                     "centroid": [round(m["m10"] / m["m00"], 1), round(m["m01"] / m["m00"], 1)]}
        overlay = rgb.copy()
        if mask.any():
            overlay[mask == 1] = (0.55 * overlay[mask == 1] + 0.45 * np.array([76, 91, 212])).astype(np.uint8)
            contours, _ = cv2.findContours(mask_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(overlay, contours, -1, (201, 168, 106), max(2, round(max(w, h) / 256)))
        images = {"original": rgb, "overlay": overlay, "probability": _heat(rgb, prob_map), "saliency": _heat(rgb, sal),
                  "mask": np.repeat(mask_u8[..., None] * 255, 3, axis=2)}

        finding = FINDING_NO_TUMOR if label == "no_tumor" else f"{CLASS_NAMES[label]} suspected"
        report = base | {
            "finding": finding, "applicable": check["applicable"], "predicted_class": CLASS_NAMES[label],
            "predicted_probability": round(conf_p, 4), "confidence": ["Low", "Moderate", "High"][lvl],
            "confidence_reasons": reasons, "selected_model": BACKBONES[key][0], "tta": settings.use_tta,
            "class_probabilities": {CLASS_NAMES[c]: round(float(x), 4) for c, x in zip(self.class_labels, p)},
            "backbones": backbones, "classical": classical,
            "segmentation": {"model": "U-Net (small), 256 px", "threshold": settings.threshold,
                             "lesion_area_percent": round(area_pct, 2), "lesion_size": size,
                             "intensity_contrast": round(contrast, 2)} | morph,
            "risk": {"score": round(score, 1), "level": level, "priority": priority,
                     "explanation": (f"Predicted {CLASS_NAMES[label].lower()}, lesion area {area_pct:.2f}% of the "
                                     f"slice ({size}), intensity contrast {contrast:.1f}: triage score "
                                     f"{score:.1f}/100 ({level}).")},
            "features": {k: round(v, 4) for k, v in features.items()},
        }
        return BrainResult(report, images)


def _sklearn_compat(bundle: dict) -> dict:
    """Newer scikit-learn reads SimpleImputer._fill_dtype, which pipelines saved with 1.6 do not have."""
    pipe = bundle.get("pipeline")
    for _, step in getattr(pipe, "steps", []):
        if type(step).__name__ == "SimpleImputer" and not hasattr(step, "_fill_dtype"):
            step._fill_dtype = step.statistics_.dtype
    return bundle


def _heat(rgb: np.ndarray, values: np.ndarray) -> np.ndarray:
    import cv2

    heat = cv2.cvtColor(cv2.applyColorMap(np.uint8(np.clip(values, 0, 1) * 255), cv2.COLORMAP_MAGMA), cv2.COLOR_BGR2RGB)
    return cv2.addWeighted(rgb, 0.6, heat, 0.4, 0)


def _unet_small():
    from torch import cat, nn

    def double(i, o):
        return nn.Sequential(nn.Conv2d(i, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(inplace=True),
                             nn.Conv2d(o, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(inplace=True))

    class DoubleConv(nn.Module):
        def __init__(self, i, o):
            super().__init__()
            self.block = double(i, o)

        def forward(self, x):
            return self.block(x)

    class UNetSmall(nn.Module):   # layer names match the checkpoint
        def __init__(self):
            super().__init__()
            self.down1, self.pool1 = DoubleConv(3, 32), nn.MaxPool2d(2)
            self.down2, self.pool2 = DoubleConv(32, 64), nn.MaxPool2d(2)
            self.bridge = DoubleConv(64, 128)
            self.up2, self.conv2 = nn.ConvTranspose2d(128, 64, 2, stride=2), DoubleConv(128, 64)
            self.up1, self.conv1 = nn.ConvTranspose2d(64, 32, 2, stride=2), DoubleConv(64, 32)
            self.out = nn.Conv2d(32, 1, 1)

        def forward(self, x):
            d1 = self.down1(x)
            d2 = self.down2(self.pool1(d1))
            b = self.bridge(self.pool2(d2))
            u2 = self.conv2(cat([self.up2(b), d2], 1))
            return self.out(self.conv1(cat([self.up1(u2), d1], 1)))

    return UNetSmall()


MODEL_INFO = {
    "name": "MedVisionAI brain tumour MRI models",
    "backbone": "EfficientNet-B0 5-fold ensemble (+ ConvNeXt-Tiny, ResNet-18), U-Net segmentation, classical radiomics",
    "task": "4 classes: glioma, meningioma, pituitary tumour, no tumour (BRISC 2025, T1 MRI slices)",
    "test_setup": "BRISC 2025 test split, 1,000 slices",
    "test_metrics": {"ensemble_accuracy": 0.993, "ensemble_macro_f1": 0.9936, "unet_val_dice_tta": 0.636},
}


def report_for_llm(report: dict) -> dict:
    """Compact version for the AI assistant (no per-backbone probability tables)."""
    d = {k: v for k, v in report.items() if k not in ("backbones", "features")}
    d["backbone_votes"] = {b["title"]: f'{b["predicted_class"]} {b["probability"]:.1%}'
                           for b in report.get("backbones", {}).values()}
    return d
