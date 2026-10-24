"""Specialist profiles and pre-filled booking links."""
from urllib.parse import parse_qs, urlparse

from medvision.consult import booking_link, case_summary, load_specialists


def test_examples_are_marked_and_use_the_default_link():
    sps = load_specialists({}, "https://calendly.com/practice/30min")
    assert len(sps) == 3 and all(s.example and s.booking_url.endswith("/30min") for s in sps)
    assert [s.initials for s in sps] == ["GI", "AI", "CS"]


def test_configured_specialists_override_examples():
    sps = load_specialists({"dr-a": {"name": "Dr. A", "title": "Pathologist",
                                     "booking_url": "https://cal.com/dr-a/30"}}, "https://calendly.com/x")
    assert len(sps) == 1 and not sps[0].example and sps[0].booking_url == "https://cal.com/dr-a/30"
    assert load_specialists({"dr-b": {"title": "Surgeon"}}, "https://calendly.com/x")[0].booking_url == "https://calendly.com/x"


def test_booking_link_prefill_and_embed():
    q = parse_qs(urlparse(booking_link("https://calendly.com/p/30min?month=2026-11", name="Acme",
                                       notes="Second opinion", embed=True)).query)
    assert q["name"] == ["Acme"] and q["a1"] == ["Second opinion"] and q["month"] == ["2026-11"]
    assert q["embed_type"] == ["Inline"]
    q = parse_qs(urlparse(booking_link("https://cal.com/dr/30", notes="x", embed=True)).query)
    assert q["notes"] == ["x"] and q["embed"] == ["true"]
    assert booking_link("", notes="x") == ""


def test_case_summary_has_no_image_and_states_research_use():
    r = {"filename": "p.png", "finding": "Tumour tissue detected", "confidence": "High",
         "predicted_class": "Colorectal adenocarcinoma epithelium", "tumor_probability": 0.97}
    s = case_summary(r)
    assert "Tumour tissue detected" in s and "97.0%" in s and "not a diagnosis" in s
