"""Finds and loads the colorectal tissue classifier. Add new backends to `BACKENDS`."""
from __future__ import annotations

from ..config import MODELS_DIR, get_secret
from .base import ClassifierError, TissueClassifier

DEFAULT_BACKEND = "phikon"


def _load_foundation(key: str) -> TissueClassifier:
    import torch

    from .foundation import BACKBONES, FoundationTissueClassifier

    path = MODELS_DIR / f"crc_head_{key}.pt"
    if not path.is_file():
        raise ClassifierError(f"Classification head not found: models/{path.name}. Train it with "
                              "`python evaluation/benchmark.py` (see README).")
    try:
        ck = torch.load(path, map_location="cpu", weights_only=True)
    except Exception as e:
        raise ClassifierError(f"Could not read models/{path.name}: {e}") from e
    if ck.get("backbone") not in BACKBONES:
        raise ClassifierError(f"models/{path.name} was trained for an unknown backbone '{ck.get('backbone')}'.")
    return FoundationTissueClassifier(ck["backbone"], ck["head"], ck.get("meta", {}))


BACKENDS = {
    "phikon": lambda: _load_foundation("phikon"),
    "lunit_vits8": lambda: _load_foundation("lunit_vits8"),
    # "my_model": _load_my_model,      # see README, "Integrating another model"
}


def load_classifier(name: str | None = None) -> TissueClassifier:
    name = name or get_secret("MEDVISION_BACKEND", DEFAULT_BACKEND)
    if name not in BACKENDS:
        raise ClassifierError(f"Unknown classifier backend '{name}'. Available: {', '.join(BACKENDS)}")
    return BACKENDS[name]()
