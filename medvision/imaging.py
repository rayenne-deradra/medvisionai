"""Image loading and validation, input-applicability checks, tiling and heatmap rendering."""
from __future__ import annotations

import io
import math
from dataclasses import asdict, dataclass, field

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

Image.MAX_IMAGE_PIXELS = 60_000_000   # refuse decompression bombs

ALLOWED_EXTENSIONS = ["png", "jpg", "jpeg", "tif", "tiff", "bmp", "webp"]
_ALLOWED_FORMATS = {"PNG", "JPEG", "MPO", "TIFF", "BMP", "WEBP"}
MIN_SIDE = 32


class ImageError(ValueError):
    """Raised with a user-readable message when an upload cannot be used."""


# ----------------------------------------------------------------------------- loading
def load_image(data: bytes, max_mb: float) -> Image.Image:
    """Validate raw upload bytes and return an RGB image."""
    if not data:
        raise ImageError("The file is empty.")
    if len(data) > max_mb * 1024 * 1024:
        raise ImageError(f"The file is larger than {max_mb:g} MB. Please upload a smaller image or crop it.")
    try:
        img = Image.open(io.BytesIO(data))
        fmt = img.format
        img.load()
    except Image.DecompressionBombError as e:
        raise ImageError("The image has too many pixels to process safely. Please crop or downscale it.") from e
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as e:
        raise ImageError("This file is not a readable image. Supported formats: PNG, JPEG, TIFF, BMP, WebP. "
                         "DICOM files must first be exported to PNG.") from e
    if fmt not in _ALLOWED_FORMATS:
        raise ImageError(f"Unsupported image format ({fmt}). Supported formats: PNG, JPEG, TIFF, BMP, WebP.")
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[-1])
        img = background
    img = img.convert("RGB")
    if min(img.size) < MIN_SIDE:
        raise ImageError(f"The image is too small ({img.width} × {img.height} px). Minimum is {MIN_SIDE} px per side.")
    return img


def downscale(img: Image.Image, max_side: int) -> Image.Image:
    if max(img.size) <= max_side:
        return img.copy()
    out = img.copy()
    out.thumbnail((max_side, max_side), Image.LANCZOS)
    return out


def to_bytes(img: Image.Image, fmt: str = "PNG", quality: int = 88) -> bytes:
    buf = io.BytesIO()
    if fmt.upper() == "JPEG":
        img.convert("RGB").save(buf, "JPEG", quality=quality, optimize=True)
    else:
        img.save(buf, fmt)
    return buf.getvalue()


# ----------------------------------------------------------------------------- applicability checks
@dataclass
class InputCheck:
    """Heuristic check of whether the image looks like an H&E histopathology image (the model's only domain)."""
    image_type: str            # "H&E-like histology" | "grayscale (e.g. radiology)" | "little tissue" | "unusual colours"
    applicable: bool
    tissue_fraction: float
    he_colour_fraction: float
    colourfulness: float
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _tissue_mask(arr: np.ndarray) -> np.ndarray:
    """arr: uint8 RGB. Tissue = not near-white background and somewhat saturated."""
    rgb = arr.astype(np.float32) / 255.0
    mx, mn = rgb.max(-1), rgb.min(-1)
    sat = (mx - mn) / (mx + 1e-6)
    return (sat > 0.08) & (mx < 0.94) & (mx > 0.08)


def assess_input(img: Image.Image) -> InputCheck:
    small = downscale(img, 384)
    arr = np.asarray(small, dtype=np.uint8)
    rgb = arr.astype(np.float32) / 255.0
    chroma = rgb.max(-1) - rgb.min(-1)
    colourfulness = float(chroma.mean())
    tissue = _tissue_mask(arr)
    tissue_fraction = float(tissue.mean())

    hsv = np.asarray(small.convert("HSV"), dtype=np.float32)
    hue_deg = hsv[..., 0] * 360.0 / 255.0
    he_hue = (hue_deg >= 250) | (hue_deg <= 25)   # violet / purple / pink / magenta, typical of H&E
    he_fraction = float(he_hue[tissue].mean()) if tissue.any() else 0.0

    warnings: list[str] = []
    if colourfulness < 0.02 or (colourfulness < 0.05 and tissue_fraction < 0.03):   # pale H&E still has tinted tissue
        image_type, applicable = "grayscale (e.g. radiology)", False
        warnings.append("The image is (nearly) grayscale, like an X-ray, CT, MRI or ultrasound. The MedVisionAI "
                        "classifier was trained only on colour H&E histopathology patches, so it cannot assess it.")
    elif tissue_fraction < 0.05:     # fat, background and mucus can look like this; the model has classes for them
        image_type, applicable = "little stained tissue", True
        warnings.append("Very little stained tissue was found; the image is mostly background, fat or mucus.")
    elif he_fraction < 0.35:
        image_type, applicable = "unusual colours", False
        warnings.append("The colours do not look like an H&E stain (pink/purple). The image may be a different "
                        "stain, a photo or a screenshot of something else; the classifier is out of its domain.")
    else:
        image_type, applicable = "H&E-like histology", True
        if he_fraction < 0.6:
            warnings.append("The staining colours are only partly H&E-like; the result may be less reliable.")
    if min(img.size) < 64:
        warnings.append("The image is very small, so detail is limited.")
    return InputCheck(image_type, applicable, round(tissue_fraction, 3), round(he_fraction, 3),
                      round(colourfulness, 3), warnings)


def tile_tissue_fraction(tile: Image.Image) -> float:
    return float(_tissue_mask(np.asarray(downscale(tile, 96), dtype=np.uint8)).mean())


# ----------------------------------------------------------------------------- tiling
def tile_boxes(width: int, height: int, tile: int) -> list[tuple[int, int, int, int]]:
    """Square tiles covering the image; the last row/column is shifted inwards so every tile is full size."""
    tile = max(1, min(tile, width, height))
    nx, ny = math.ceil(width / tile), math.ceil(height / tile)
    boxes = []
    for j in range(ny):
        y0 = min(j * tile, height - tile)
        for i in range(nx):
            x0 = min(i * tile, width - tile)
            boxes.append((x0, y0, x0 + tile, y0 + tile))
    return boxes


def auto_tile_size(width: int, height: int, min_tile: int, max_grid: int) -> int:
    return max(min_tile, math.ceil(max(width, height) / max_grid))


# ----------------------------------------------------------------------------- heatmap rendering
def resize_cam(cam: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    c = Image.fromarray((np.clip(cam, 0, 1) * 255).astype(np.uint8)).resize(size, Image.BICUBIC)
    return np.asarray(c, dtype=np.float32) / 255.0


def overlay_image(img: Image.Image, cam: np.ndarray, alpha: float = 0.5) -> Image.Image:
    """Semi-transparent red-to-yellow heatmap on top of the original image.

    The opacity follows the heat, so regions the model ignored keep their original colours and tissue detail;
    only influential regions are tinted (red = moderate, yellow = strongest influence).
    """
    base = np.asarray(img.convert("RGB"), dtype=np.float32) / 255
    c = resize_cam(cam, img.size)
    heat = np.stack([np.ones_like(c), np.clip(2 * c - 0.6, 0, 1), np.zeros_like(c)], -1)
    a = (alpha * np.clip((c - 0.15) / 0.85, 0, 1))[..., None]      # weakest 15% stay fully transparent
    return Image.fromarray((((1 - a) * base + a * heat).clip(0, 1) * 255).astype(np.uint8))
