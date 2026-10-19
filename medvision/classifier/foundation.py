"""Colorectal tissue classifier: a frozen, pretrained pathology foundation model + a small linear head.

Only the linear head (9 classes) is trained on NCT-CRC-HE-100K (see `evaluation/benchmark.py`); the backbone weights
are downloaded unchanged from Hugging Face and never modified. Heatmaps are Grad-CAM over the ViT patch tokens entering
the last transformer block, for the predicted (or requested) class.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

from .base import ClassifierError, ModelCard, TissueClassifier

CODES = ["ADI", "BACK", "DEB", "LYM", "MUC", "MUS", "NORM", "STR", "TUM"]
CLASS_NAMES = ["Adipose tissue", "Background", "Debris / necrosis", "Lymphocytes", "Mucus", "Smooth muscle",
               "Normal colon mucosa", "Cancer-associated stroma", "Colorectal adenocarcinoma epithelium"]
TUMOR_INDEX = CODES.index("TUM")


@dataclass(frozen=True)
class BackboneSpec:
    key: str
    hub_id: str
    title: str
    params_m: int
    licence: str
    pretraining: str


BACKBONES = {
    "phikon": BackboneSpec(
        "phikon", "hf-hub:1aurent/vit_base_patch16_224.owkin_pancancer", "Phikon (Owkin) ViT-B/16", 86,
        "Owkin non-commercial licence (research use)",
        "iBOT self-supervised pretraining on 43M H&E tiles from 16 TCGA cancer types, including colon and rectum"),
    "lunit_vits8": BackboneSpec(
        "lunit_vits8", "hf-hub:1aurent/vit_small_patch8_224.lunit_dino", "Lunit DINO ViT-S/8", 22,
        "Lunit non-commercial licence (research use)",
        "DINO self-supervised pretraining on 19M H&E tiles from 37k TCGA and in-house slides"),
}


def load_backbone(key: str):
    """Returns (timm model in eval mode, preprocessing function PIL -> tensor)."""
    try:
        import timm
        from timm.data import create_transform, resolve_data_config
    except ImportError as e:
        raise ClassifierError("The 'timm' package is missing. Run: pip install -r requirements.txt") from e
    spec = BACKBONES[key]
    try:
        model = timm.create_model(spec.hub_id, pretrained=True, num_classes=0)
    except Exception as e:
        raise ClassifierError(f"Could not download the {spec.title} backbone from Hugging Face "
                              f"({type(e).__name__}). Check the internet connection.") from e
    model.eval()
    for p in model.parameters():
        p.requires_grad_(False)
    cfg = resolve_data_config({}, model=model)
    cfg.update(input_size=(3, 224, 224), crop_pct=1.0, interpolation="bicubic")
    return model, create_transform(**cfg)


class LinearHead(torch.nn.Module):
    """Standardisation + linear layer + temperature, trained on frozen backbone features."""

    def __init__(self, dim: int, n_classes: int = 9):
        super().__init__()
        self.register_buffer("mean", torch.zeros(dim))
        self.register_buffer("std", torch.ones(dim))
        self.register_buffer("temperature", torch.ones(()))
        self.fc = torch.nn.Linear(dim, n_classes)

    def forward(self, feats: torch.Tensor) -> torch.Tensor:
        """Calibrated logits (divide by temperature before softmax)."""
        return self.fc((feats - self.mean) / self.std) / self.temperature


class _TokenGradCAM:
    """Grad-CAM on the patch tokens entering the last ViT block (CLS / register tokens are dropped).

    The hook sits on the last block's first LayerNorm: the class token attends over these tokens, so they
    receive gradients. (The patch-token *outputs* of the last block never reach the class token.)
    """

    def __init__(self, model):
        self.model, self.act, self.grad = model, None, None
        self._h = model.blocks[-1].norm1.register_forward_hook(self._hook)

    def _hook(self, module, inputs, output):
        self.act = output
        output.register_hook(lambda g: setattr(self, "grad", g))

    def remove(self):
        self._h.remove()

    def cam(self) -> np.ndarray:
        n_prefix = getattr(self.model, "num_prefix_tokens", 1)
        act, grad = self.act[:, n_prefix:], self.grad[:, n_prefix:]
        side = int(math.isqrt(act.shape[1]))
        w = grad.mean(dim=1, keepdim=True)                       # channel weights
        cam = F.relu((w * act).sum(-1)).reshape(-1, side, side)
        cam = cam / (cam.amax(dim=(1, 2), keepdim=True) + 1e-8)
        return cam.detach().cpu().numpy().astype(np.float32)


class FoundationTissueClassifier(TissueClassifier):
    """9-class colorectal tissue classifier. `predict` returns calibrated probabilities and Grad-CAM maps."""

    def __init__(self, backbone_key: str, head_state: dict, meta: dict):
        self.spec = BACKBONES[backbone_key]
        self.backbone, self.transform = load_backbone(backbone_key)
        dim = self.backbone.num_features
        self.head = LinearHead(dim, len(CLASS_NAMES))
        try:
            self.head.load_state_dict(head_state)
        except RuntimeError as e:
            raise ClassifierError(f"The classification head does not match the {self.spec.title} backbone: {e}") from e
        self.head.eval()
        self.meta = meta
        self.class_names = CLASS_NAMES
        self.tumor_index = TUMOR_INDEX
        self.card = ModelCard(
            name="MedVisionAI colorectal tissue classifier",
            backbone=f"{self.spec.title} ({self.spec.params_m}M parameters, frozen) + linear head",
            task="Classifies an H&E colorectal tissue patch into 9 tissue types. 'Colorectal adenocarcinoma "
                 "epithelium' is the tumour class; the other 8 are normal or non-tumour tissue.",
            training_data=f"Backbone: {self.spec.pretraining}. Linear head: {meta.get('training', {}).get('data', '')}",
            input_description="Colour H&E patch of colon/rectum tissue, ideally 224 × 224 px at ~0.5 µm/px (20×). "
                              "Larger images are scanned tile by tile.",
            test_setup=meta.get("test_setup", ""),
            test_metrics=meta.get("test", {}),
            robustness=meta.get("robustness", {}),
            limitations=[
                "Research prototype: validated on patches from one external cohort (CRC-VAL-HE-7K, 50 patients), "
                "not on whole slides or in a clinical setting.",
                "Covers colorectal tissue only. Other organs, tumour types, polyps/adenomas and grading are outside "
                "its training.",
                "Magnification matters: patches far from ~20× (e.g. screenshots of whole slides) are less reliable.",
                "Cancer-associated stroma and debris are the classes most often confused.",
            ],
            licence=self.spec.licence,
        )

    @torch.inference_mode()
    def features(self, images: list[Image.Image], batch_size: int = 32) -> torch.Tensor:
        out = []
        for i in range(0, len(images), batch_size):
            x = torch.stack([self.transform(im.convert("RGB")) for im in images[i:i + batch_size]])
            out.append(self.backbone(x))
        return torch.cat(out)

    @torch.inference_mode()
    def probabilities(self, images: list[Image.Image], batch_size: int = 32) -> np.ndarray:
        return torch.softmax(self.head(self.features(images, batch_size)), 1).numpy()

    def explain(self, images: list[Image.Image], class_index: int | None = None, batch_size: int = 16):
        """Returns (probabilities (N, 9), Grad-CAM maps (N, h, w) for `class_index` or each image's top class)."""
        probs, cams = [], []
        for i in range(0, len(images), batch_size):
            x = torch.stack([self.transform(im.convert("RGB")) for im in images[i:i + batch_size]])
            engine = _TokenGradCAM(self.backbone)
            try:
                with torch.enable_grad():
                    x = x.clone().requires_grad_(True)
                    logits = self.head(self.backbone(x))
                    target = (logits.argmax(1) if class_index is None
                              else torch.full((len(x),), class_index, dtype=torch.long))
                    logits.gather(1, target[:, None]).sum().backward()
                cams.append(engine.cam())
            except Exception as e:
                raise ClassifierError(f"The model failed while analysing the image: {e}") from e
            finally:
                engine.remove()
            probs.append(torch.softmax(logits.detach(), 1).numpy())
        return np.concatenate(probs), np.concatenate(cams)
