"""MedVisionAI: Clinical Intelligence Platform for medical imaging.

Pages (all listed in the left panel):
  Platform             overview of the modalities, models and results
  Brain tumour MRI     BRISC 2025 CNN ensemble, U-Net lesion segmentation, classical radiomics, triage risk score
  Colorectal tissue    upload an H&E image -> 9-class tissue classification, calibrated confidence, Grad-CAM overlay
  AI Assistant         ChatGPT-style chat (OpenAI / Gemini) about analysed or attached images; medical questions only
  Book an appointment  in-person specialist consultation, urgent requests first
  Triage queue         hospital coordinators only
  Study & benchmarks   validation tables and figures for both modalities
  Activation           licence activation with an activation code; the app opens here until a valid code is entered

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
from medvision.ui.theme import CSS, account_html, disclaimer_html, footer_html, sidebar_brand_html

st.set_page_config(page_title="MedVisionAI", page_icon=":material/monitor_heart:", layout="wide",
                   initial_sidebar_state="auto")
st.markdown(CSS, unsafe_allow_html=True)
init_state()

# Licensing is on as soon as ACTIVATION_SECRET and at least one [activation_codes.*] entry exist in the secrets.
licensing_on = bool(get_secret("ACTIVATION_SECRET") and get_secret_table("activation_codes"))
ss.licensing_on = licensing_on
licence = ss.get("licence")
if licensing_on and not licence and not ss.get("signed_out"):
    # "Remember this device": the browser hands over its saved, signed token once via ?device=... (see restore_script)
    token = st.query_params.get(DEVICE_PARAM)
    if token:
        st.query_params.pop(DEVICE_PARAM)    # never leave the token in the address bar
        remembered = read_device_token(token, get_secret("ACTIVATION_SECRET") or "", get_secret_table("activation_codes"))
        if remembered:                       # re-checked against the licence list: revoked/expired licences fail
            licence = ss.licence = remembered.to_dict() | {"signed_in": "remembered device"}
            ss.just_activated = True         # views/login.py then opens the page the visitor asked for
        else:
            ss.device_action = ""            # stale or invalid token: delete it from the browser
    else:
        ss.try_restore = True
if licence and licence.get("expires") and date.fromisoformat(licence["expires"]) < date.today():
    ss.pop("licence", None)                 # licence expired during the session
    licence = None


def sign_out() -> None:
    for key in ("licence", "cases", "case_order", "current_case", "current_brain", "conversations", "active_chat"):
        ss.pop(key, None)                   # also clears the analyses and chats of this session
    ss.signed_out = True                    # do not sign in again from the saved token in this session
    ss.device_action = ""                   # and delete the remember-device token from the browser


overview_page = st.Page("views/overview.py", title="Platform", icon=":material/dashboard:", url_path="platform",
                        default=True)
brain_page = st.Page("views/brain.py", title="Brain tumour MRI", icon=":material/neurology:", url_path="brain-mri")
analysis_page = st.Page("views/analysis.py", title="Colorectal tissue", icon=":material/biotech:",
                        url_path="colorectal")
assistant_page = st.Page("views/assistant.py", title="AI Assistant", icon=":material/forum:", url_path="assistant")
appointments_page = st.Page("views/appointments.py", title="Book an appointment", icon=":material/event:",
                            url_path="appointments")
triage_page = st.Page("views/triage.py", title="Triage queue", icon=":material/clinical_notes:", url_path="triage")
benchmarks_page = st.Page("views/benchmarks.py", title="Study & benchmarks", icon=":material/monitoring:",
                          url_path="benchmarks")
login_page = st.Page("views/login.py", title="Activation", icon=":material/key:", url_path="login")
# All pages are always registered (so bookmarked addresses never show "page not found"); the menu is drawn below.
page = st.navigation([overview_page, brain_page, analysis_page, assistant_page, appointments_page, triage_page,
                      benchmarks_page, login_page], position="hidden")
signed_in = bool(licence) or not licensing_on
is_coordinator = bool(licence) and licence.get("role") == "coordinator"
public = {overview_page.url_path, login_page.url_path}       # readable before activation
if page.url_path != login_page.url_path:
    ss.pop("just_activated", None)          # only the Activation page redirects after signing in
if not signed_in and page.url_path not in public:
    # remember where the visitor wanted to go, so activation (code or remembered device) leads there
    st.switch_page(login_page, query_params={"next": page.url_path})
if page.url_path == triage_page.url_path and not is_coordinator:
    st.switch_page(appointments_page)

if "device_action" in ss:                  # save or delete the remember-device token (runs after any redirect)
    st.html(storage_script(ss.pop("device_action") or None), unsafe_allow_javascript=True)
elif ss.pop("try_restore", False) and not signed_in:
    st.html(restore_script(), unsafe_allow_javascript=True)

NAV = [   # left panel: (section, pages)
    ("Overview", [overview_page]),
    ("Imaging analysis", [brain_page, analysis_page]),
    ("Clinical care", [assistant_page, appointments_page] + ([triage_page] if is_coordinator else [])),
    ("Research", [benchmarks_page]),
    ("Account", [login_page]),
]
with st.sidebar:
    st.markdown(sidebar_brand_html(), unsafe_allow_html=True)
    with st.container(key="mv_nav"):
        for section, pages in NAV:
            st.markdown(f'<div class="mv-navsec">{section}</div>', unsafe_allow_html=True)
            for pg in pages:
                locked = not signed_in and pg.url_path not in public
                st.page_link(pg, label=pg.title, icon=":material/lock:" if locked else pg.icon,
                             help="Enter an activation code to open this page" if locked else None)
page.run()
st.markdown(footer_html(), unsafe_allow_html=True)

with st.sidebar:
    if licence:
        st.markdown(account_html(licence), unsafe_allow_html=True)
        st.button("Sign out", icon=":material/logout:", type="tertiary", width="stretch", on_click=sign_out)
    elif not licensing_on:
        st.caption("Demo mode: licensing is not configured on this server, so no activation is required.")
    st.markdown(disclaimer_html(DISCLAIMER), unsafe_allow_html=True)
