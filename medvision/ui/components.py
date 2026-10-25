"""Rendering helpers: result header with KPI tiles, probability panel, original + Grad-CAM overlay, downloads."""
from __future__ import annotations

import html
import json

import numpy as np
import streamlit as st
from PIL import Image

from ..imaging import overlay_image, to_bytes

TUMOR_CLASS = "Colorectal adenocarcinoma epithelium"
_TONE = {"Tumour tissue detected": ("rose", "!"), "No tumour tissue detected": ("teal", "✓")}


def _pct(p: float) -> str:
    """Never show 0% or 100%: calibrated probabilities are estimates, not certainties."""
    return ">99.9%" if p > 0.999 else "<0.1%" if p < 0.001 else f"{p:.1%}"


def result_header_html(r: dict) -> str:
    """Finding, confidence chip and four KPI tiles."""
    e = html.escape
    tone, icon = _TONE.get(r["finding"], ("muted", "–"))
    conf = r["confidence"]
    sub = f'{r["filename"]} · {r["analysis_mode"]}'
    parts = ['<div class="mv-result"><div class="mv-result-top">'
             f'<div class="mv-finding {tone}"><div class="ic">{icon}</div><div>'
             f'<div class="t">{e(r["finding"])}</div><div class="s">{e(sub)}</div></div></div>'
             f'<span class="mv-chip {e(conf.split()[0])}">Confidence: {e(conf)}</span></div>']
    kpis = []
    if r["predicted_class"]:
        tp = r["tumor_probability"]
        kpis.append(("Tumour probability" + (" · max tile" if r.get("tiles") else ""),
                     f'<div class="v big">{_pct(tp)}</div><div class="meter"><span style="width:{max(tp, .01) * 100:.0f}%">'
                     "</span></div>"))
        kpis.append(("Dominant tissue" if r.get("tiles") else "Predicted tissue",
                     f'<div class="v">{e(r["predicted_class"])}</div>'))
        if r.get("tiles"):
            t = r["tiles"]
            kpis.append(("Tumour tiles", f'<div class="v">{t["n_tumor_tiles"]} of {t["n_tissue_tiles"]}</div>'))
        else:
            kpis.append(("Model certainty", f'<div class="v">{_pct(r["predicted_probability"])}</div>'))
    kpis.append(("Image check", f'<div class="v">{e(r["input_check"]["image_type"])}</div>'))
    if len(kpis) < 4:
        kpis.append(("Image size", f'<div class="v">{r["image_size"][0]} × {r["image_size"][1]} px</div>'))
    parts.append('<div class="mv-kpis">' + "".join(
        f'<div class="mv-kpi"><div class="k">{e(k)}</div>{v}</div>' for k, v in kpis[:4]) + "</div></div>")
    return "".join(parts)


def probabilities_html(r: dict) -> str:
    if not r["class_probabilities"]:
        return ""
    title = "Tissue composition (mean over tiles)" if r.get("tiles") else "Confidence scores (calibrated)"
    rows = []
    for name, p in sorted(r["class_probabilities"].items(), key=lambda kv: -kv[1]):
        cls = "tumor" if name == TUMOR_CLASS else "top" if name == r["predicted_class"] else ""
        rows.append(f'<div class="mv-prob {cls}"><span class="n">{html.escape(name)}</span>'
                    f'<span class="track"><span class="fill" style="width:{max(p, 0.004) * 100:.1f}%"></span></span>'
                    f'<span class="p">{_pct(p)}</span></div>')
    return f'<div class="mv-label">{title}</div>' + "".join(rows)


def reasons_html(r: dict) -> str:
    e = html.escape
    out = ('<div class="mv-label">Why this confidence</div><ul class="mv-reasons">' +
           "".join(f"<li>{e(x)}</li>" for x in r["confidence_reasons"]) + "</ul>")
    if r.get("tiles"):
        out += f'<div class="mv-foot">{e(r["tiles"]["rule"])}</div>'
    out += (f'<div class="mv-foot">{e(r["model"]["backbone"])} · {e(r["created_utc"])} · '
            "Research use only, not a diagnosis.</div>")
    return out


def render_visuals(case: dict, alpha: float) -> None:
    """Original and Grad-CAM overlay side by side, in one card."""
    img: Image.Image = case["display_image"]
    cam: np.ndarray | None = case["cam"]
    target = case["report"].get("heatmap_target")
    with st.container(key="mv_images"):
        col_a, col_b = st.columns(2, gap="small")
        with col_a:
            st.markdown('<div class="mv-label">Original</div>', unsafe_allow_html=True)
            st.image(img, width="stretch")
        with col_b:
            st.markdown('<div class="mv-label">Grad-CAM overlay</div>', unsafe_allow_html=True)
            if cam is None:
                st.info("No heatmap: the classifier did not assess this image.")
            else:
                st.image(overlay_image(img, cam, alpha), width="stretch")
        if cam is not None:
            st.markdown(f'<div class="mv-legend">untinted = little influence<span class="g"></span>'
                        f'strongest evidence for “{html.escape(target or "")}”</div>', unsafe_allow_html=True)


def render_downloads(case: dict, key: str, alpha: float) -> None:
    d1, d2 = st.columns(2)
    d1.download_button("Report", json.dumps(case["report"], indent=2, default=str),
                       file_name="medvision_report.json", mime="application/json", key=f"dl_r_{key}",
                       icon=":material/description:", width="stretch", help="Download the report as JSON")
    if case["cam"] is not None:
        d2.download_button("Overlay", to_bytes(overlay_image(case["display_image"], case["cam"], alpha)),
                           file_name="medvision_gradcam.png", mime="image/png", key=f"dl_h_{key}",
                           icon=":material/download:", width="stretch", help="Download the Grad-CAM overlay as PNG")


# ----------------------------------------------------------------------------- brain MRI
_BRAIN_TONE = {"No brain tumour detected": ("teal", "✓"), "Not assessed": ("muted", "–")}


def brain_header_html(r: dict) -> str:
    """Finding, confidence chip and four KPI tiles for a brain MRI case."""
    e = html.escape
    tone, icon = _BRAIN_TONE.get(r["finding"], ("rose", "!"))
    conf = r["confidence"]
    plane = r.get("plane", "")
    sub = f'{r["filename"]} · {plane} plane' if r.get("predicted_class") else r["filename"]
    parts = ['<div class="mv-result"><div class="mv-result-top">'
             f'<div class="mv-finding {tone}"><div class="ic">{icon}</div><div>'
             f'<div class="t">{e(r["finding"])}</div><div class="s">{e(sub)}</div></div></div>'
             f'<span class="mv-chip {e(conf.split()[0])}">Confidence: {e(conf)}</span></div>']
    if r.get("risk"):
        risk, seg = r["risk"], r["segmentation"]
        kpis = [("Triage risk score", f'<div class="v big {risk["level"]}">{risk["score"]:.0f}<small>/100</small></div>'
                 f'<div class="meter risk"><span style="width:{max(risk["score"], 1):.0f}%"></span></div>'),
                ("Predicted class", f'<div class="v">{e(r["predicted_class"])}</div>'),
                ("Model certainty", f'<div class="v">{_pct(r["predicted_probability"])}</div>'),
                ("Lesion area (U-Net)", f'<div class="v">{seg["lesion_area_percent"]:.2f}% · {e(seg["lesion_size"])}</div>')]
    else:
        kpis = [("Image check", f'<div class="v">{e(r["input_check"]["image_type"])}</div>'),
                ("Image size", f'<div class="v">{r["image_size"][0]} × {r["image_size"][1]} px</div>')]
    parts.append('<div class="mv-kpis">' + "".join(
        f'<div class="mv-kpi"><div class="k">{e(k)}</div>{v}</div>' for k, v in kpis) + "</div></div>")
    return "".join(parts)


def brain_probabilities_html(r: dict) -> str:
    if not r.get("class_probabilities"):
        return ""
    rows = []
    for name, p in sorted(r["class_probabilities"].items(), key=lambda kv: -kv[1]):
        cls = "tumor" if name == r["predicted_class"] and name != "No tumour" else "top" if name == r["predicted_class"] else ""
        rows.append(f'<div class="mv-prob {cls}"><span class="n">{html.escape(name)}</span>'
                    f'<span class="track"><span class="fill" style="width:{max(p, 0.004) * 100:.1f}%"></span></span>'
                    f'<span class="p">{_pct(p)}</span></div>')
    return f'<div class="mv-label">Class probabilities · {html.escape(r["selected_model"])}</div>' + "".join(rows)


def brain_backbones_html(r: dict) -> str:
    """Every CNN backbone's vote, the reported one in bold."""
    from ..brain import CLASS_NAMES

    rows = []
    for b in r["backbones"].values():
        sel = "sel" if b["title"] == r["selected_model"] else ""
        rows.append(f'<tr class="{sel}"><td>{html.escape(b["title"])}</td>'
                    f'<td>{html.escape(CLASS_NAMES.get(b["predicted_class"], b["predicted_class"]))}</td>'
                    f'<td class="num">{_pct(b["probability"])}</td></tr>')
    return ('<div class="mv-label">Deep-learning consensus' + (" · flip TTA" if r.get("tta") else "") + '</div>'
            '<table class="mv-table"><tr><th>Model</th><th>Prediction</th><th class="num">Probability</th></tr>'
            + "".join(rows) + "</table>")


def brain_classical_html(r: dict) -> str:
    rows = "".join(
        f'<tr><td>{html.escape(c["model"])}</td><td><span class="mv-tag {"yes" if c["label"] == "tumour" else "no"}">'
        f'{c["label"].capitalize()}</span></td><td class="num">{_pct(c["tumor_probability"])}</td></tr>'
        for c in r["classical"])
    return ('<div class="mv-label">Classical radiomics · tumour vs no tumour</div>'
            '<table class="mv-table"><tr><th>Model</th><th>Vote</th><th class="num">P(tumour)</th></tr>' + rows +
            '</table><div class="mv-foot">7 image-level features (entropy, blur, edges, intensity, quality, plane). '
            'Weaker evidence than the CNNs, shown as a second opinion.</div>')


def brain_reasons_html(r: dict) -> str:
    e = html.escape
    out = ('<div class="mv-label">Why this confidence</div><ul class="mv-reasons">' +
           "".join(f"<li>{e(x)}</li>" for x in r["confidence_reasons"]) + "</ul>")
    if r.get("risk"):
        out += f'<div class="mv-foot"><b>{e(r["risk"]["priority"])}.</b> {e(r["risk"]["explanation"])}</div>'
    out += f'<div class="mv-foot">{e(r["model"]["backbone"])} · {e(r["created_utc"])} · Research use only, not a diagnosis.</div>'
    return out
