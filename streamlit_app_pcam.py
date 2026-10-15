"""MedVisionAI demo: lymph node tissue patch check (PatchCamelyon model).
Research prototype only. Not a medical device. Not for clinical use."""
import os
from glob import glob

import streamlit as st

import medvision_infer as mvi

# ===== Set these two lines after you upload the checkpoint to Hugging Face =====
HF_REPO_ID = "rayennedr/medvisionai-pcam"
HF_FILENAME = "medvision_pcam_convnext_tiny.pt"     # the exact file name printed by the notebook
# ================================================================================
LOCAL_CHECKPOINT = os.environ.get("MEDVISION_CHECKPOINT")   # optional: test with a local file instead

st.set_page_config(page_title="MedVisionAI", page_icon="🔬")


@st.cache_resource(show_spinner="Loading the model (first start only)...")
def get_predictor():
    if LOCAL_CHECKPOINT:
        return mvi.Predictor.from_checkpoint(LOCAL_CHECKPOINT, device="cpu")
    if HF_REPO_ID.startswith("YOUR-"):
        raise mvi.InferenceError("Set HF_REPO_ID and HF_FILENAME at the top of streamlit_app_pcam.py.")
    return mvi.Predictor.from_hub(HF_REPO_ID, HF_FILENAME, device="cpu")


st.title("MedVisionAI: lymph node tissue patch check")
st.write(
    "A research prototype. Upload a small H&E-stained lymph node tissue patch (like the examples, about 96 x 96 px). "
    "It scores how likely the **centre of the patch** contains metastatic tumor tissue, and shows where the model looked."
)
st.warning(
    "Not a medical device. Do not use it for diagnosis. It was trained on one public dataset (PatchCamelyon: lymph node "
    "sections from two scanning centers). Other tissues, stains, scanners or image scales can give confident but wrong "
    "answers. The score is not a calibrated probability."
)

try:
    predictor = get_predictor()
except mvi.InferenceError as e:
    st.error(str(e))
    st.stop()
except Exception as e:
    st.error(f"Could not start the model: {e}")
    st.stop()

examples = sorted(glob("examples_pcam/*.png"))
ex_map = {os.path.basename(p)[:-4].replace("_", " "): p for p in examples}

uploaded = st.file_uploader("Upload a patch image", type=["png", "jpg", "jpeg", "tif", "tiff", "bmp", "webp"])
choice = (st.selectbox("Or try an example (held-out test images, the name shows the true label)",
                       ["(none)"] + list(ex_map)) if ex_map else "(none)")

source = None
if uploaded is not None:
    if hasattr(uploaded, "seek"):
        uploaded.seek(0)
    source = uploaded
elif choice != "(none)":
    source = ex_map[choice]

if source is not None:
    try:
        img = mvi.load_image(source)
        if max(img.size) > 256:
            st.info("This image is large. The model was trained on 96 x 96 px patches, so it will be shrunk "
                    "and the result may be unreliable.")
        result, overlay = predictor.explain(img)
    except mvi.InferenceError as e:
        st.error(str(e))
        st.stop()

    col1, col2 = st.columns(2)
    with col1:
        st.image(img.resize((256, 256)), caption="Input patch", width=256)
    with col2:
        st.image(overlay, caption="Where the model looked (evidence for Cancer)", width=256)

    st.subheader(f"Prediction: {result['label']}")
    st.write(f"Cancer score: **{result['cancer_score']:.3f}**   |   decision threshold: **{result['threshold']:.3f}** "
             "(score at or above the threshold means Cancer)")
    st.progress(min(max(result["cancer_score"], 0.0), 1.0))

with st.expander("About this model and how it was evaluated"):
    meta = predictor.meta or {}
    st.write(f"Architecture: **{predictor.arch}**, input size {predictor.img_size} px.")
    st.write(f"Checkpoint: `{predictor.source}`")
    if meta.get("smoke_test"):
        st.error("This checkpoint comes from a SMOKE TEST on fake data. Do not use it.")
    tm, ci = meta.get("test_metrics"), meta.get("test_ci95", {})
    if tm:
        st.write("Held-out PatchCamelyon test split, measured when the model was trained (95% intervals in brackets):")
        for key, name in [("recall", "Sensitivity (cancer found)"), ("specificity", "Specificity (non-cancer found)"),
                          ("auc", "ROC-AUC"), ("precision", "Precision"), ("f1", "F1")]:
            if key in tm:
                rng = f" [{ci[key][0]:.3f}, {ci[key][1]:.3f}]" if key in ci else ""
                st.write(f"- {name}: {tm[key]:.3f}{rng}")
        st.caption("One test split, patches from the same slides are correlated (intervals are too narrow), "
                   "classes were balanced 50/50 in this dataset, and the score is not a calibrated probability.")
    st.write(meta.get("intended_use", "Research prototype only."))
