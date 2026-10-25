"""Platform page: what MedVisionAI does, the two imaging modalities and their validated results."""
from __future__ import annotations

import streamlit as st

from medvision.ui.theme import hero_html, section_html

st.markdown(hero_html(), unsafe_allow_html=True)

st.markdown(section_html("Imaging modalities", "each upload goes to a model validated for that modality"),
            unsafe_allow_html=True)
MODALITIES = [
    ("brain", "views/brain.py", "🧠", "Neuro-oncology · BRISC 2025", "Brain tumour MRI",
     "Classifies T1 MRI slices as glioma, meningioma, pituitary tumour or no tumour with a 5-fold EfficientNet-B0 "
     "ensemble, compared live with ConvNeXt-Tiny and ResNet-18. A U-Net outlines the lesion, classical radiomics give "
     "a second opinion, and a 0–100 triage score suggests how soon a specialist should review the case.",
     (("99.3%", "ensemble test accuracy"), ("0.994", "macro F1, 4 classes"), ("10,793", "MRI slices studied")),
     "Open brain tumour MRI"),
    ("crc", "views/analysis.py", "🔬", "Histopathology · NCT-CRC-HE-100K", "Colorectal tissue",
     "Classifies H&E patches into 9 colorectal tissue types with the Phikon pathology foundation model and a "
     "temperature-calibrated head. Large images are scanned tile by tile, non-H&E images are refused, and a Grad-CAM "
     "overlay shows which regions drove the result.",
     (("95.1%", "9-class accuracy"), ("100%", "tumour recall"), ("50", "unseen test patients")),
     "Open colorectal tissue"),
]
cols = st.columns(2, gap="medium")
for col, (key, target, icon, label, title, text, kpis, cta) in zip(cols, MODALITIES):
    with col, st.container(key=f"mv_mod_{key}"):
        st.markdown(f'<div class="mv-mod"><div class="top"><div class="ic">{icon}</div>'
                    f'<span class="mv-dept">{label}</span></div><h3>{title}</h3><p>{text}</p><div class="kp">'
                    + "".join(f"<div><b>{v}</b><span>{k}</span></div>" for v, k in kpis) + "</div></div>",
                    unsafe_allow_html=True)
        st.page_link(target, label=cta, icon=":material/arrow_forward:")

st.markdown(section_html("Around every analysis", "explain, discuss, refer"), unsafe_allow_html=True)
FEATURES = [
    ("xai", "Explainable AI", "Heatmaps and lesion outlines",
     "Grad-CAM for tissue patches; U-Net lesion contours, probability maps and saliency for MRI. They show where the "
     "model looked, not proof of disease.", "views/brain.py", "See an example"),
    ("chat", "AI Assistant", "Discuss a case",
     "Attach any brain MRI or tissue analysis and ask about it. The assistant answers medical and health questions "
     "only, and never gives a diagnosis.", "views/assistant.py", "Open the assistant"),
    ("care", "Triage", "Specialist referrals",
     "Request an in-person consultation with neuro-oncology, neuroradiology or GI pathology. Urgent requests go "
     "to the top of the coordinator's queue.", "views/appointments.py", "Book an appointment"),
]
cols = st.columns(3, gap="medium")
for col, (key, k, title, text, target, cta) in zip(cols, FEATURES):
    with col, st.container(key=f"mv_feat_{key}"):
        st.markdown(f'<div class="mv-feat"><div class="k">{k}</div><h4>{title}</h4><p>{text}</p></div>',
                    unsafe_allow_html=True)
        st.page_link(target, label=cta, icon=":material/arrow_forward:")

st.page_link("views/benchmarks.py", label="How the models were validated: Study & benchmarks",
             icon=":material/monitoring:")
