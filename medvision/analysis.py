"""Runs the colorectal tissue classifier on an uploaded image and builds the classification report."""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

import numpy as np
from PIL import Image

from .classifier import TissueClassifier
from .imaging import assess_input, auto_tile_size, tile_boxes

FINDING_TUMOR = "Tumour tissue detected"
FINDING_NO_TUMOR = "No tumour tissue detected"
FINDING_NOT_ASSESSED = "Not assessed"


@dataclass
class AnalysisSettings:
    mode: str = "Auto"                  # "Auto" | "Single patch" | "Tile scan"
    tile_size: int | None = None        # px in the original image; None = automatic
    max_grid: int = 4                   # automatic tile size gives at most max_grid × max_grid tiles
    min_tumor_fraction: float = 0.10    # tile scan: share of tissue tiles that must be tumour to flag the image
    force_out_of_scope: bool = False    # run the model even when the image does not look like H&E
    single_patch_max_side: int = 336    # "Auto" analyses images up to this size as one patch


@dataclass
class CaseReport:
    filename: str
    created_utc: str
    image_size: tuple[int, int]
    finding: str
    applicable: bool
    analysis_mode: str
    predicted_class: str | None
    predicted_probability: float | None
    tumor_probability: float | None
    class_probabilities: dict[str, float]
    confidence: str                      # "High" | "Moderate" | "Low" | "Not assessed"
    confidence_reasons: list[str]
    heatmap_target: str | None
    input_check: dict
    tiles: dict | None
    model: dict
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_llm_dict(self) -> dict:
        """Compact version for the AI assistant."""
        d = self.to_dict()
        d["model"] = {k: self.model.get(k) for k in ("name", "backbone", "task", "test_setup", "test_metrics")}
        d.pop("limitations", None)
        return d


@dataclass
class AnalysisResult:
    report: CaseReport
    cam: np.ndarray | None        # heatmap in image coordinates (downscaled), values 0..1


_LEVELS = ["Low", "Moderate", "High"]


def _level(p: float) -> int:
    return 2 if p >= 0.9 else 1 if p >= 0.7 else 0


def _confidence(p: float, extra: list[str]) -> tuple[str, list[str]]:
    level = _level(p)
    reasons = [{2: f"The model is decisive ({p:.0%} for its answer).",
                1: f"The model is moderately sure ({p:.0%} for its answer).",
                0: f"The model is unsure ({p:.0%} for its answer); several tissue types are plausible."}[level]]
    if extra:
        level = max(0, level - 1)
        reasons += extra
    return _LEVELS[level], reasons


def analyze(img: Image.Image, clf: TissueClassifier, settings: AnalysisSettings,
            filename: str = "image") -> AnalysisResult:
    w, h = img.size
    check = assess_input(img)
    names, T = clf.class_names, clf.tumor_index
    card = clf.card.to_dict()
    base = dict(filename=filename, created_utc=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                image_size=(w, h), input_check=check.to_dict(), model=card, limitations=list(clf.card.limitations))

    if not check.applicable and not settings.force_out_of_scope:
        return AnalysisResult(CaseReport(
            finding=FINDING_NOT_ASSESSED, applicable=False, analysis_mode="none", predicted_class=None,
            predicted_probability=None, tumor_probability=None, class_probabilities={}, confidence="Not assessed",
            confidence_reasons=check.warnings + ["No tissue classification was made because the image is outside "
                                                 "the model's domain (colour H&E colorectal histology)."],
            heatmap_target=None, tiles=None, **base), None)

    extra = list(check.warnings)
    if not check.applicable:
        extra.append("Analysis was forced on an image that does not look like H&E histology; the result is "
                     "probably meaningless.")
    mode = settings.mode
    if mode == "Auto":
        mode = "Single patch" if max(w, h) <= settings.single_patch_max_side else "Tile scan"

    if mode == "Single patch":
        probs, cams = clf.explain([img])
        p = probs[0]
        top = int(p.argmax())
        cam = cams[0]
        if max(w, h) > 2.5 * clf.input_size:
            extra.append(f"The whole {w} × {h} px image was shrunk to {clf.input_size} px, which loses detail and "
                         "changes magnification; tile scan is usually better for large images.")
        confidence, reasons = _confidence(float(p[top]), extra)
        report = CaseReport(
            finding=FINDING_TUMOR if top == T else FINDING_NO_TUMOR, applicable=check.applicable,
            analysis_mode="single patch", predicted_class=names[top], predicted_probability=round(float(p[top]), 4),
            tumor_probability=round(float(p[T]), 4),
            class_probabilities={n: round(float(v), 4) for n, v in zip(names, p)},
            confidence=confidence, confidence_reasons=reasons, heatmap_target=names[top], tiles=None, **base)
        return AnalysisResult(report, cam.astype(np.float32))

    # ---- tile scan
    tile = settings.tile_size or auto_tile_size(w, h, clf.input_size, settings.max_grid)
    tile = min(tile, w, h)
    boxes = tile_boxes(w, h, tile)
    probs, cams = clf.explain([img.crop(b) for b in boxes], class_index=T)
    top = probs.argmax(1)
    background = names.index("Background") if "Background" in names else -1
    tissue = top != background
    n_tissue = int(tissue.sum())
    tumor_tiles = top == T
    n_tumor = int(tumor_tiles.sum())
    needed = max(1, math.ceil(settings.min_tumor_fraction * max(n_tissue, 1)))
    is_tumor = n_tumor >= needed

    # tumour heatmap: Grad-CAM for the tumour class, weighted by each tile's tumour probability
    scale = min(1.0, 768 / max(w, h))
    cw, ch = max(1, round(w * scale)), max(1, round(h * scale))
    cam_sum = np.zeros((ch, cw), np.float32)
    cam_cnt = np.zeros((ch, cw), np.float32)
    for (x0, y0, x1, y1), c, pt in zip(boxes, cams, probs[:, T]):
        x0, y0, x1, y1 = (round(v * scale) for v in (x0, y0, x1, y1))
        sw, sh = max(1, x1 - x0), max(1, y1 - y0)
        r = np.asarray(Image.fromarray((c * 255).astype(np.uint8)).resize((sw, sh), Image.BICUBIC), np.float32) / 255
        cam_sum[y0:y0 + sh, x0:x0 + sw] += (r * pt)[:ch - y0, :cw - x0]
        cam_cnt[y0:y0 + sh, x0:x0 + sw] += 1
    cam = cam_sum / np.maximum(cam_cnt, 1)

    composition = {n: round(float((top == k).mean()), 4) for k, n in enumerate(names)}
    mean_probs = probs.mean(0)
    if is_tumor:
        decisive = float(probs[tumor_tiles, T].mean())
    else:
        decisive = float(1 - probs[:, T].max())
    extra.append("Tile scan of a larger image is a heuristic: the model was validated on single 224 px patches, "
                 "and the magnification of this image is unknown.")
    if n_tumor and not is_tumor:
        extra.append(f"{n_tumor} tile(s) look like tumour, below the {settings.min_tumor_fraction:.0%} needed to "
                     "flag the image; review those areas.")
    confidence, reasons = _confidence(decisive, extra)
    k_top = int(mean_probs.argmax())
    report = CaseReport(
        finding=FINDING_TUMOR if is_tumor else FINDING_NO_TUMOR, applicable=check.applicable,
        analysis_mode=f"tile scan ({len(boxes)} tiles of {tile} px)", predicted_class=names[k_top],
        predicted_probability=round(float(mean_probs[k_top]), 4), tumor_probability=round(float(probs[:, T].max()), 4),
        class_probabilities={n: round(float(v), 4) for n, v in zip(names, mean_probs)},
        confidence=confidence, confidence_reasons=reasons, heatmap_target=names[T],
        tiles={"tile_size_px": tile, "n_tiles": len(boxes), "n_tissue_tiles": n_tissue, "n_tumor_tiles": n_tumor,
               "tumor_fraction": round(n_tumor / max(n_tissue, 1), 4), "required_tumor_fraction":
               settings.min_tumor_fraction, "composition": composition,
               "rule": f"Flagged when at least {needed} of {n_tissue} tissue tiles are classified as tumour "
                       f"(≥ {settings.min_tumor_fraction:.0%}). Heuristic, not validated at slide level."},
        **base)
    return AnalysisResult(report, cam.astype(np.float32))
