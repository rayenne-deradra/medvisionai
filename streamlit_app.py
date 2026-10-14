
"""MedVisionAI: 9-class colorectal tissue patch classifier with Grad-CAM.
Research prototype only. Not a medical device. Not for clinical use.
"""

import os
from glob import glob

import numpy as np
import pandas as pd
import streamlit as st
import torch
import torch.nn as nn
from PIL import Image
from torchvision import models, transforms
from huggingface_hub import hf_hub_download

# Configure the page before other Streamlit UI commands.
st.set_page_config(page_title="MedVisionAI", page_icon="🔬")

# Hugging Face model repository
MODEL_REPO_ID = "rayennedr/medvisionai-weights"
MODEL_FILENAME = "model_v2.pt"  # Change if your uploaded filename differs

CONFIDENCE_MIN = 0.60
TEMPERATURE = 1.0

device = torch.device("cpu")


@st.cache_resource(show_spinner="Downloading MedVisionAI model...")
def load_model():
    # Download the checkpoint from Hugging Face.
    model_path = hf_hub_download(
        repo_id=MODEL_REPO_ID,
        filename=MODEL_FILENAME,
        repo_type="model",
    )

    # This assumes the checkpoint is a trusted file you created.
    # weights_only=False supports checkpoints containing metadata such as lists.
    try:
        checkpoint = torch.load(
            model_path,
            map_location="cpu",
            weights_only=False,
        )
    except TypeError:
        # Compatibility fallback for older PyTorch versions.
        checkpoint = torch.load(model_path, map_location="cpu")

    required = {"state", "names", "size"}
    if not isinstance(checkpoint, dict) or not required.issubset(checkpoint):
        raise ValueError(
            "Unexpected checkpoint format. Expected a dictionary containing "
            "'state', 'names', and 'size'."
        )

    # Rebuild the same architecture used during training.
    model = models.convnext_tiny(weights=None)
    model.classifier[2] = nn.Linear(
        model.classifier[2].in_features, 9
    )

    state_dict = {
        key: value.float() if value.is_floating_point() else value
        for key, value in checkpoint["state"].items()
    }
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()

    names = checkpoint["names"]
    size = int(checkpoint["size"])

    if len(names) != 9:
        raise ValueError("The checkpoint must contain exactly 9 class names.")

    return model, names, size


def forward_with_features(model, x):
    """Return logits and intermediate features for Grad-CAM."""
    features = x
    cam_features = None

    for index, layer in enumerate(model.features):
        features = layer(features)
        if index == 5:
            cam_features = features

    logits = model.classifier(model.avgpool(features))
    return logits, cam_features


def make_overlay(image, cam):
    """Blend a red/yellow activation heatmap with the input patch."""
    base = np.asarray(
        image.resize((256, 256)), dtype=np.float32
    ) / 255.0

    cam_image = Image.fromarray(
        (cam * 255).astype(np.uint8)
    ).resize((256, 256), Image.Resampling.BICUBIC)

    activation = np.asarray(cam_image, dtype=np.float32) / 255.0

    heat = np.stack(
        [
            np.clip(2 * activation, 0, 1),
            np.clip(2 * activation - 1, 0, 1),
            np.zeros_like(activation),
        ],
        axis=-1,
    )

    alpha = (0.6 * activation)[..., None]
    blended = ((1 - alpha) * base + alpha * heat) * 255

    return Image.fromarray(np.clip(blended, 0, 255).astype(np.uint8))


def predict(image):
    model, names, size = load_model()

    preprocessing = transforms.Compose([
        transforms.Resize((size, size)),
        transforms.ToTensor(),
        transforms.Normalize(
            [0.485, 0.456, 0.406],
            [0.229, 0.224, 0.225],
        ),
    ])

    x = preprocessing(image).unsqueeze(0).to(device)

    # Do not use torch.no_grad() here: Grad-CAM needs gradients.
    model.zero_grad(set_to_none=True)
    logits, features = forward_with_features(model, x)

    if features is None:
        raise RuntimeError("Grad-CAM feature layer was not found.")

    predicted_index = int(logits.argmax(dim=1).item())
    gradients = torch.autograd.grad(
        logits[0, predicted_index], features
    )[0]

    weights = gradients.mean(dim=(2, 3), keepdim=True)
    cam = torch.relu((weights * features).sum(dim=1))[0]
    cam = cam.detach().cpu().numpy()

    if cam.max() > 0:
        cam = cam / cam.max()

    probabilities = torch.softmax(
        logits / TEMPERATURE, dim=1
    )[0].detach().cpu().numpy()

    top = int(probabilities.argmax())

    return names, probabilities, top, make_overlay(image, cam)


st.title("MedVisionAI: tissue patch explorer")

st.write(
    "A research prototype for exploring H&E-stained colorectal tissue patches. "
    "It predicts one of nine tissue classes and displays a Grad-CAM heatmap."
)

st.warning(
    "Not a medical device. Do not use for diagnosis or clinical decisions. "
    "Predictions may be unreliable on images from different datasets, stains, "
    "magnifications, or tissue types. Confidence scores are not proof of accuracy."
)

# Find example PNG images committed to the GitHub repository.
examples = sorted(glob("examples/*.png"))
example_names = {
    os.path.basename(path).rsplit(".", 1)[0].replace("_", " "): path
    for path in examples
}

uploaded = st.file_uploader(
    "Upload a tissue patch",
    type=["png", "jpg", "jpeg"],
)

if example_names:
    choice = st.selectbox(
        "Or try an example",
        ["(none)"] + list(example_names.keys()),
    )
else:
    choice = "(none)"
    st.info("No example PNGs found in the examples/ folder.")

image = None

if uploaded is not None:
    try:
        image = Image.open(uploaded).convert("RGB")
    except Exception:
        st.error("Could not open the uploaded image.")
elif choice != "(none)":
    image = Image.open(example_names[choice]).convert("RGB")

if image is not None:
    if max(image.size) > 300:
        st.info(
            "This image will be resized to the model input dimensions. "
            "Large images may differ from the small patches used during training."
        )

    try:
        with st.spinner("Analyzing image..."):
            names, probabilities, top, overlay = predict(image)
    except Exception as error:
        st.error(
            "Prediction failed. Check the model checkpoint, class labels, "
            "and training architecture."
        )
        with st.expander("Technical details"):
            st.code(str(error))
        st.stop()

    col1, col2 = st.columns(2)

    with col1:
        st.image(
            image.resize((256, 256)),
            caption="Input patch",
            width=256,
        )

    with col2:
        st.image(
            overlay,
            caption=f"Grad-CAM: {names[top]}",
            width=256,
        )

    st.subheader("Prediction")
    st.write(f"**{str(names[top]).capitalize()}** — {probabilities[top]:.1%} model confidence")

    tumor_indices = [
        i for i, name in enumerate(names)
        if "adenocarcinoma" in str(name).lower()
    ]

    if tumor_indices:
        tumor_probability = float(probabilities[tumor_indices].sum())
        st.write(
            f"Tumor-class probability: **{tumor_probability:.1%}**"
        )

    if probabilities[top] < CONFIDENCE_MIN:
        st.warning(
            "The model's top-class confidence is below the configured threshold. "
            "This does not establish whether the image is benign or cancerous."
        )

    chart = pd.DataFrame(
        {"Probability": probabilities},
        index=[str(name).capitalize() for name in names],
    )
    st.bar_chart(chart)
