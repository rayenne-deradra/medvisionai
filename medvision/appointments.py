"""In-person hospital appointments with a priority (triage) queue.

Users request a consultation with a hospital specialist and choose an urgency. Requests wait in one queue ordered by
priority (urgent > soon > routine), then by time of request. Hospital coordinators (licences with
role = "coordinator") confirm a date, time and room, or decline with a note.

Storage:
  * Supabase (hosted Postgres) when SUPABASE_URL and SUPABASE_KEY are in the secrets: requests survive restarts and
    are shared by all users. Table definition: tools/supabase_schema.sql.
  * Otherwise an in-memory demo store, shared by all sessions until the app restarts.
"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone

import requests

URGENCY = {   # key -> (priority, label, target, description)
    "urgent": (1, "Urgent", "within 48 hours",
               "Suspected cancer or a result that could change treatment soon."),
    "soon": (2, "Soon", "within 2 weeks", "Needs specialist review, but no immediate risk."),
    "routine": (3, "Routine", "within 6 weeks", "Second opinion, follow-up or general questions."),
}
STATUSES = {"pending": "Waiting for triage", "confirmed": "Confirmed", "declined": "Declined",
            "completed": "Completed", "cancelled": "Cancelled"}
OPEN = ("pending", "confirmed")

SPECIALISTS = [   # (id, avatar label, title, department, focus)
    ("neuro-oncology", "NO", "Consultant neuro-oncologist", "Neuro-oncology",
     "Glioma, meningioma and pituitary tumours: treatment planning and referral to neurosurgery"),
    ("neuroradiology", "NR", "Consultant neuroradiologist", "Neuroradiology",
     "Reading brain MRI, lesion outlines and AI results; further imaging if needed"),
    ("gi-pathology", "GI", "Consultant gastrointestinal pathologist", "Pathology",
     "Colorectal tumours and polyps, second opinions on difficult cases"),
    ("digital-pathology", "AI", "Digital pathology & AI specialist", "Pathology",
     "Interpreting AI results, heatmaps and model uncertainty"),
    ("colorectal-surgery", "CS", "Colorectal surgeon", "Colorectal surgery",
     "Treatment pathways and referral to the multidisciplinary tumour board"),
    ("gastroenterology", "GE", "Consultant gastroenterologist", "Gastroenterology",
     "Colonoscopy, biopsies and follow-up of polyps"),
]


class StoreError(RuntimeError):
    """Readable storage problem."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_request(*, licence_id: str, organisation: str, requester: str, contact: str, hospital: str,
                specialist: str, department: str, urgency: str, reason: str, preferred: str,
                patient_ref: str = "", case_summary: str = "") -> dict:
    if urgency not in URGENCY:
        raise ValueError(f"Unknown urgency '{urgency}'")
    for name, value in (("your name", requester), ("a phone number or e-mail", contact), ("the reason", reason)):
        if not str(value).strip():
            raise ValueError(f"Please enter {name}.")
    return {"id": str(uuid.uuid4()), "created_at": now_iso(), "updated_at": now_iso(),
            "licence_id": licence_id, "organisation": organisation, "requester_name": requester.strip()[:120],
            "contact": contact.strip()[:120], "hospital": hospital, "department": department,
            "specialist": specialist, "urgency": urgency, "priority": URGENCY[urgency][0],
            "reason": reason.strip()[:2000], "preferred": preferred.strip()[:300], "patient_ref": patient_ref.strip()[:60],
            "case_summary": case_summary[:1000], "status": "pending", "appointment_at": None, "location": "",
            "staff_note": ""}


def sort_key(r: dict):
    return (r["status"] != "pending", r.get("priority", 9), r.get("created_at", ""))


def queue_position(requests_: list[dict], request_id: str) -> int | None:
    """1-based place in the line among pending requests (urgent first, then oldest first)."""
    pending = sorted((r for r in requests_ if r["status"] == "pending"), key=sort_key)
    for i, r in enumerate(pending, 1):
        if r["id"] == request_id:
            return i
    return None


def suggest_urgency(report: dict | None) -> str:
    """A suggestion only; the requester decides, and the coordinator triages."""
    if not report:
        return "routine"
    if report.get("modality") == "brain_mri":
        level = (report.get("risk") or {}).get("level")
        return {"high": "urgent", "medium": "soon"}.get(level, "soon" if report.get("confidence") == "Low" else "routine")
    if report.get("finding") == "Tumour tissue detected":
        return "urgent"
    if report.get("confidence") == "Low" or (report.get("tumor_probability") or 0) >= 0.2:
        return "soon"
    return "routine"


def case_summary(report: dict) -> str:
    """Short, image-free summary of an analysis to share with the specialist."""
    parts = [f"MedVisionAI analysis of {report['filename']}: {report['finding']}",
             f"confidence {report['confidence'].lower()}"]
    if report.get("modality") == "brain_mri":
        if report.get("risk"):
            parts += [f"brain MRI ({report.get('plane', '')} plane), predicted {report['predicted_class']} "
                      f"{report['predicted_probability']:.1%}",
                      f"lesion area {report['segmentation']['lesion_area_percent']:.2f}%",
                      f"triage score {report['risk']['score']:.0f}/100 ({report['risk']['level']})"]
        return "; ".join(parts) + ". (Research prototype output, not a diagnosis.)"
    if report.get("predicted_class"):
        parts.append(f"predicted tissue {report['predicted_class']}")
    if report.get("tumor_probability") is not None:
        parts.append(f"tumour probability {report['tumor_probability']:.1%}")
    return "; ".join(parts) + ". (Research prototype output, not a diagnosis.)"


# ----------------------------------------------------------------------------- stores
class MemoryStore:
    """Demo store shared by all sessions of one app process; emptied when the app restarts."""

    persistent = False

    def __init__(self):
        self._rows: dict[str, dict] = {}
        self._lock = threading.Lock()

    def add(self, row: dict) -> dict:
        with self._lock:
            self._rows[row["id"]] = dict(row)
        return row

    def list(self, licence_id: str | None = None) -> list[dict]:
        with self._lock:
            rows = [dict(r) for r in self._rows.values() if licence_id is None or r["licence_id"] == licence_id]
        return sorted(rows, key=sort_key)

    def update(self, request_id: str, **fields) -> dict:
        with self._lock:
            if request_id not in self._rows:
                raise StoreError("This request no longer exists.")
            self._rows[request_id].update(fields, updated_at=now_iso())
            return dict(self._rows[request_id])


class SupabaseStore:
    """Supabase REST (PostgREST). Use the service-role key; it stays on the server in Streamlit secrets."""

    persistent = True
    TABLE = "appointments"

    def __init__(self, url: str, key: str, timeout: int = 20):
        self.base = url.rstrip("/") + f"/rest/v1/{self.TABLE}"
        self._key, self.timeout = key, timeout

    def _headers(self, extra: dict | None = None) -> dict:
        h = {"apikey": self._key, "Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}
        return h | (extra or {})

    def _check(self, resp: requests.Response) -> list[dict]:
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("message", "")
            except Exception:
                detail = ""
            raise StoreError(f"The appointment database returned an error ({resp.status_code}). {detail}".strip())
        return resp.json() if resp.content else []

    def _call(self, method: str, params: dict | None = None, body: dict | None = None, extra: dict | None = None):
        try:
            resp = requests.request(method, self.base, params=params, json=body, headers=self._headers(extra),
                                    timeout=self.timeout)
        except requests.RequestException as e:
            raise StoreError(f"Could not reach the appointment database ({type(e).__name__}).") from e
        return self._check(resp)

    def add(self, row: dict) -> dict:
        rows = self._call("POST", body=row, extra={"Prefer": "return=representation"})
        return rows[0] if rows else row

    def list(self, licence_id: str | None = None) -> list[dict]:
        params = {"select": "*", "order": "priority.asc,created_at.asc"}
        if licence_id is not None:
            params["licence_id"] = f"eq.{licence_id}"
        return sorted(self._call("GET", params=params), key=sort_key)

    def update(self, request_id: str, **fields) -> dict:
        rows = self._call("PATCH", params={"id": f"eq.{request_id}"}, body=fields | {"updated_at": now_iso()},
                          extra={"Prefer": "return=representation"})
        if not rows:
            raise StoreError("This request no longer exists.")
        return rows[0]
