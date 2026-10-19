"""MedVisionAI: colorectal tissue analysis with an AI assistant.

Pages:
  Tissue analysis  upload an H&E image -> 9-class colorectal tissue classification, calibrated confidence scores,
                   tumour finding, classification report and Grad-CAM overlay
  AI Assistant     ChatGPT-style chat (OpenAI) about analysed or attached images, or general questions

Run:  streamlit run app.py
Research prototype only. Not a medical device. Not for diagnosis.
"""
from __future__ import annotations

import streamlit as st

from medvision import DISCLAIMER
from medvision.config import ASSETS_DIR
from medvision.ui.shared import init_state
from medvision.ui.theme import CSS, disclaimer_html

st.set_page_config(page_title="MedVisionAI", page_icon=":material/monitor_heart:", layout="wide",
                   initial_sidebar_state="auto")
st.markdown(CSS, unsafe_allow_html=True)
st.logo(str(ASSETS_DIR / "logo_wide.svg"), icon_image=str(ASSETS_DIR / "logo.svg"), size="large")
init_state()

page = st.navigation([
    st.Page("views/analysis.py", title="Tissue analysis", icon=":material/biotech:", default=True),
    st.Page("views/assistant.py", title="AI Assistant", icon=":material/forum:"),
])
page.run()

with st.sidebar:
    st.markdown(disclaimer_html(DISCLAIMER), unsafe_allow_html=True)
