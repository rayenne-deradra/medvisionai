"""Real-model tests on CRC-VAL-HE-7K example patches (skipped if the trained head is missing). No mocks."""
import pytest
from PIL import Image

from medvision.analysis import FINDING_NO_TUMOR, FINDING_NOT_ASSESSED, FINDING_TUMOR, AnalysisSettings, analyze
from medvision.config import EXAMPLES_DIR, MODELS_DIR

pytestmark = pytest.mark.skipif(not (MODELS_DIR / "crc_head_phikon.pt").is_file(), reason="head not trained yet")


@pytest.fixture(scope="module")
def clf():
    from medvision.classifier import load_classifier
    return load_classifier("phikon")


def test_example_patches_are_classified_correctly(clf):
    wrong = []
    for path in sorted(EXAMPLES_DIR.glob("test_*.png")):
        r = analyze(Image.open(path).convert("RGB"), clf, AnalysisSettings(), path.name).report
        truth = path.stem.replace("test_", "").rsplit("_", 1)[0]
        expected_tumor = truth == "colorectal_adenocarcinoma_epithelium"
        if r.finding != (FINDING_TUMOR if expected_tumor else FINDING_NO_TUMOR):
            wrong.append(path.name)
        assert abs(sum(r.class_probabilities.values()) - 1) < 1e-3
    assert len(wrong) <= 1, f"misclassified: {wrong}"


def test_mosaic_tile_scan_finds_tumour(clf):
    img = Image.open(next(EXAMPLES_DIR.glob("mosaic_*.jpg"))).convert("RGB")
    res = analyze(img, clf, AnalysisSettings(mode="Tile scan", tile_size=224), "mosaic")
    assert res.report.tiles["n_tumor_tiles"] >= 2 and res.report.finding == FINDING_TUMOR
    assert res.cam is not None and res.cam.max() > 0


def test_radiology_like_image_is_not_assessed(clf):
    gray = Image.new("RGB", (256, 256), (120, 120, 120))
    res = analyze(gray, clf, AnalysisSettings(), "xray")
    assert res.report.finding == FINDING_NOT_ASSESSED and res.cam is None
