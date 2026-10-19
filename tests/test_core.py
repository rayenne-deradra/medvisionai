"""Fast tests for image handling, tiling and chat history (no model needed)."""
import io

import numpy as np
import pytest
from PIL import Image

from medvision.config import EXAMPLES_DIR
from medvision.chat import add_message, build_llm_messages, new_conversation
from medvision.imaging import ImageError, assess_input, load_image, overlay_image, tile_boxes


def _png(img):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _he_like(size=96, seed=0):
    rng = np.random.default_rng(seed)
    arr = np.zeros((size, size, 3), np.uint8)
    arr[...] = (215, 120, 190)
    arr[rng.random((size, size)) < 0.3] = (110, 60, 160)
    return Image.fromarray(arr)


def test_load_image_rejects_garbage_tiny_and_empty():
    for bad in (b"not an image", _png(Image.new("RGB", (8, 8))), b""):
        with pytest.raises(ImageError):
            load_image(bad, 10)


def test_load_image_flattens_alpha():
    img = load_image(_png(Image.new("RGBA", (64, 64), (0, 0, 0, 0))), 10)
    assert img.mode == "RGB" and img.getpixel((0, 0)) == (255, 255, 255)


def test_grayscale_is_out_of_scope_but_he_and_fat_are_not():
    gray = Image.fromarray((np.random.default_rng(0).random((128, 128)) * 255).astype(np.uint8)).convert("RGB")
    assert not assess_input(gray).applicable
    assert assess_input(_he_like()).applicable
    for name in ("test_adipose_0.png", "test_background_0.png", "test_mucus_0.png"):   # pale but valid classes
        assert assess_input(Image.open(EXAMPLES_DIR / name).convert("RGB")).applicable


def test_tiles_cover_image():
    boxes = tile_boxes(500, 230, 224)
    assert all(b[2] - b[0] == 224 and b[3] - b[1] == 224 for b in boxes)
    assert max(b[2] for b in boxes) == 500 and max(b[3] for b in boxes) == 230


def test_overlay_keeps_cold_regions_untouched():
    img = _he_like(64)
    cam = np.zeros((8, 8), np.float32)
    cam[:2, :2] = 1.0
    out = np.asarray(overlay_image(img, cam, 0.5))
    assert (out[-10:, -10:] == np.asarray(img)[-10:, -10:]).all()      # zero heat: original pixels
    assert (out[:4, :4] != np.asarray(img)[:4, :4]).any()               # hot corner is tinted


def test_llm_history_alternates_and_only_latest_pictures_are_sent():
    conv = new_conversation()
    cases = {"a": {"report_llm": {"finding": "x"}, "llm_images": [b"img", b"cam"]}}
    add_message(conv, "user", "explain", case_id="a")
    add_message(conv, "assistant", "explanation")
    add_message(conv, "user", "what is this?", images=[b"photo"])
    add_message(conv, "assistant", "failed", kind="error")
    add_message(conv, "user", "and now?")
    msgs = build_llm_messages(conv, cases, 16)
    assert [m.role for m in msgs] == ["user", "assistant", "user"]
    assert msgs[0].images == [] and "medvision_report" in msgs[0].text
    assert msgs[2].images == [b"photo"] and "and now?" in msgs[2].text
    assert conv["title"] == "explain"
