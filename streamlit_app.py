"""MedVisionAI demo (Streamlit): 9-class colorectal tissue patch classifier with Grad-CAM.
Research prototype only. Not a medical device. Not for clinical use."""

import streamlit as st
import torch
from huggingface_hub import hf_hub_download

MODEL_REPO_ID = "rayennedr/medvisionai-weights"


@st.cache_resource(show_spinner="Downloading and loading MedVisionAI model...")
def get_model_path():
    return hf_hub_download(
        repo_id=MODEL_REPO_ID,
        filename=MODEL_FILENAME,
        repo_type="model",
    )

model_path = get_model_path()
device = torch.device("cpu")

st.success("Model file downloaded successfully!")
st.caption(f"Model file: {model_path}")

import os
import urllib.request
from glob import glob

import numpy as np
import pandas as pd
import streamlit as st
import torch
import torch.nn as nn
from PIL import Image
from torchvision import models, transforms

# Paste the link you copied from your GitHub release (right-click the model file, Copy link address)
MODEL_URL = "PASTE_THE_LINK_FROM_YOUR_GITHUB_RELEASE_HERE"
MODEL_FILE = "model_v2.pt"
CONFIDENCE_MIN = 0.60   # below this the app says it is not confident
TEMPERATURE = 1.0       # kept at 1: a value fitted on validation data tends to be overconfident on new images

st.set_page_config(page_title="MedVisionAI", page_icon="🔬")


@st.cache_resource
def load_model():
    if not os.path.exists(MODEL_FILE):
        if MODEL_URL.startswith("PASTE"):
            st.error("Model link missing. Put the GitHub release link in MODEL_URL in streamlit_app.py.")
            st.stop()
        with st.spinner("Downloading the model (first start only, about a minute)..."):
            urllib.request.urlretrieve(MODEL_URL, MODEL_FILE)
    ck = torch.load(MODEL_FILE, map_location="cpu")
    m = models.convnext_tiny(weights=None)
    m.classifier[2] = nn.Linear(m.classifier[2].in_features, 9)
    sd = {k: (v.float() if v.is_floating_point() else v) for k, v in ck["state"].items()}
    m.load_state_dict(sd)
    m.eval()
    return m, ck["names"], ck["size"]


def forward_with_features(m, x):
    """Same as m(x) but also returns stage-3 features for the heatmap."""
    f = x
    feats = None
    for i, layer in enumerate(m.features):
        f = layer(f)
        if i == 5:
            feats = f
    return m.classifier(m.avgpool(f)), feats


def make_overlay(img, cam):
    """Blend a red/yellow heatmap on top of the patch."""
    base = np.asarray(img.resize((256, 256)), dtype=np.float32) / 255
    c = Image.fromarray((cam * 255).astype(np.uint8)).resize((256, 256), Image.BICUBIC)
    c = np.asarray(c, dtype=np.float32) / 255
    heat = np.stack([np.clip(2 * c, 0, 1), np.clip(2 * c - 1, 0, 1), np.zeros_like(c)], -1)
    a = (0.6 * c)[..., None]
    return Image.fromarray((((1 - a) * base + a * heat) * 255).astype(np.uint8))


def predict(img):
    model, names, size = load_model()
    tf = transforms.Compose([
        transforms.Resize((size, size)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    x = tf(img).unsqueeze(0)
    out, feats = forward_with_features(model, x)
    probs = torch.softmax(out / TEMPERATURE, 1)[0].detach().numpy()
    top = int(probs.argmax())
    # Grad-CAM for the predicted class
    grads = torch.autograd.grad(out[0, top], feats)[0]
    weights = grads.mean(dim=(2, 3), keepdim=True)
    cam = torch.relu((weights * feats).sum(1))[0].detach().numpy()
    cam = cam / cam.max() if cam.max() > 0 else cam
    return names, probs, top, make_overlay(img, cam)


st.title("MedVisionAI: tissue patch explorer")
st.write(
    "A research prototype. Pick an example or upload a small H&E-stained colorectal tissue patch. "
    "It says which of 9 tissue types the patch looks like, including **tumor epithelium**, "
    "and shows a heatmap of where the model looked."
)
st.warning(
    "Not a medical device. Do not use it for diagnosis. It was trained on small colorectal patches "
    "from one public dataset. Photos of other kinds, stains or sizes can get a confident but wrong answer. "
    "On an independent test set it was right about 95% of the time. Weakest: cancer-associated stroma "
    "and smooth muscle, which it often mixes up."
)

examples = sorted(glob("examples/*.png"))
ex_names = {os.path.basename(p).replace(".png", "").replace("_", " "): p for p in examples}

uploaded = st.file_uploader("Upload a tissue patch", type=["png", "jpg", "jpeg"])
choice = st.selectbox("Or try an example", ["(none)"] + list(ex_names)) if ex_names else "(none)"

img = None
if uploaded is not None:
    img = Image.open(uploaded).convert("RGB")
elif choice != "(none)":
    img = Image.open(ex_names[choice]).convert("RGB")

if img is not None:
    if max(img.size) > 300:
        st.info("This image is large. The model works best on small patches (about 64 to 128 px). "
                "It will be shrunk, and the result may be less reliable.")
    names, probs, top, overlay = predict(img)
    col1, col2 = st.columns(2)
    with col1:
        st.image(img.resize((256, 256)), caption="Input patch", width=256)
    with col2:
        st.image(overlay, caption=f"Where the model looked for: {names[top]}", width=256)

    st.subheader("Prediction")
    st.write(f"**{names[top].capitalize()}**  ({probs[top]:.0%} confidence)")
    tumor_idx = [i for i, n in enumerate(names) if "adenocarcinoma" in n.lower()][0]
    st.write(f"Tumor epithelium probability: **{probs[tumor_idx]:.0%}**")
    if probs[top] < CONFIDENCE_MIN:
        st.warning("The model is not confident about this patch. Do not trust this result.")
    st.bar_chart(pd.DataFrame({"probability": probs}, index=[n.capitalize() for n in names]))
