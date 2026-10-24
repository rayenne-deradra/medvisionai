"""Specialist consultations: who can be booked, and the pre-filled link to an external booking calendar.

Bookings are handled by a scheduling service (Calendly or Cal.com): it owns the time slots, confirmation e-mails and
reminders, so the app stores nothing. Configure in Streamlit secrets:

    CONSULT_BOOKING_URL = "https://calendly.com/your-practice/30min"   # used for every specialist without their own

    [specialists.gi-pathology]                       # optional; without any, example profiles are shown
    name = "Dr. A. Example"
    title = "Consultant gastrointestinal pathologist"
    focus = "Colorectal tumours, polyps, second opinions"
    languages = "English, French"
    duration = "30 min · video call"
    booking_url = "https://calendly.com/dr-example/30min"
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


@dataclass(frozen=True)
class Specialist:
    sid: str
    name: str
    title: str
    focus: str
    languages: str
    duration: str
    booking_url: str
    example: bool = False
    badge: str = ""                  # short label in the avatar; derived from the title when empty

    @property
    def initials(self) -> str:
        if self.badge:
            return self.badge[:3].upper()
        words = [w for w in self.title.replace("&", " ").split() if w[:1].isalpha() and w.lower() not in
                 {"and", "of", "the", "consultant"}]
        return "".join(w[0] for w in words[:2]).upper() or "MD"


EXAMPLES = [
    ("gi-pathology", "GI", "Consultant gastrointestinal pathologist",
     "Colorectal tumours and polyps, second opinions on difficult cases", "English, French", "30 min · video call"),
    ("digital-pathology", "AI", "Digital pathology & AI specialist",
     "Interpreting AI results, heatmaps and model uncertainty", "English", "30 min · video call"),
    ("colorectal-surgery", "CS", "Colorectal surgeon (tumour board liaison)",
     "Treatment pathways and multidisciplinary team referral", "English, Arabic", "20 min · video call"),
]


def load_specialists(table: dict, default_url: str) -> list[Specialist]:
    """Specialists from secrets, or clearly marked example profiles when none are configured."""
    if table:
        return [Specialist(sid, str(e.get("name", "")), str(e.get("title", "Specialist")), str(e.get("focus", "")),
                           str(e.get("languages", "")), str(e.get("duration", "30 min · video call")),
                           str(e.get("booking_url") or default_url or ""), badge=str(e.get("badge", "")))
                for sid, e in table.items()]
    return [Specialist(sid, "Example profile", title, focus, langs, dur, default_url or "", example=True, badge=badge)
            for sid, badge, title, focus, langs, dur in EXAMPLES]


def booking_link(url: str, name: str = "", notes: str = "", embed: bool = False) -> str:
    """The booking URL with prefilled details. Calendly reads `name` and `a1` (first question); Cal.com reads `name`
    and `notes`. Unknown parameters are ignored by both. `embed` adds Calendly's inline-embed flags."""
    if not url:
        return ""
    parts = urlparse(url)
    query = dict(parse_qsl(parts.query))
    if name:
        query["name"] = name
    if notes:
        query["a1"] = notes[:1000]
        query["notes"] = notes[:1000]
    if embed and "calendly.com" in parts.netloc:
        query.update({"embed_type": "Inline", "hide_gdpr_banner": "1"})
    if embed and "cal.com" in parts.netloc:
        query["embed"] = "true"
    return urlunparse(parts._replace(query=urlencode(query)))


def case_summary(report: dict) -> str:
    """Short, image-free summary of an analysis to share with the specialist."""
    parts = [f"MedVisionAI analysis of {report['filename']}: {report['finding']}",
             f"confidence {report['confidence'].lower()}"]
    if report.get("predicted_class"):
        parts.append(f"predicted tissue {report['predicted_class']}")
    if report.get("tumor_probability") is not None:
        parts.append(f"tumour probability {report['tumor_probability']:.1%}")
    return "; ".join(parts) + ". (Research prototype output, not a diagnosis.)"
