"""Interface every MedVisionAI colorectal tissue classifier implements.

To plug in another model, subclass `TissueClassifier`, implement `explain`, and register a loader in
`registry.py`. Tiling, the report, the heatmap overlay and the AI assistant only talk to this interface.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field

import numpy as np
from PIL import Image


class ClassifierError(RuntimeError):
    """Raised with a readable message when a model cannot be loaded or run."""


@dataclass
class ModelCard:
    name: str
    backbone: str
    task: str
    training_data: str
    input_description: str
    test_setup: str
    test_metrics: dict = field(default_factory=dict)
    robustness: dict = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    licence: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class TissueClassifier(ABC):
    """Multi-class colorectal tissue classifier with calibrated probabilities and a heatmap explanation."""

    card: ModelCard
    class_names: list[str]
    tumor_index: int
    input_size: int = 224          # patch side (px) the model expects; larger images are tiled at this scale

    @abstractmethod
    def explain(self, images: list[Image.Image], class_index: int | None = None) -> tuple[np.ndarray, np.ndarray]:
        """Returns (probabilities (N, K), heatmaps (N, h, w) with values 0..1).

        Heatmaps are for `class_index`, or for each image's most likely class when it is None.
        """
