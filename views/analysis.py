"""Colorectal tissue page: upload -> colorectal tissue classification, confidence scores, report, Grad-CAM overlay."""
from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

import streamlit as st

from medvision.analysis import AnalysisSettings, analyze
from medvision.chat import add_message, new_conversation
from medvision.classifier import ClassifierError
from medvision.config import DISPLAY_MAX_SIDE, EXAMPLES_DIR, LLM_IMAGE_MAX_SIDE, MAX_UPLOAD_MB
from medvision.imaging import ALLOWED_EXTENSIONS, ImageError, downscale, load_image, overlay_image, to_bytes
from medvision.ui.components import (probabilities_html, reasons_html, render_downloads, render_visuals,
                                     result_header_html)
from medvision.ui.shared import cases_of, get_classifier, ss
from medvision.ui.theme import page_head_html, sample_html, section_html, thumb_uri


# ----------------------------------------------------------------------------- sidebar (this page only)
def settings_from_state() -> AnalysisSettings:
    tile = ss.get("an_tile", "Auto")
    return AnalysisSettings(mode=ss.get("an_mode") or "Auto", tile_size=None if tile == "Auto" else int(tile),
                            min_tumor_fraction=ss.get("an_frac", 0.10), force_out_of_scope=ss.get("an_force", False))


def pick_case(key: str) -> None:
    ss.current_case = ss[key]


with st.sidebar:
    picker_slot = st.empty()          # filled at the end of the run, after a new analysis may have been added
    with st.expander("Analysis settings", icon=":material/tune:"):
        st.segmented_control("Mode", ["Auto", "Single patch", "Tile scan"], default="Auto", key="an_mode",
                             help="Auto: images up to 336 px are one patch; larger images are scanned tile by tile.")
        st.select_slider("Tile size (px)", ["Auto", 224, 320, 448, 672, 896], value="Auto", key="an_tile",
                         help="Tile side in pixels of the original image. Auto gives at most 4 × 4 tiles. "
                              "224 px matches the model's training scale (~20×).")
        st.slider("Tumour tiles needed", 0.05, 0.5, 0.10, 0.05, key="an_frac", format="%.2f",
                  help="Tile scan: share of tissue tiles that must be classified as tumour to flag the image.")
        st.slider("Heatmap opacity", 0.2, 0.8, 0.5, 0.05, key="heat_alpha")
        st.toggle("Analyse out-of-scope images anyway", key="an_force",
                  help="Run the classifier even on images that do not look like H&E histology (unreliable).")
    card_slot = st.empty()


# ----------------------------------------------------------------------------- actions
def run_analysis(data: bytes, filename: str) -> None:
    filename = Path(filename).name[:80] or "image"
    try:
        img = load_image(data, MAX_UPLOAD_MB)
    except ImageError as e:
        st.error(str(e), icon=":material/error:")
        return
    try:
        with st.status("Analysing the tissue…", expanded=False) as status:
            status.write("Loading the classifier (first time: downloads the Phikon backbone, ~350 MB)…")
            clf = get_classifier()
            status.write("Checking the image and classifying…")
            result = analyze(img, clf, settings_from_state(), filename)
            status.update(label="Analysis complete", state="complete")
    except ClassifierError as e:
        st.error(str(e), icon=":material/error:")
        return
    llm_view = downscale(img, LLM_IMAGE_MAX_SIDE)
    llm_images = [to_bytes(llm_view, "JPEG")]
    if result.cam is not None:
        llm_images.append(to_bytes(overlay_image(llm_view, result.cam, 0.5), "JPEG"))
    case_id = uuid.uuid4().hex[:10]
    ss.cases[case_id] = {"id": case_id, "modality": "colorectal", "report": result.report.to_dict(), "report_llm": result.report.to_llm_dict(),
                         "cam": result.cam, "display_image": downscale(img, DISPLAY_MAX_SIDE),
                         "thumb": downscale(img, 320), "llm_images": llm_images, "source": data}
    ss.case_order.append(case_id)
    ss.current_case = case_id
    st.rerun()          # redraw without the progress box


def queue_example(path: str) -> None:
    ss.pending_example = path


def discuss(case_id: str) -> None:
    conv = new_conversation()
    ss.conversations[conv["id"]] = conv
    ss.active_chat = conv["id"]
    ss.pending_send = {"text": "Please explain this MedVisionAI analysis.", "case_id": case_id}


# ----------------------------------------------------------------------------- page
st.markdown(page_head_html("Histopathology · NCT-CRC-HE-100K", "Colorectal tissue analysis",
                           "Upload an H&amp;E image of colon or rectum tissue. The Phikon foundation model classifies it "
                           "into 9 tissue types with calibrated confidence, flags tumour tissue and shows a Grad-CAM "
                           "overlay. Large images are scanned tile by tile."), unsafe_allow_html=True)

st.markdown(section_html("Analyse an image", "H&E colorectal tissue · ideally 224 × 224 px at ~20×"),
            unsafe_allow_html=True)
upload = st.file_uploader("Upload an H&E image of colorectal tissue", type=ALLOWED_EXTENSIONS,
                          label_visibility="collapsed",
                          help=f"PNG, JPEG, TIFF, BMP or WebP, up to {MAX_UPLOAD_MB} MB. Larger images are scanned "
                               "tile by tile.")
if upload is not None:
    data = upload.getvalue()
    digest = hashlib.sha256(data).hexdigest()
    if ss.get("last_upload") != digest:          # analyse each new upload once
        ss.last_upload = digest
        run_analysis(data, upload.name)

example = ss.pop("pending_example", None)
if example:
    run_analysis(Path(example).read_bytes(), Path(example).name)

examples = sorted(EXAMPLES_DIR.glob("*.png")) + sorted(EXAMPLES_DIR.glob("*.jpg"))


def render_examples(where: str = "main") -> None:
    cols = st.columns(4, gap="small")
    for i, path in enumerate(examples):
        label = path.stem.replace("test_", "").rsplit("_", 1)[0].replace("_", " ").replace("-", " ")
        mosaic = path.stem.startswith("mosaic")
        title = "16-patch mosaic" if mosaic else label.replace("colorectal adenocarcinoma epithelium",
                                                               "adenocarcinoma").capitalize()
        tumour = "adenocarcinoma" in label or mosaic
        with cols[i % 4], st.container(key=f"mv_card_c{where}{i}"):
            st.markdown(sample_html(thumb_uri(str(path)), title, "tile scan" if mosaic else "224 px patch",
                                    "#E8B5C9" if tumour else "#E2E5EE"), unsafe_allow_html=True)
            st.button(f"Analyse {title}", key=f"ex_{where}_{path.stem}", help=f"True label: {label}",
                      on_click=queue_example, args=(str(path),))


case = ss.cases.get(ss.current_case or "")
if case and case.get("modality", "colorectal") != "colorectal":
    case = None
if not case:
    st.markdown(section_html("Or try a sample", "real test patches from CRC-VAL-HE-7K, true label shown"),
                unsafe_allow_html=True)
    render_examples()
else:
    st.markdown(section_html("Result", "calibrated 9-class tissue classification"), unsafe_allow_html=True)
    r = case["report"]
    st.markdown(result_header_html(r), unsafe_allow_html=True)
    left, right = st.columns([1.3, 1], gap="medium")
    with left:
        render_visuals(case, ss.get("heat_alpha", 0.5))
        with st.container(key="mv_reasons"):
            st.markdown(reasons_html(r), unsafe_allow_html=True)
    with right:
        with st.container(key="mv_probs"):
            st.markdown(probabilities_html(r), unsafe_allow_html=True)
    a1, a2, a3 = st.columns([1.3, 1, 1], gap="small")
    if a1.button("Discuss with the AI Assistant", icon=":material/forum:", type="primary", width="stretch",
                 on_click=discuss, args=(case["id"],)):
        st.switch_page("views/assistant.py")
    if a2.button("Re-analyse with current settings", icon=":material/refresh:", width="stretch"):
        run_analysis(case["source"], r["filename"])
        st.rerun()
    with a3:
        render_downloads(case, case["id"], ss.get("heat_alpha", 0.5))
    with st.expander("Try another sample", icon=":material/photo_library:"):
        render_examples("more")

crc_ids = cases_of("colorectal")
if crc_ids:
    labels = {cid: f"{ss.cases[cid]['report']['filename']} · {ss.cases[cid]['report']['finding']}" for cid in crc_ids}
    key = f"case_picker_{ss.current_case}"
    picker_slot.selectbox("Previous analyses", list(labels), format_func=labels.get, key=key,
                          index=list(labels).index(ss.current_case) if ss.current_case in labels else 0,
                          on_change=pick_case, args=(key,))

# model card last, so loading the model never delays the page
with card_slot.container():
    with st.expander("Model card", icon=":material/info:"):
        try:
            card = get_classifier().card
            m = card.test_metrics
            st.markdown(f"**{card.name}**  \n{card.backbone}\n\n{card.task}")
            if m:
                st.markdown(f"**Test** ({card.test_setup}): accuracy {m.get('accuracy_9class', 0):.1%} · "
                            f"macro-F1 {m.get('macro_f1_9class', 0):.3f} · tumour recall "
                            f"{m.get('tumor_recall', 0):.1%} · tumour precision {m.get('tumor_precision', 0):.1%}")
            if card.robustness:
                st.markdown("**Robustness (accuracy · tumour recall)**\n" + "\n".join(
                    f"- {c}: {v['accuracy_9class']:.1%} · {v['tumor_recall']:.1%}" for c, v in card.robustness.items()))
            st.markdown(f"**Training data:** {card.training_data}")
            st.markdown("**Limitations**\n" + "\n".join(f"- {x}" for x in card.limitations))
            st.caption(f"Licence: {card.licence}")
        except ClassifierError as e:
            st.error(str(e))
