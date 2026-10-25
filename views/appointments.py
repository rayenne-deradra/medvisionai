"""Book an appointment: request an in-person hospital consultation; urgent requests are triaged first."""
from __future__ import annotations

import html
from datetime import datetime

import streamlit as st

from medvision.appointments import (OPEN, SPECIALISTS, STATUSES, URGENCY, StoreError, case_summary, new_request,
                                    queue_position, suggest_urgency)
from medvision.config import get_secret
from medvision.ui.shared import get_store, ss
from medvision.ui.theme import section_html

HOSPITAL = get_secret("HOSPITAL_NAME") or "Example University Hospital"
HOSPITAL_ADDRESS = get_secret("HOSPITAL_ADDRESS") or ""
store = get_store()
licence = ss.get("licence") or {"licence_id": "demo", "organisation": "Demo user"}
by_id = {sid: (badge, title, dept, focus) for sid, badge, title, dept, focus in SPECIALISTS}


def choose(sid: str) -> None:
    ss.appt_sid = sid
    ss.appt_done = None


def cancel(request_id: str) -> None:
    try:
        store.update(request_id, status="cancelled")
    except StoreError as e:
        ss.appt_error = str(e)


def fmt_time(value) -> str:
    if not value:
        return ""
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).strftime("%a %d %b %Y, %H:%M")
    except ValueError:
        return str(value)


# ----------------------------------------------------------------------------- header
st.markdown(f'<div class="mv-consult-head"><div class="mv-label">Hospital appointments · {html.escape(HOSPITAL)}</div>'
            '<h1>Book an appointment</h1><p>Request an in-person consultation with a hospital specialist. Every '
            'request is triaged: <b>urgent cases are seen first</b>, then by time of request. A coordinator confirms '
            'the date, time and room.</p></div>', unsafe_allow_html=True)
st.markdown('<div class="mv-emergency"><b>Medical emergency?</b> Call your local emergency number (for example 112 or '
            '911) or go to the nearest emergency department. Appointment requests are not monitored around the '
            'clock.</div>', unsafe_allow_html=True)
if not store.persistent:
    st.caption("Demo mode: requests are kept until the app restarts. Connect Supabase to store them permanently.")
if ss.get("appt_error"):
    st.error(ss.pop("appt_error"), icon=":material/error:")

# ----------------------------------------------------------------------------- 1. specialist
st.markdown(section_html("1 · Choose a specialist", f"in person at {HOSPITAL}"), unsafe_allow_html=True)
cols = st.columns(2, gap="medium")
for i, (sid, badge, title, dept, focus) in enumerate(SPECIALISTS):
    with cols[i % 2]:
        with st.container(key=f"mv_spec_{sid}"):
            st.markdown(f'<div class="mv-spec"><div class="top"><div class="av">{badge}</div>'
                        f'<span class="mv-dept">{html.escape(dept)}</span></div>'
                        f'<div class="tt">{html.escape(title)}</div><div class="fc">{html.escape(focus)}</div>'
                        f'<div class="meta"><span>🏥 In person · {html.escape(HOSPITAL)}</span></div></div>',
                        unsafe_allow_html=True)
            selected = ss.get("appt_sid") == sid
            st.button("Selected" if selected else "Select", key=f"pick_{sid}", width="stretch",
                      icon=":material/check_circle:" if selected else ":material/person_add:",
                      type="primary" if selected else "secondary", on_click=choose, args=(sid,))

# ----------------------------------------------------------------------------- 2. request form
sid = ss.get("appt_sid")
if ss.get("appt_done"):
    st.success(ss.appt_done, icon=":material/check_circle:")
elif sid in by_id:
    badge, title, dept, _ = by_id[sid]
    st.markdown(section_html("2 · Request details", f"{title} · {dept}"), unsafe_allow_html=True)
    labels = {"none": "No analysis"} | {
        cid: ("Brain MRI · " if ss.cases[cid].get("modality") == "brain_mri" else "Tissue · ") +
        f"{ss.cases[cid]['report']['filename']} · {ss.cases[cid]['report']['finding']}"
        for cid in reversed(ss.get("case_order", []))}
    if "appt_case" not in ss or ss.appt_case not in labels:
        ss.appt_case = next(iter(list(labels)[1:]), "none")
    picked = st.selectbox("Attach an analysis summary (optional)", list(labels), format_func=labels.get,
                          key="appt_case", help="Adds a short text summary of the result. Images are never sent.")
    report = ss.cases[picked]["report"] if picked in ss.get("cases", {}) else None
    suggestion = suggest_urgency(report)
    with st.form("appt_form", border=False), st.container(key="mv_appt_form"):
        st.radio("Urgency", list(URGENCY), index=list(URGENCY).index(suggestion), horizontal=True, key="appt_urg",
                 format_func=lambda k: f"{URGENCY[k][1]} · {URGENCY[k][2]}")
        st.caption(" · ".join(f"**{v[1]}**: {v[3]}" for v in URGENCY.values()) +
                   (f"  \nSuggested: **{URGENCY[suggestion][1]}**, based on the attached analysis. You decide; "
                    "the hospital triages." if report else ""))
        st.text_area("Reason for the consultation", key="appt_reason", max_chars=2000, height=110,
                     placeholder="What should the specialist look at? Relevant history, what has been done so far.")
        c1, c2 = st.columns(2, gap="medium")
        c1.text_input("Contact person", key="appt_name", max_chars=120, placeholder="Dr. Name or coordinator")
        c2.text_input("Phone or e-mail", key="appt_contact", max_chars=120)
        c3, c4 = st.columns(2, gap="medium")
        c3.text_input("Preferred days / times", key="appt_pref", max_chars=300, placeholder="e.g. weekday mornings")
        c4.text_input("Patient reference (optional)", key="appt_ref", max_chars=60,
                      placeholder="Internal ID only, no names", help="Use your hospital's internal reference.")
        consent = st.checkbox("I confirm the patient agreed to this referral and that I have not entered "
                              "unnecessary identifying details.", key="appt_consent")
        submitted = st.form_submit_button("Send request", type="primary", icon=":material/send:", width="stretch")
    if submitted:
        if not consent:
            st.error("Please confirm the consent statement.", icon=":material/error:")
        else:
            try:
                row = new_request(licence_id=licence["licence_id"], organisation=licence.get("organisation", ""),
                                  requester=ss.appt_name, contact=ss.appt_contact, hospital=HOSPITAL,
                                  specialist=title, department=dept, urgency=ss.appt_urg, reason=ss.appt_reason,
                                  preferred=ss.appt_pref, patient_ref=ss.appt_ref,
                                  case_summary=case_summary(report) if report else "")
                store.add(row)
                pos = queue_position(store.list(), row["id"])
                ss.appt_done = (f"Request sent to **{title}** ({URGENCY[row['urgency']][1]}). You are **number {pos}** "
                                "in the line; urgent requests are seen first. You'll see the confirmed date, time "
                                "and room under *My requests* below.")
                ss.appt_sid = None
                st.rerun()
            except (ValueError, StoreError) as e:
                st.error(str(e), icon=":material/error:")
else:
    st.caption("Select a specialist to continue.")

# ----------------------------------------------------------------------------- my requests
st.markdown(section_html("My requests", licence.get("organisation", "")), unsafe_allow_html=True)
try:
    everything = store.list()
    mine = [r for r in everything if r["licence_id"] == licence["licence_id"]]
except StoreError as e:
    st.error(str(e), icon=":material/error:")
    everything, mine = [], []
if not mine:
    st.caption("No requests yet.")
for r in mine:
    urg = URGENCY.get(r["urgency"], (9, r["urgency"], "", ""))
    with st.container(key=f"mv_req_{r['id'][:8]}"):
        line = ""
        if r["status"] == "pending":
            line = f"Place in the line: <b>#{queue_position(everything, r['id'])}</b> · target {urg[2]}"
        elif r["status"] == "confirmed":
            line = (f"<b>{html.escape(fmt_time(r.get('appointment_at')))}</b>"
                    + (f" · {html.escape(r.get('location') or '')}" if r.get("location") else ""))
        note = f'<div class="mv-req-note">Hospital note: {html.escape(r["staff_note"])}</div>' if r.get("staff_note") else ""
        st.markdown(f'<div class="mv-req"><div class="hd"><span class="mv-urg {r["urgency"]}">{urg[1]}</span>'
                    f'<span class="mv-status {r["status"]}">{STATUSES.get(r["status"], r["status"])}</span></div>'
                    f'<div class="tt">{html.escape(r["specialist"])}</div>'
                    f'<div class="sub">Requested {html.escape(fmt_time(r["created_at"]))} by '
                    f'{html.escape(r["requester_name"])}</div><div class="when">{line}</div>{note}</div>',
                    unsafe_allow_html=True)
        if r["status"] in OPEN:
            st.button("Cancel request", key=f"cancel_{r['id']}", type="tertiary", icon=":material/close:",
                      on_click=cancel, args=(r["id"],))
