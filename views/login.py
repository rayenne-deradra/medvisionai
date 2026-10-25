"""Activation page (left panel → Account): licence activation with the code an organisation receives after its
subscription is confirmed. Signed in, it shows the active licence and lets you switch to another code."""
from __future__ import annotations

import html
from datetime import datetime, timezone

import streamlit as st

from medvision.auth import ActivationError, AttemptLimiter, make_device_token, verify
from medvision.config import get_secret, get_secret_table
from medvision.ui.shared import ss
from medvision.ui.theme import logo_data_uri

limiter = AttemptLimiter(ss)
PAGES = {"platform": "views/overview.py", "brain-mri": "views/brain.py", "colorectal": "views/analysis.py",
         "assistant": "views/assistant.py", "appointments": "views/appointments.py", "triage": "views/triage.py",
         "benchmarks": "views/benchmarks.py"}


def activate() -> None:
    wait = limiter.locked_for()
    if wait:
        ss.auth_error = f"Too many attempts. Please wait {wait} seconds and try again."
        return
    secret = get_secret("ACTIVATION_SECRET") or ""
    try:
        licence = verify(ss.get("activation_code", ""), secret, get_secret_table("activation_codes"))
    except ActivationError as e:
        limiter.failed()
        ss.auth_error = str(e)
        return
    limiter.succeeded()
    ss.auth_error = None
    if ss.get("licence") and ss.licence.get("licence_id") != licence.licence_id:
        for key in ("cases", "case_order", "current_case", "current_brain", "conversations", "active_chat"):
            ss.pop(key, None)               # another organisation's code: start with a clean session
    ss.licence = licence.to_dict() | {"signed_in": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
    ss.activation_code = ""                 # never keep the code itself in the session
    ss.pop("signed_out", None)
    ss.just_activated = True
    if ss.get("remember_device", True):     # app.py saves the token in the browser on the next run
        ss.device_action = make_device_token(licence, secret)


licensing_on = ss.get("licensing_on", False)
licence = ss.get("licence")
_, mid, _ = st.columns([1, 1.25, 1])
with mid:
    with st.container(key="mv_login"):
        if licence:
            e = html.escape
            role = "Hospital coordinator" if licence.get("role") == "coordinator" else "Clinical user"
            st.markdown(
                f'<div class="mv-login-head"><img src="{logo_data_uri()}" alt="MedVisionAI logo"/>'
                '<div class="brand">MedVisionAI</div><div class="sub">Clinical Intelligence Platform</div></div>'
                '<h2 class="mv-login-title">Licence active</h2>'
                f'<p class="mv-login-text">Licensed to <b>{e(licence.get("organisation", ""))}</b></p>'
                '<div class="mv-req-detail" style="margin:0 0 14px">'
                f'<div class="kv"><span>Plan</span>{e(licence.get("plan") or "—")}</div>'
                f'<div class="kv"><span>Valid until</span>{e(licence.get("expires") or "no expiry")}</div>'
                f'<div class="kv"><span>Access</span>{role}</div>'
                f'<div class="kv"><span>Signed in</span>{e(str(licence.get("signed_in", "")))}</div></div>',
                unsafe_allow_html=True)
            title = "Use a different activation code"
        else:
            st.markdown(
                f'<div class="mv-login-head"><img src="{logo_data_uri()}" alt="MedVisionAI logo"/>'
                '<div class="brand">MedVisionAI</div><div class="sub">Clinical Intelligence Platform</div></div>'
                '<h2 class="mv-login-title">Activate your licence</h2>'
                '<p class="mv-login-text">Enter the activation code your organisation received from MedVisionAI.</p>',
                unsafe_allow_html=True)
            title = None
        if not licensing_on:
            st.info("Demo mode: licensing is not configured on this server, so every page is open without a code.",
                    icon=":material/info:")
        else:
            with (st.expander(title, icon=":material/key:") if title else st.container()):
                with st.form("activate", border=False):
                    st.text_input("Activation code", key="activation_code", placeholder="MVAI-XXXX-XXXX-XXXX-XXXX",
                                  max_chars=40, autocomplete="off")
                    st.checkbox("Remember this device for 30 days", value=True, key="remember_device",
                                help="Keeps you signed in on this browser after a refresh. Don't use on shared "
                                     "computers.")
                    st.form_submit_button("Activate", type="primary", width="stretch", on_click=activate,
                                          icon=":material/key:")
            if ss.get("auth_error"):
                st.error(ss.auth_error, icon=":material/error:")
        st.markdown(
            '<div class="mv-login-foot"><b>How do I get a code?</b> Activation codes are issued to hospitals, '
            'laboratories and research groups once their MedVisionAI subscription is confirmed. Each code is '
            'linked to your organisation and has an expiry date.</div>',
            unsafe_allow_html=True)

if ss.pop("just_activated", False):        # activated: go where the visitor wanted to go
    st.switch_page(PAGES.get(st.query_params.get("next", ""), "views/overview.py"))
