"""Platform page, laid out like a clinical atlas: headline next to a real result on a light box, key figures, a
numbered index of the platform, and plates that open a sample case in one click."""
from __future__ import annotations

import streamlit as st

from medvision.brain import SAMPLES_DIR as BRAIN_SAMPLES
from medvision.config import EXAMPLES_DIR
from medvision.ui.shared import ss
from medvision.ui.theme import (atlas_html, figures_html, lightbox_html, masthead_html, plate_html, row_html,
                                section_html, thumb_uri)

BRAIN, CRC = "views/brain.py", "views/analysis.py"

st.markdown(masthead_html(), unsafe_allow_html=True)
left, right = st.columns([1.15, 1], gap="large")
with left:
    st.markdown(atlas_html(), unsafe_allow_html=True)
    with st.container(key="mv_cta2"):
        c1, c2 = st.columns(2)
        if c1.button("Read a brain MRI  →", key="cta_brain"):
            st.switch_page(BRAIN)
        if c2.button("Read a tissue slide  →", key="cta_crc"):
            st.switch_page(CRC)
with right:
    st.markdown(lightbox_html(), unsafe_allow_html=True)

st.markdown(figures_html(), unsafe_allow_html=True)

st.markdown(section_html("Index", "five rooms, one platform"), unsafe_allow_html=True)
INDEX = [
    ("I", "Brain tumour MRI", "Neuro-oncology · BRISC 2025", BRAIN,
     "Four CNNs read a T1 slice; a U-Net outlines the lesion; classical radiomics second-guess them; a 0–100 score "
     "suggests how soon a specialist should look."),
    ("II", "Colorectal tissue", "Histopathology · NCT-CRC-HE-100K", CRC,
     "The Phikon foundation model sorts H&E patches into 9 tissue types with calibrated confidence and a Grad-CAM map; "
     "large slides are read tile by tile."),
    ("III", "AI Assistant", "Medical questions only", "views/assistant.py",
     "Attach any case and ask about it. It explains, it flags uncertainty, it never diagnoses."),
    ("IV", "Appointments & triage", "Urgent first", "views/appointments.py",
     "Refer a case to neuro-oncology, neuroradiology or GI pathology; coordinators see the most urgent requests on top."),
    ("V", "Study & benchmarks", "Validation", "views/benchmarks.py",
     "Every number on this page, with the tables and figures it came from."),
]
for i, (n, title, kicker, target, text) in enumerate(INDEX, 1):
    with st.container(key=f"mv_row_{i}"):
        st.markdown(row_html(n, title, kicker, text), unsafe_allow_html=True)
        if st.button(f"Open {title}", key=f"row_{i}"):
            st.switch_page(target)

st.markdown(section_html("Plates", "open a real test case in one click"), unsafe_allow_html=True)
PLATES = [
    ("I", "brain", BRAIN_SAMPLES / "glioma_axial_t1.jpg", "Glioma, axial T1", "Brain MRI"),
    ("II", "crc", EXAMPLES_DIR / "test_colorectal_adenocarcinoma_epithelium_0.png", "Adenocarcinoma", "H&E patch"),
    ("III", "brain", BRAIN_SAMPLES / "pituitary_coronal_sample.png", "Pituitary, coronal", "Brain MRI"),
]
cols = st.columns(3, gap="medium")
for col, (num, kind, path, title, tag) in zip(cols, PLATES):
    with col, st.container(key=f"mv_plate_{num}"):
        st.markdown(plate_html(thumb_uri(str(path), 480), num, title, tag), unsafe_allow_html=True)
        if st.button(f"Analyse {title}", key=f"plate_{num}"):
            if kind == "brain":
                ss.pending_brain_example = str(path)
                st.switch_page(BRAIN)
            ss.pending_example = str(path)
            st.switch_page(CRC)
