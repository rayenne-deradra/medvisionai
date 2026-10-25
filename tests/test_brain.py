"""Brain MRI models on the bundled BRISC samples (loads ~220 MB of weights, a few seconds per image on CPU)."""
import pytest
from PIL import Image

from medvision.appointments import case_summary, suggest_urgency
from medvision.brain import SAMPLES_DIR, BrainEngine, BrainSettings, assess_mri_input, parse_plane


@pytest.fixture(scope="module")
def engine():
    return BrainEngine()


def test_input_check_and_plane():
    assert not assess_mri_input(Image.new("RGB", (256, 256), (200, 80, 160)))["applicable"]
    assert assess_mri_input(Image.new("L", (256, 256), 90))["applicable"]
    assert parse_plane("x_cor_t1.png", "auto") == "coronal" and parse_plane("x.png", "sagittal") == "sagittal"


@pytest.mark.parametrize("path", sorted(SAMPLES_DIR.iterdir()), ids=lambda p: p.stem)
def test_samples(engine, path):
    r = engine.analyze(Image.open(path), BrainSettings(), path.name).report
    truth = path.stem.split("_")[0]
    expected = {"glioma": "Glioma", "meningioma": "Meningioma", "pituitary": "Pituitary tumour", "no": "No tumour"}[truth]
    assert r["predicted_class"] == expected
    assert 0 <= r["risk"]["score"] <= 100 and r["classical"]
    assert suggest_urgency(r) in ("urgent", "soon", "routine") and "triage score" in case_summary(r)


def test_colour_image_not_assessed(engine):
    r = engine.analyze(Image.new("RGB", (300, 300), (220, 120, 180)), BrainSettings(), "slide.png").report
    assert r["finding"] == "Not assessed" and r["risk"] is None
