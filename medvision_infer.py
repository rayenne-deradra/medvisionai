"""medvision_infer.py: model definition, preprocessing and inference for MedVisionAI.

Binary classifier for histopathology image patches:
    index 0 = "Non-cancer", index 1 = "Cancer"  (two output logits, softmax, cancer index = 1).

The training notebook and the application import this same file, so preprocessing,
class order and model construction cannot drift apart.

Research prototype only. Not a medical device. Not for clinical use.
"""
import io
import os

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image, UnidentifiedImageError
from torchvision import models, transforms

MEAN = (0.485, 0.456, 0.406)   # ImageNet statistics, required by the pretrained weights
STD = (0.229, 0.224, 0.225)
CLASS_NAMES = ("Non-cancer", "Cancer")
CANCER_INDEX = 1
SUPPORTED_ARCHS = ("convnext_tiny", "resnet50", "efficientnet_b0")
SCORE_DEFINITION = ("Softmax probability of the Cancer class (output index 1). "
                    "It is a model score, not a calibrated clinical probability.")


class InferenceError(Exception):
    """Raised with a readable message when a model or image cannot be loaded or used."""


# ----------------------------------------------------------------------------- model
def build_model(arch, pretrained=True):
    """ImageNet-pretrained backbone with a new 2-logit head."""
    if arch == "convnext_tiny":
        m = models.convnext_tiny(weights=models.ConvNeXt_Tiny_Weights.DEFAULT if pretrained else None)
        m.classifier[2] = nn.Linear(m.classifier[2].in_features, 2)
    elif arch == "resnet50":
        m = models.resnet50(weights=models.ResNet50_Weights.DEFAULT if pretrained else None)
        m.fc = nn.Linear(m.fc.in_features, 2)
    elif arch == "efficientnet_b0":
        m = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT if pretrained else None)
        m.classifier[1] = nn.Linear(m.classifier[1].in_features, 2)
    else:
        raise ValueError(f"Unknown architecture '{arch}'. Choose one of {SUPPORTED_ARCHS}.")
    return m


def head_module(model, arch):
    """The part that contains the new classification layer."""
    return model.fc if arch == "resnet50" else model.classifier


def finetune_modules(model, arch):
    """Backbone stages that are unfrozen in the fine-tuning stage (the last ones)."""
    if arch == "resnet50":
        return [model.layer3, model.layer4]
    return [model.features[i] for i in range(5, len(model.features))]


def gradcam_layer(model, arch):
    """Layer used for Grad-CAM (stride 16, so a 6 x 6 map for a 96 px input)."""
    return model.layer3 if arch == "resnet50" else model.features[5]


def eval_transform(img_size):
    """The ONLY preprocessing used for validation, test and inference."""
    return transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])


def save_checkpoint(path, model, arch, img_size, threshold, meta=None, half=True):
    """Save weights plus everything needed to rebuild the model and reproduce preprocessing."""
    sd = {}
    for k, v in model.state_dict().items():
        v = v.detach().cpu()
        sd[k] = v.half() if (half and v.is_floating_point()) else v
    ck = {"format_version": 1, "arch": arch, "state_dict": sd,
          "class_names": list(CLASS_NAMES), "cancer_index": CANCER_INDEX,
          "img_size": int(img_size), "mean": list(MEAN), "std": list(STD),
          "threshold": float(threshold), "meta": meta or {}}
    torch.save(ck, path)
    return path


# ----------------------------------------------------------------------------- images
def load_image(source):
    """Accepts a path, bytes, a PIL image or a file-like object (e.g. a Streamlit upload)."""
    try:
        if isinstance(source, Image.Image):
            img = source
        elif isinstance(source, (bytes, bytearray)):
            img = Image.open(io.BytesIO(source))
        elif isinstance(source, (str, os.PathLike)):
            if not os.path.isfile(source):
                raise InferenceError(f"Image file not found: {source}")
            img = Image.open(source)
        elif hasattr(source, "read"):
            img = Image.open(source)
        else:
            raise InferenceError(f"Unsupported input type: {type(source).__name__}")
        img.load()
        return img.convert("RGB")
    except InferenceError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as e:
        raise InferenceError(f"Unsupported or corrupted image: {e}") from e


def overlay_heatmap(img, cam, size=256, alpha=0.6):
    """Blend a red/yellow heatmap (values 0 to 1) on top of the image."""
    base = np.asarray(img.convert("RGB").resize((size, size)), dtype=np.float32) / 255
    c = Image.fromarray((np.clip(cam, 0, 1) * 255).astype(np.uint8)).resize((size, size), Image.BICUBIC)
    c = np.asarray(c, dtype=np.float32) / 255
    heat = np.stack([np.clip(2 * c, 0, 1), np.clip(2 * c - 1, 0, 1), np.zeros_like(c)], -1)
    a = (alpha * c)[..., None]
    return Image.fromarray((((1 - a) * base + a * heat) * 255).astype(np.uint8))


# ----------------------------------------------------------------------------- Grad-CAM
class GradCAM:
    """Grad-CAM for the Cancer logit. Call remove() when finished."""

    def __init__(self, model, layer):
        self.model, self.act, self.grad = model, None, None
        self._handle = layer.register_forward_hook(self._save_activation)

    def _save_activation(self, module, inputs, output):
        self.act = output
        if output.requires_grad:
            output.register_hook(self._save_gradient)

    def _save_gradient(self, grad):
        self.grad = grad

    def remove(self):
        self._handle.remove()

    def __call__(self, x, class_index=CANCER_INDEX):
        """x: float tensor (B, 3, H, W). Returns (cam (B, h, w) in 0..1, class probability (B,))."""
        self.model.eval()
        x = x.clone().requires_grad_(True)       # makes sure gradients flow even through frozen layers
        with torch.enable_grad():
            logits = self.model(x).float()
            self.model.zero_grad(set_to_none=True)
            logits[:, class_index].sum().backward()
        weights = self.grad.mean(dim=(2, 3), keepdim=True)
        cam = F.relu((weights * self.act).sum(1))
        cam = cam / (cam.amax(dim=(1, 2), keepdim=True) + 1e-8)
        self.model.zero_grad(set_to_none=True)
        probs = torch.softmax(logits.detach(), 1)[:, class_index]
        return cam.detach().cpu().numpy(), probs.cpu().numpy()


# ----------------------------------------------------------------------------- predictor
def _pick_device(device):
    if device is not None:
        return torch.device(device)
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


class Predictor:
    """Loads a checkpoint written by save_checkpoint() and predicts Cancer / Non-cancer."""

    def __init__(self, model, arch, img_size, threshold, device="cpu", source="in-memory", meta=None):
        self.device = _pick_device(device)
        self.model = model.to(self.device).eval()
        self.arch, self.img_size, self.threshold = arch, int(img_size), float(threshold)
        self.source, self.meta = source, meta or {}
        self.transform = eval_transform(self.img_size)

    # -- constructors
    @classmethod
    def from_checkpoint(cls, path, device=None):
        if not os.path.isfile(path):
            raise InferenceError(f"Checkpoint file not found: {path}")
        try:
            ck = torch.load(path, map_location="cpu", weights_only=True)
        except Exception as e:
            raise InferenceError(f"Could not read checkpoint '{path}': {e}") from e
        missing = [k for k in ("arch", "state_dict", "img_size", "threshold", "cancer_index") if k not in ck]
        if missing:
            raise InferenceError(f"Checkpoint is missing fields: {missing}")
        if ck["arch"] not in SUPPORTED_ARCHS:
            raise InferenceError(f"Unsupported architecture in checkpoint: {ck['arch']}")
        if int(ck["cancer_index"]) != CANCER_INDEX:
            raise InferenceError("Checkpoint cancer index does not match this module.")
        model = build_model(ck["arch"], pretrained=False)
        sd = {k: (v.float() if v.is_floating_point() else v) for k, v in ck["state_dict"].items()}
        try:
            model.load_state_dict(sd)
        except RuntimeError as e:
            raise InferenceError(f"Checkpoint weights do not match the architecture: {e}") from e
        return cls(model, ck["arch"], ck["img_size"], ck["threshold"], device,
                   source=os.path.abspath(path), meta=ck.get("meta", {}))

    @classmethod
    def from_hub(cls, repo_id, filename, device=None, revision=None, token=None):
        """Download the checkpoint from Hugging Face (cached after the first time)."""
        try:
            from huggingface_hub import hf_hub_download
        except ImportError as e:
            raise InferenceError("Install huggingface_hub: pip install huggingface_hub") from e
        try:
            path = hf_hub_download(repo_id=repo_id, filename=filename, revision=revision, token=token)
        except Exception as e:
            raise InferenceError(f"Could not download '{filename}' from '{repo_id}': {e}") from e
        predictor = cls.from_checkpoint(path, device)
        predictor.source = f"hf://{repo_id}/{filename}"
        return predictor

    # -- prediction
    def _result(self, p):
        is_cancer = p >= self.threshold
        return {"label": CLASS_NAMES[CANCER_INDEX] if is_cancer else CLASS_NAMES[1 - CANCER_INDEX],
                "cancer_score": float(p),
                "score_definition": SCORE_DEFINITION,
                "threshold": self.threshold,
                "architecture": self.arch,
                "img_size": self.img_size,
                "checkpoint": self.source}

    @torch.no_grad()
    def predict_batch(self, images, batch_size=64):
        results = []
        for i in range(0, len(images), batch_size):
            x = torch.stack([self.transform(load_image(im)) for im in images[i:i + batch_size]]).to(self.device)
            try:
                probs = torch.softmax(self.model(x).float(), 1)[:, CANCER_INDEX].cpu().numpy()
            except Exception as e:
                raise InferenceError(f"Inference failed: {e}") from e
            results.extend(self._result(float(p)) for p in probs)
        return results

    def predict(self, image):
        return self.predict_batch([image])[0]

    def explain(self, image):
        """Returns (result dict, heatmap overlay as a PIL image)."""
        img = load_image(image)
        x = self.transform(img).unsqueeze(0).to(self.device)
        engine = GradCAM(self.model, gradcam_layer(self.model, self.arch))
        try:
            cam, prob = engine(x)
        except Exception as e:
            raise InferenceError(f"Grad-CAM failed: {e}") from e
        finally:
            engine.remove()
        return self._result(float(prob[0])), overlay_heatmap(img, cam[0])


def verify_hub_file(repo_id, filename, token=None):
    """True if the file really exists in the Hugging Face repo (check before deploying)."""
    from huggingface_hub import list_repo_files
    return filename in list_repo_files(repo_id, token=token)


if __name__ == "__main__" and "ipykernel" not in __import__("sys").modules:   # skipped inside Colab/Jupyter cells
    import argparse
    ap = argparse.ArgumentParser(description="Predict Cancer / Non-cancer for one image.")
    ap.add_argument("image")
    ap.add_argument("--checkpoint", help="local .pt file")
    ap.add_argument("--hf-repo")
    ap.add_argument("--hf-file")
    a = ap.parse_args()
    pred = (Predictor.from_checkpoint(a.checkpoint) if a.checkpoint
            else Predictor.from_hub(a.hf_repo, a.hf_file))
    print(pred.predict(a.image))
