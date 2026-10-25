"""Brain tumour MRI page: upload a T1 MRI slice -> 4-class CNN ensemble, U-Net lesion outline, classical radiomics,
saliency map and a 0-100 triage risk score."""
from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

import streamlit as st
from PIL import Image

from medvision.brain import BACKBONES, SAMPLES_DIR, BrainModelError, BrainSettings, report_for_llm
from medvision.chat import new_conversation
from medvision.config import LLM_IMAGE_MAX_SIDE, MAX_UPLOAD_MB
from medvision.imaging import ALLOWED_EXTENSIONS, ImageError, downscale, load_image, to_bytes
from medvision.ui.components import (brain_backbones_html, brain_classical_html, brain_header_html,
                                     brain_probabilities_html, brain_reasons_html)
from medvision.ui.shared import cases_of, get_brain_engine, ss
from medvision.ui.theme import page_head_html, section_html

VIEWS = {"overlay": "Lesion outline (U-Net)", "probability": "U-Net probability map", "saliency": "CNN saliency map"}


# ----------------------------------------------------------------------------- sidebar (this page only)
def settings_from_state() -> BrainSettings:
    return BrainSettings(backbone=ss.get("br_model", "ensemble"), plane=ss.get("br_plane", "auto"),
                         threshold=ss.get("br_thresh", 0.35), use_tta=ss.get("br_tta", True),
                         force_out_of_scope=ss.get("br_force", False))


def pick_case(key: str) -> None:
    ss.current_brain = ss[key]


with st.sidebar:
    picker_slot = st.empty()
    with st.expander("Analysis settings", icon=":material/tune:"):
        st.selectbox("Reported model", list(BACKBONES), format_func=lambda k: BACKBONES[k][0], key="br_model",
                     help="All four CNNs are always run and compared; this one gives the reported class.")
        st.segmented_control("Anatomical plane", ["auto", "axial", "coronal", "sagittal"], default="auto",
                             key="br_plane", format_func=str.capitalize,
                             help="Auto reads the plane from the file name (e.g. _ax_, _cor_, _sag_), else assumes axial.")
        st.slider("U-Net threshold", 0.15, 0.75, 0.35, 0.05, key="br_thresh", format="%.2f",
                  help="Pixels with a lesion probability above this value form the lesion outline.")
        st.toggle("Test-time augmentation (flip)", value=True, key="br_tta",
                  help="Averages each CNN over the image and its mirror image.")
        st.toggle("Analyse out-of-scope images anyway", key="br_force",
                  help="Run the models even on colour images that do not look like an MRI slice (unreliable).")
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
        with st.status("Analysing the MRI slice…", expanded=False) as status:
            status.write("Loading the brain MRI models (first time only, about 30 seconds)…")
            engine = get_brain_engine()
            status.write("Classifying, segmenting and scoring…")
            result = engine.analyze(img, settings_from_state(), filename)
            status.update(label="Analysis complete", state="complete")
    except BrainModelError as e:
        st.error(str(e), icon=":material/error:")
        return
    images = {k: Image.fromarray(v) for k, v in result.images.items()}
    llm_images = [to_bytes(downscale(images["original"], LLM_IMAGE_MAX_SIDE), "JPEG")]
    if "overlay" in images:
        llm_images.append(to_bytes(downscale(images["overlay"], LLM_IMAGE_MAX_SIDE), "JPEG"))
    case_id = uuid.uuid4().hex[:10]
    ss.cases[case_id] = {"id": case_id, "modality": "brain_mri", "report": result.report,
                         "report_llm": report_for_llm(result.report), "images": {k: downscale(v, 900)
                                                                                 for k, v in images.items()},
                         "thumb": downscale(images["original"], 320), "llm_images": llm_images, "source": data}
    ss.case_order.append(case_id)
    ss.current_brain = case_id
    st.rerun()


def queue_example(path: str) -> None:
    ss.pending_brain_example = path


def discuss(case_id: str) -> None:
    conv = new_conversation()
    ss.conversations[conv["id"]] = conv
    ss.active_chat = conv["id"]
    ss.pending_send = {"text": "Please explain this MedVisionAI brain MRI analysis.", "case_id": case_id}


def refer(case_id: str) -> None:
    ss.appt_case = case_id
    ss.appt_sid = "neuro-oncology" if ss.cases[case_id]["report"].get("risk", {}).get("level") == "high" \
        else "neuroradiology"
    ss.appt_done = None


# ----------------------------------------------------------------------------- page
st.markdown(page_head_html("Neuro-oncology · BRISC 2025", "Brain tumour MRI",
                           "Upload a T1-weighted axial, coronal or sagittal brain MRI slice. Four CNNs classify it "
                           "(glioma, meningioma, pituitary tumour or no tumour), a U-Net outlines the lesion, and a "
                           "triage score suggests how soon a specialist should review it."), unsafe_allow_html=True)

st.markdown(section_html("Analyse an MRI slice", "JPEG or PNG · grayscale T1 slice"), unsafe_allow_html=True)
upload = st.file_uploader("Upload a brain MRI slice", type=ALLOWED_EXTENSIONS, label_visibility="collapsed",
                          key="br_upload", help=f"PNG, JPEG, TIFF, BMP or WebP, up to {MAX_UPLOAD_MB} MB.")
if upload is not None:
    data = upload.getvalue()
    digest = hashlib.sha256(data).hexdigest()
    if ss.get("last_brain_upload") != digest:
        ss.last_brain_upload = digest
        run_analysis(data, upload.name)

example = ss.pop("pending_brain_example", None)
if example:
    run_analysis(Path(example).read_bytes(), Path(example).name)

samples = sorted(p for p in SAMPLES_DIR.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg"))


def render_examples() -> None:
    with st.container(key="mv_examples"):
        cols = st.columns(5, gap="small")
        for i, path in enumerate(samples):
            label = path.stem.replace("_sample", "").replace("_t1", "").replace("_2", " 2").replace("no_tumor", "no tumour")
            label = label.replace("_", " ")
            with cols[i % 5]:
                st.image(str(path), width="stretch")
                st.button(label.capitalize()[:26], key=f"bex_{path.stem}", width="stretch", type="tertiary",
                          help=f"True label: {label.split(' ')[0]}", on_click=queue_example, args=(str(path),))


case = ss.cases.get(ss.current_brain or "")
if not case:
    st.markdown(section_html("Or try a sample", "BRISC 2025 test slices, true label shown"), unsafe_allow_html=True)
    render_examples()
else:
    r = case["report"]
    st.markdown(section_html("Result", "4-class CNN ensemble · U-Net segmentation · triage score"),
                unsafe_allow_html=True)
    st.markdown(brain_header_html(r), unsafe_allow_html=True)
    left, right = st.columns([1.3, 1], gap="medium")
    with left:
        with st.container(key="mv_bimages"):
            imgs = case["images"]
            if len(imgs) == 1:
                st.markdown('<div class="mv-label">Original</div>', unsafe_allow_html=True)
                st.image(imgs["original"], width="stretch")
                st.info("No overlay: the models did not assess this image.")
            else:
                view = st.segmented_control("Overlay", list(VIEWS), format_func=VIEWS.get, default="overlay",
                                            key="br_view", label_visibility="collapsed") or "overlay"
                a, b = st.columns(2, gap="small")
                with a:
                    st.markdown('<div class="mv-label">Original</div>', unsafe_allow_html=True)
                    st.image(imgs["original"], width="stretch")
                with b:
                    st.markdown(f'<div class="mv-label">{VIEWS[view]}</div>', unsafe_allow_html=True)
                    st.image(imgs[view], width="stretch")
                st.markdown('<div class="mv-foot">Blue fill and gold outline = U-Net lesion mask. Maps: dark = little, '
                            'bright = strong (lesion probability or influence on the CNN). They show where the models '
                            'looked, not proof of disease.</div>', unsafe_allow_html=True)
        with st.container(key="mv_breasons"):
            st.markdown(brain_reasons_html(r), unsafe_allow_html=True)
    with right:
        if r.get("class_probabilities"):
            with st.container(key="mv_bprobs"):
                st.markdown(brain_probabilities_html(r), unsafe_allow_html=True)
            with st.container(key="mv_bb"):
                st.markdown(brain_backbones_html(r), unsafe_allow_html=True)
            if r["classical"]:
                with st.container(key="mv_cl"):
                    st.markdown(brain_classical_html(r), unsafe_allow_html=True)
    a1, a2, a3, a4 = st.columns([1.25, 1.1, 1, 1], gap="small")
    if a1.button("Discuss with the AI Assistant", icon=":material/forum:", type="primary", width="stretch",
                 on_click=discuss, args=(case["id"],)):
        st.switch_page("views/assistant.py")
    if r.get("risk") and a2.button("Refer to a specialist", icon=":material/event:", width="stretch",
                                   on_click=refer, args=(case["id"],)):
        st.switch_page("views/appointments.py")
    if a3.button("Re-analyse", icon=":material/refresh:", width="stretch", help="Run again with the current settings"):
        run_analysis(case["source"], r["filename"])
    a4.download_button("Report", json.dumps(r, indent=2, default=str), file_name="medvision_brain_report.json",
                       mime="application/json", icon=":material/description:", width="stretch",
                       key=f"bdl_{case['id']}", help="Download the report as JSON")
    with st.expander("Try another sample", icon=":material/photo_library:"):
        render_examples()

brain_ids = cases_of("brain_mri")
if brain_ids:
    labels = {cid: f"{ss.cases[cid]['report']['filename']} · {ss.cases[cid]['report']['finding']}" for cid in brain_ids}
    key = f"brain_picker_{ss.current_brain}"
    picker_slot.selectbox("Previous MRI analyses", list(labels), format_func=labels.get, key=key,
                          index=list(labels).index(ss.current_brain) if ss.current_brain in labels else 0,
                          on_change=pick_case, args=(key,))

with card_slot.container():
    with st.expander("Model card", icon=":material/info:"):
        st.markdown(
            "**Classifier:** 5-fold EfficientNet-B0 ensemble, trained with weighted focal loss on BRISC 2025 "
            "(T1 MRI, 4 classes). Test accuracy **99.3%**, macro-F1 **0.994** on 1,000 held-out slices. "
            "Compared live with single EfficientNet-B0 (97.9%), ConvNeXt-Tiny (97.7% with TTA) and ResNet-18 "
            "(96.5% with TTA).\n\n"
            "**Segmentation:** small U-Net, 256 × 256 px, flip TTA; validation Dice **0.64**. It finds the lesion "
            "region but its outline is approximate.\n\n"
            "**Classical radiomics:** Random Forest, SVM, Decision Tree and Logistic Regression on 7 image "
            "features (Random Forest test F1 0.98 for tumour vs no tumour).\n\n"
            "**Triage score (0–100):** lesion area (up to 50) + intensity contrast (up to 30) + tumour type "
            "(glioma 25, pituitary 18, meningioma 12); capped at 18 when no tumour is predicted. A heuristic, not "
            "a validated clinical score.")
        st.markdown("**Limitations**\n- Single 2D slices only, no 3D volumes or DICOM.\n- One public dataset; not "
                    "validated on other hospitals or scanners.\n- Not a medical device; never use for diagnosis.")
