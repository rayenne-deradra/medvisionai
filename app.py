"""MedVisionAI: colorectal tissue analysis with an AI assistant.

Pages:
  Sign in          licence activation with an activation code (shown until a valid code is entered)
  Tissue analysis  upload an H&E image -> 9-class colorectal tissue classification, calibrated confidence scores,
                   tumour finding, classification report and Grad-CAM overlay
  AI Assistant     ChatGPT-style chat (OpenAI / Gemini) about analysed or attached images; medical questions only

Run:  streamlit run app.py
Research prototype only. Not a medical device. Not for diagnosis.
"""
from __future__ import annotations

from datetime import date

import streamlit as st

from medvision import DISCLAIMER
from medvision.config import ASSETS_DIR, get_secret, get_secret_table
from medvision.ui.shared import init_state, ss
from medvision.ui.theme import CSS, account_html, disclaimer_html

st.set_page_config(page_title="MedVisionAI", page_icon=":material/monitor_heart:", layout="wide",
                   initial_sidebar_state="auto")
st.markdown(CSS, unsafe_allow_html=True)
st.logo(str(ASSETS_DIR / "logo_wide.svg"), icon_image=str(ASSETS_DIR / "logo.svg"), size="large")
init_state()

# Licensing is on as soon as ACTIVATION_SECRET and at least one [activation_codes.*] entry exist in the secrets.
licensing_on = bool(get_secret("ACTIVATION_SECRET") and get_secret_table("activation_codes"))
licence = ss.get("licence")
if licence and licence.get("expires") and date.fromisoformat(licence["expires"]) < date.today():
    ss.pop("licence", None)                 # licence expired during the session
    licence = None


def sign_out() -> None:
    for key in ("licence", "cases", "case_order", "current_case", "conversations", "active_chat"):
        ss.pop(key, None)                   # also clears the analyses and chats of this session


login_page = st.Page("views/login.py", title="Sign in", icon=":material/login:", url_path="login")
analysis_page = st.Page("views/analysis.py", title="Tissue analysis", icon=":material/biotech:", default=True)
assistant_page = st.Page("views/assistant.py", title="AI Assistant", icon=":material/forum:")
# All pages are always registered (so bookmarked addresses never show "page not found"); the menu is drawn below.
page = st.navigation([analysis_page, assistant_page, login_page], position="hidden")
signed_in = bool(licence) or not licensing_on
if not signed_in and page.url_path != login_page.url_path:
    st.switch_page(login_page)
if signed_in and page.url_path == login_page.url_path:
    st.switch_page(analysis_page)

with st.sidebar:
    with st.container(key="mv_nav"):
        for pg in ([analysis_page, assistant_page] if signed_in else [login_page]):
            st.page_link(pg, label=pg.title, icon=pg.icon)
page.run()

with st.sidebar:
    if licence:
        st.markdown(account_html(licence), unsafe_allow_html=True)
        st.button("Sign out", icon=":material/logout:", type="tertiary", width="stretch", on_click=sign_out)
    elif not licensing_on:
        st.caption("Demo mode: licensing is not configured on this server, so no sign-in is required.")
    st.markdown(disclaimer_html(DISCLAIMER), unsafe_allow_html=True)
