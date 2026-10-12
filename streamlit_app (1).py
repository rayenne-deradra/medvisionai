"""MedVisionAI demo (Streamlit): tumor vs other tissue on H&E colorectal tissue patches.
Research prototype only. Not a medical device. Not for clinical use."""
import os
from glob import glob

import numpy as np
import streamlit as st
import torch
import torch.nn as nn
from PIL import Image
from torchvision import models, transforms

SIZE = 64  # the model was trained on 64 x 64 patches
MODEL_FILE = "model_small.pt"

st.set_page_config(page_title="MedVisionAI", page_icon="🔬")

prep = transforms.Compose([
    transforms.Resize((SIZE, SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])


@st.cache_resource
def load_model():
    m = models.resnet18(weights=None)
    m.fc = nn.Linear(m.fc.in_features, 2)
    sd = torch.load(MODEL_FILE, map_location="cpu")
    sd = {k: (v.float() if v.is_floating_point() else v) for k, v in sd.items()}
    m.load_state_dict(sd)
    m.eval()
    return m


def forward_with_features(m, x):
    """Same as m(x) but also returns layer3 features for the heatmap."""
    x = m.maxpool(m.relu(m.bn1(m.conv1(x))))
    x = m.layer2(m.layer1(x))
    feats = m.layer3(x)
    out = m.fc(torch.flatten(m.avgpool(m.layer4(feats)), 1))
    return out, feats


def make_overlay(img, cam):
    """Blend a red/yellow heatmap on top of the patch."""
    base = np.asarray(img.resize((256, 256)), dtype=np.float32) / 255
    c = Image.fromarray((cam * 255).astype(np.uint8)).resize((256, 256), Image.BICUBIC)
    c = np.asarray(c, dtype=np.float32) / 255
    heat = np.stack([np.clip(2 * c, 0, 1), np.clip(2 * c - 1, 0, 1), np.zeros_like(c)], -1)
    a = (0.6 * c)[..., None]
    return Image.fromarray((((1 - a) * base + a * heat) * 255).astype(np.uint8))


def predict(img):
    model = load_model()
    x = prep(img).unsqueeze(0)
    out, feats = forward_with_features(model, x)
    probs = torch.softmax(out, 1)[0].detach().numpy()
    # Grad-CAM for the "tumor" class (index 1)
    grads = torch.autograd.grad(out[0, 1], feats)[0]
    weights = grads.mean(dim=(2, 3), keepdim=True)
    cam = torch.relu((weights * feats).sum(1))[0].detach().numpy()
    cam = cam / cam.max() if cam.max() > 0 else cam
    cam = cam * float(probs[1])  # faint when the model sees little tumor evidence
    return float(probs[1]), make_overlay(img, cam)


st.title("MedVisionAI: tumor tissue patch explorer")
st.write(
    "A research prototype. Pick an example or upload a small H&E-stained colorectal tissue "
    "patch. It says whether the patch looks like **tumor epithelium** or **other tissue**. "
    "The heatmap shows which parts pushed the model toward \"tumor\" (red and yellow = stronger)."
)
st.warning(
    "Not a medical device. Do not use it for diagnosis. The model was trained on 64 x 64 "
    "patches, so the heatmap is coarse. A normal photo (not histology) will still get an "
    "answer, but that answer means nothing."
)

examples = sorted(glob("examples/*.png"))
names = {os.path.basename(p).replace(".png", "").replace("_", " "): p for p in examples}

uploaded = st.file_uploader("Upload a tissue patch", type=["png", "jpg", "jpeg"])
choice = st.selectbox("Or try an example", ["(none)"] + list(names)) if names else "(none)"

img = None
if uploaded is not None:
    img = Image.open(uploaded).convert("RGB")
elif choice != "(none)":
    img = Image.open(names[choice]).convert("RGB")

if img is not None:
    p_tumor, overlay = predict(img)
    col1, col2 = st.columns(2)
    with col1:
        st.image(img.resize((256, 256)), caption="Input patch", width=256)
    with col2:
        st.image(overlay, caption="Heatmap (evidence for tumor)", width=256)
    st.subheader("Prediction")
    st.write(f"Tumor epithelium: **{p_tumor:.1%}**   |   Other tissue: **{1 - p_tumor:.1%}**")
    st.progress(min(max(p_tumor, 0.0), 1.0))
