"""Book a consultation: choose a specialist and book a slot in the practice's online calendar (Calendly / Cal.com)."""
from __future__ import annotations

import html

import streamlit as st
import streamlit.components.v1 as components

from medvision.config import get_secret, get_secret_table
from medvision.consult import booking_link, case_summary, load_specialists
from medvision.ui.shared import ss
from medvision.ui.theme import section_html

specialists = load_specialists(get_secret_table("specialists"), get_secret("CONSULT_BOOKING_URL") or "")
by_id = {s.sid: s for s in specialists}


def choose(sid: str) -> None:
    ss.book_sid = sid


st.markdown('<div class="mv-consult-head"><div class="mv-label">Specialist consultations</div>'
            '<h1>Book a consultation</h1><p>Discuss a result with an expert: a second opinion on a difficult case, '
            'help interpreting the AI output, or the next steps for a referral. Pick a specialist, then choose a time '
            'that suits you.</p></div>', unsafe_allow_html=True)

# ----------------------------------------------------------------------------- what to share
with st.container(key="mv_consult_share"):
    st.markdown('<div class="mv-label">Share with the specialist (optional)</div>', unsafe_allow_html=True)
    labels = {"none": "No analysis"} | {cid: f"{ss.cases[cid]['report']['filename']} · {ss.cases[cid]['report']['finding']}"
                                      for cid in reversed(ss.get("case_order", []))}
    c1, c2 = st.columns([1, 1.4], gap="medium")
    if "consult_case" not in ss or ss.consult_case not in labels:   # default: the most recent analysis, if any
        ss.consult_case = next(iter(list(labels)[1:]), "none")
    picked = c1.selectbox("Analysis summary", list(labels), format_func=labels.get, key="consult_case",
                          help="Adds a short text summary (finding, confidence, tissue). Images are never sent.")
    message = c2.text_input("Message", key="consult_msg", max_chars=500,
                            placeholder="e.g. Borderline result on a rectal biopsy patch, would value a second opinion")
    st.caption("Please don't include patient names or other identifying details.")

notes_parts = []
if ss.get("licence"):
    notes_parts.append(f"Organisation: {ss.licence.get('organisation', '')}")
if picked and picked in ss.cases:
    notes_parts.append(case_summary(ss.cases[picked]["report"]))
if message.strip():
    notes_parts.append(message.strip())
notes = "\n".join(notes_parts)

# ----------------------------------------------------------------------------- specialists
st.markdown(section_html("Specialists", "example profiles" if specialists[0].example else ""), unsafe_allow_html=True)
cols = st.columns(len(specialists) if len(specialists) <= 3 else 3, gap="medium")
for i, sp in enumerate(specialists):
    with cols[i % len(cols)]:
        with st.container(key=f"mv_spec_{sp.sid}"):
            badge = '<span class="mv-example">Example profile</span>' if sp.example else ""
            name = "" if sp.example else f'<div class="nm">{html.escape(sp.name)}</div>'
            st.markdown(
                f'<div class="mv-spec"><div class="top"><div class="av">{html.escape(sp.initials)}</div>{badge}</div>'
                f'<div class="tt">{html.escape(sp.title)}</div>{name}'
                f'<div class="fc">{html.escape(sp.focus)}</div>'
                f'<div class="meta"><span>🕒 {html.escape(sp.duration)}</span>'
                + (f'<span>🌐 {html.escape(sp.languages)}</span>' if sp.languages else "") + "</div></div>",
                unsafe_allow_html=True)
            st.button("Book a time", key=f"book_{sp.sid}", icon=":material/event:", width="stretch",
                      type="primary" if ss.get("book_sid") == sp.sid else "secondary", on_click=choose, args=(sp.sid,))

if specialists[0].example:
    st.caption("These are example profiles that show how MedVisionAI connects users with partner specialists.")

# ----------------------------------------------------------------------------- booking calendar
sp = by_id.get(ss.get("book_sid") or "")
if sp:
    st.markdown(section_html(f"Booking · {sp.title}", sp.duration), unsafe_allow_html=True)
    if sp.booking_url:
        link = booking_link(sp.booking_url, notes=notes)
        with st.container(key="mv_calendar"):
            components.iframe(booking_link(sp.booking_url, notes=notes, embed=True), height=720, scrolling=True)
        st.link_button("Open the booking page in a new tab", link, icon=":material/open_in_new:")
        st.caption("Your booking, confirmation e-mail and reminders are handled by the scheduling service. "
                   "The details above are pre-filled in the booking form; you can still edit them there.")
    else:
        st.info("Online booking will open here once the clinic's calendar is connected.", icon=":material/event_busy:")
        with st.expander("For the app owner: connect a booking calendar"):
            st.markdown("1. Create a free event type on **Calendly** or **Cal.com** (for example *30-minute "
                        "consultation*).\n2. Copy its public link.\n3. In Streamlit secrets add "
                        "`CONSULT_BOOKING_URL = \"https://calendly.com/your-practice/30min\"` and save. "
                        "Optional: per-specialist links and profiles, see the README.")
