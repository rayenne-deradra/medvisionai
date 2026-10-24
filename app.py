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
from medvision.auth import DEVICE_PARAM, read_device_token, restore_script, storage_script
from medvision.config import get_secret, get_secret_table
from medvision.ui.shared import init_state, ss
from medvision.ui.theme import CSS, account_html, disclaimer_html, sidebar_brand_html

st.set_page_config(page_title="MedVisionAI", page_icon=":material/monitor_heart:", layout="wide",
                   initial_sidebar_state="auto")
st.markdown(CSS, unsafe_allow_html=True)
init_state()

# Licensing is on as soon as ACTIVATION_SECRET and at least one [activation_codes.*] entry exist in the secrets.
licensing_on = bool(get_secret("ACTIVATION_SECRET") and get_secret_table("activation_codes"))
licence = ss.get("licence")
if licensing_on and not licence and not ss.get("signed_out"):
    # "Remember this device": the browser hands over its saved, signed token once via ?device=... (see restore_script)
    token = st.query_params.get(DEVICE_PARAM)
    if token:
        st.query_params.pop(DEVICE_PARAM)    # never leave the token in the address bar
        remembered = read_device_token(token, get_secret("ACTIVATION_SECRET") or "", get_secret_table("activation_codes"))
        if remembered:                       # re-checked against the licence list: revoked/expired licences fail
            licence = ss.licence = remembered.to_dict() | {"signed_in": "remembered device"}
        else:
            ss.device_action = ""            # stale or invalid token: delete it from the browser
    else:
        ss.try_restore = True
if licence and licence.get("expires") and date.fromisoformat(licence["expires"]) < date.today():
    ss.pop("licence", None)                 # licence expired during the session
    licence = None


def sign_out() -> None:
    for key in ("licence", "cases", "case_order", "current_case", "conversations", "active_chat"):
        ss.pop(key, None)                   # also clears the analyses and chats of this session
    ss.signed_out = True                    # do not sign in again from the saved token in this session
    ss.device_action = ""                   # and delete the remember-device token from the browser


login_page = st.Page("views/login.py", title="Sign in", icon=":material/login:", url_path="login")
analysis_page = st.Page("views/analysis.py", title="Tissue analysis", icon=":material/biotech:", default=True)
assistant_page = st.Page("views/assistant.py", title="AI Assistant", icon=":material/forum:")
consult_page = st.Page("views/consult.py", title="Book a consultation", icon=":material/event:", url_path="consult")
# All pages are always registered (so bookmarked addresses never show "page not found"); the menu is drawn below.
page = st.navigation([analysis_page, assistant_page, consult_page, login_page], position="hidden")
signed_in = bool(licence) or not licensing_on
app_pages = {pg.url_path: pg for pg in (analysis_page, assistant_page, consult_page)}
if not signed_in and page.url_path != login_page.url_path:
    # remember where the visitor wanted to go, so sign-in (code or remembered device) leads there
    st.switch_page(login_page, query_params={"next": page.url_path} if page.url_path else None)
if signed_in and page.url_path == login_page.url_path:
    st.switch_page(app_pages.get(st.query_params.get("next", ""), analysis_page))

if "device_action" in ss:                  # save or delete the remember-device token (runs after any redirect)
    st.html(storage_script(ss.pop("device_action") or None), unsafe_allow_javascript=True)
elif ss.pop("try_restore", False) and not signed_in:
    st.html(restore_script(), unsafe_allow_javascript=True)

with st.sidebar:
    st.markdown(sidebar_brand_html(), unsafe_allow_html=True)
    with st.container(key="mv_nav"):
        for pg in ([analysis_page, assistant_page, consult_page] if signed_in else [login_page]):
            st.page_link(pg, label=pg.title, icon=pg.icon)
page.run()

with st.sidebar:
    if licence:
        st.markdown(account_html(licence), unsafe_allow_html=True)
        st.button("Sign out", icon=":material/logout:", type="tertiary", width="stretch", on_click=sign_out)
    elif not licensing_on:
        st.caption("Demo mode: licensing is not configured on this server, so no sign-in is required.")
    st.markdown(disclaimer_html(DISCLAIMER), unsafe_allow_html=True)
