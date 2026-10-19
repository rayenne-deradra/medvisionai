"""Rendering helpers: classification report card, probability bars, original + Grad-CAM overlay."""
from __future__ import annotations

import html
import json

import numpy as np
import streamlit as st
from PIL import Image

from ..imaging import overlay_image, to_bytes

TUMOR_CLASS = "Colorectal adenocarcinoma epithelium"


def _pct(p: float) -> str:
    """Never show 0% or 100%: calibrated probabilities are estimates, not certainties."""
    return ">99.9%" if p > 0.999 else "<0.1%" if p < 0.001 else f"{p:.1%}"


def _bars_html(probs: dict[str, float], highlight: str | None) -> str:
    rows = []
    for name, p in sorted(probs.items(), key=lambda kv: -kv[1]):
        cls = "tumor" if name == TUMOR_CLASS else "top" if name == highlight else ""
        rows.append(f'<div class="mv-prob {cls}"><span class="n">{html.escape(name)}</span>'
                    f'<span class="track"><span class="fill" style="width:{max(p, 0.004) * 100:.1f}%"></span></span>'
                    f'<span class="p">{_pct(p)}</span></div>')
    return "".join(rows)


def report_card_html(r: dict) -> str:
    e = html.escape
    finding = r["finding"]
    tone = {"Tumour tissue detected": "rose", "No tumour tissue detected": "teal"}.get(finding, "muted")
    conf = r["confidence"]
    parts = ['<div class="mv-card"><div class="mv-card-head"><div>'
             '<div class="mv-card-title">Classification report</div>'
             f'<div class="mv-finding {tone}">{e(finding)}</div></div>'
             f'<span class="mv-chip {e(conf.split()[0])}">CONFIDENCE · {e(conf.upper())}</span></div>']
    kv = []
    if r["predicted_class"]:
        label = "Dominant tissue" if r.get("tiles") else "Predicted tissue"
        kv += [(label, f'{r["predicted_class"]} ({_pct(r["predicted_probability"])})'),
               ("Tumour probability" + (" (max tile)" if r.get("tiles") else ""), _pct(r["tumor_probability"]))]
    if r.get("tiles"):
        t = r["tiles"]
        kv.append(("Tumour tiles", f'{t["n_tumor_tiles"]} of {t["n_tissue_tiles"]} tissue tiles'))
    check = r["input_check"]
    kv += [("Analysis", r["analysis_mode"]), ("Image check", check["image_type"]),
           ("Size", f'{r["image_size"][0]} × {r["image_size"][1]} px')]
    parts.append('<div class="mv-grid">' + "".join(
        f'<div class="mv-kv"><div class="k">{e(k)}</div><div class="v">{e(str(v))}</div></div>' for k, v in kv) +
        "</div>")
    if r["class_probabilities"]:
        title = "Tissue composition (mean over tiles)" if r.get("tiles") else "Confidence scores (calibrated)"
        parts.append(f'<div class="mv-section" style="margin-top:16px">{title}</div>'
                     + _bars_html(r["class_probabilities"], r["predicted_class"]))
    parts.append('<div class="mv-section" style="margin-top:14px">Why this confidence</div>'
                 '<ul class="mv-reasons">' + "".join(f"<li>{e(x)}</li>" for x in r["confidence_reasons"]) + "</ul>")
    if r.get("tiles"):
        parts.append(f'<div class="mv-foot">{e(r["tiles"]["rule"])}</div>')
    parts.append(f'<div class="mv-foot">{e(r["model"]["backbone"])} · {e(r["created_utc"])} · '
                 "Research use only, not a diagnosis.</div></div>")
    return "".join(parts)


def render_visuals(case: dict, key: str, alpha: float) -> None:
    img: Image.Image = case["display_image"]
    cam: np.ndarray | None = case["cam"]
    target = case["report"].get("heatmap_target")
    col_a, col_b = st.columns(2, gap="medium")
    with col_a:
        st.markdown('<div class="mv-section">Original image</div>', unsafe_allow_html=True)
        st.image(img, width="stretch")
    with col_b:
        st.markdown('<div class="mv-section">Grad-CAM overlay</div>', unsafe_allow_html=True)
        if cam is None:
            st.info("No heatmap: the classifier did not assess this image.")
        else:
            st.image(overlay_image(img, cam, alpha), width="stretch")
            st.markdown(f'<div class="mv-legend">untinted = little influence<span class="g"></span>'
                        f'strongest evidence for “{html.escape(target or "")}”</div>', unsafe_allow_html=True)


def render_downloads(case: dict, key: str, alpha: float) -> None:
    d1, d2 = st.columns(2)
    d1.download_button("Report (JSON)", json.dumps(case["report"], indent=2, default=str),
                       file_name="medvision_report.json", mime="application/json", key=f"dl_r_{key}",
                       icon=":material/description:", width="stretch")
    if case["cam"] is not None:
        d2.download_button("Overlay (PNG)", to_bytes(overlay_image(case["display_image"], case["cam"], alpha)),
                           file_name="medvision_gradcam.png", mime="image/png", key=f"dl_h_{key}",
                           icon=":material/download:", width="stretch")
