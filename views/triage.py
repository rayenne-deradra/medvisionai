"""Triage queue (hospital coordinators only): requests in priority order; confirm, decline or complete them."""
from __future__ import annotations

import html
from datetime import date, datetime, time, timedelta

import streamlit as st

from medvision.appointments import STATUSES, URGENCY, StoreError, queue_position
from medvision.ui.shared import get_store, ss
from medvision.ui.theme import section_html

store = get_store()
if not (ss.get("licence") or {}).get("role") == "coordinator":
    st.error("The triage queue is only available to hospital coordinators.", icon=":material/lock:")
    st.stop()


def act(request_id: str, status: str, **fields) -> None:
    try:
        store.update(request_id, status=status, **fields)
        ss.triage_msg = f"Request {STATUSES[status].lower()}."
    except StoreError as e:
        ss.triage_msg = f"Error: {e}"


def fmt(value) -> str:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).strftime("%a %d %b %Y, %H:%M")
    except (TypeError, ValueError):
        return str(value or "")


st.markdown('<div class="mv-consult-head"><div class="mv-label">Hospital coordinators</div><h1>Triage queue</h1>'
            '<p>Every appointment request, most urgent first and then oldest first. Confirm a date, time and room, '
            'or decline with a note; the requester sees the update immediately.</p></div>', unsafe_allow_html=True)
if not store.persistent:
    st.caption("Demo mode: requests are kept until the app restarts. Connect Supabase to store them permanently.")
if ss.get("triage_msg"):
    msg = ss.pop("triage_msg")
    (st.error if msg.startswith("Error") else st.success)(msg)

try:
    rows = store.list()
except StoreError as e:
    st.error(str(e), icon=":material/error:")
    st.stop()

pending = [r for r in rows if r["status"] == "pending"]
k = st.columns(4)
for col, (label, value) in zip(k, [("Urgent waiting", sum(r["urgency"] == "urgent" for r in pending)),
                                    ("Soon waiting", sum(r["urgency"] == "soon" for r in pending)),
                                    ("Routine waiting", sum(r["urgency"] == "routine" for r in pending)),
                                    ("Confirmed", sum(r["status"] == "confirmed" for r in rows))]):
    col.markdown(f'<div class="mv-kpi"><div class="k">{label}</div><div class="v big">{value}</div></div>',
                 unsafe_allow_html=True)

view = st.segmented_control("Show", ["Waiting", "Confirmed", "All"], default="Waiting", key="triage_view")
shown = {"Waiting": [r for r in rows if r["status"] == "pending"],
         "Confirmed": [r for r in rows if r["status"] == "confirmed"]}.get(view or "Waiting", rows)
st.markdown(section_html(f"{len(shown)} request(s)", "urgent first, then oldest first"), unsafe_allow_html=True)
if not shown:
    st.caption("Nothing here.")

for r in shown:
    urg = URGENCY.get(r["urgency"], (9, r["urgency"], "", ""))
    pos = queue_position(rows, r["id"])
    with st.container(key=f"mv_tri_{r['id'][:8]}"):
        when = (f" · <b>{html.escape(fmt(r.get('appointment_at')))}</b> · {html.escape(r.get('location') or '')}"
                if r["status"] == "confirmed" else "")
        extra = "".join(f'<div class="kv"><span>{k}</span>{html.escape(str(v))}</div>' for k, v in (
            ("Reason", r["reason"]), ("Preferred", r.get("preferred") or "—"),
            ("Patient ref.", r.get("patient_ref") or "—"), ("Analysis", r.get("case_summary") or "—"),
            ("Contact", f'{r["requester_name"]} · {r["contact"]}')))
        st.markdown(f'<div class="mv-req"><div class="hd">'
                    + (f'<span class="mv-pos">#{pos}</span>' if pos else "")
                    + f'<span class="mv-urg {r["urgency"]}">{urg[1]} · {urg[2]}</span>'
                    f'<span class="mv-status {r["status"]}">{STATUSES.get(r["status"], r["status"])}</span></div>'
                    f'<div class="tt">{html.escape(r["specialist"])} · {html.escape(r["department"])}</div>'
                    f'<div class="sub">{html.escape(r["organisation"])} · requested {html.escape(fmt(r["created_at"]))}'
                    f'{when}</div><div class="mv-req-detail">{extra}</div></div>', unsafe_allow_html=True)
        if r["status"] == "pending":
            with st.expander("Schedule or decline", icon=":material/event_available:"):
                with st.form(f"f_{r['id']}", border=False):
                    days = {"urgent": 1, "soon": 7}.get(r["urgency"], 21)
                    c1, c2, c3 = st.columns([1, 1, 1.4])
                    d = c1.date_input("Date", value=date.today() + timedelta(days=days), min_value=date.today(),
                                      key=f"d_{r['id']}")
                    t = c2.time_input("Time", value=time(9, 0), step=900, key=f"t_{r['id']}")
                    loc = c3.text_input("Location / room", value=f"{r['department']} outpatient clinic",
                                        key=f"l_{r['id']}")
                    note = st.text_input("Note to the requester (optional)", key=f"n_{r['id']}")
                    b1, b2 = st.columns(2)
                    if b1.form_submit_button("Confirm appointment", type="primary", icon=":material/check:",
                                             width="stretch"):
                        act(r["id"], "confirmed", appointment_at=datetime.combine(d, t).isoformat(timespec="minutes"),
                            location=loc, staff_note=note)
                        st.rerun()
                    if b2.form_submit_button("Decline", icon=":material/block:", width="stretch"):
                        act(r["id"], "declined", staff_note=note or "Please contact the hospital.")
                        st.rerun()
        elif r["status"] == "confirmed":
            st.button("Mark as completed", key=f"done_{r['id']}", type="tertiary", icon=":material/task_alt:",
                      on_click=act, args=(r["id"], "completed"))
