"""Sign-in page: licence activation with the code an organisation receives after its subscription is confirmed."""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from medvision.auth import ActivationError, AttemptLimiter, make_device_token, verify
from medvision.config import get_secret, get_secret_table
from medvision.ui.shared import ss
from medvision.ui.theme import logo_data_uri

limiter = AttemptLimiter(ss)


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
    ss.licence = licence.to_dict() | {"signed_in": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
    ss.activation_code = ""                 # never keep the code itself in the session
    ss.pop("signed_out", None)
    if ss.get("remember_device", True):     # app.py writes the cookie on the next run
        ss.cookie_action = make_device_token(licence, secret)


_, mid, _ = st.columns([1, 1.25, 1])
with mid:
    with st.container(key="mv_login"):
        st.markdown(
            f'<div class="mv-login-head"><img src="{logo_data_uri()}" alt="MedVisionAI logo"/>'
            '<div class="brand">MedVisionAI</div><div class="sub">Clinical Intelligence Platform</div></div>'
            '<h2 class="mv-login-title">Activate your licence</h2>'
            '<p class="mv-login-text">Enter the activation code your organisation received from MedVisionAI.</p>',
            unsafe_allow_html=True)
        with st.form("activate", border=False):
            st.text_input("Activation code", key="activation_code", placeholder="MVAI-XXXX-XXXX-XXXX-XXXX",
                          max_chars=40, autocomplete="off")
            st.checkbox("Remember this device for 30 days", value=True, key="remember_device",
                        help="Keeps you signed in on this browser after a refresh. Don't use on shared computers.")
            st.form_submit_button("Activate", type="primary", width="stretch", on_click=activate,
                                  icon=":material/key:")
        if ss.get("auth_error"):
            st.error(ss.auth_error, icon=":material/error:")
        st.markdown(
            '<div class="mv-login-foot"><b>How do I get a code?</b> Activation codes are issued to hospitals, '
            'laboratories and research groups once their MedVisionAI subscription is confirmed. Each code is '
            'linked to your organisation and has an expiry date.</div>',
            unsafe_allow_html=True)

if ss.get("licence"):
    st.rerun()                              # activated: rebuild the navigation with the app pages
