"""Appointment requests: validation, priority queue, urgency suggestion, Supabase client (canned HTTP)."""
import pytest

from medvision import appointments as ap


def req(urgency, created, licence="org-a", **kw):
    r = ap.new_request(licence_id=licence, organisation="Org", requester="Dr X", contact="x@h.org",
                       hospital="H", specialist="Pathologist", department="Pathology", urgency=urgency,
                       reason="Second opinion", preferred="", **kw)
    r["created_at"] = created
    return r


def test_validation():
    with pytest.raises(ValueError, match="reason"):
        ap.new_request(licence_id="a", organisation="", requester="Dr", contact="c", hospital="", specialist="s",
                       department="d", urgency="soon", reason="  ", preferred="")
    with pytest.raises(ValueError):
        req("someday", "2026-01-01")


def test_urgent_requests_jump_the_line_and_order_is_fair_within_a_level():
    store = ap.MemoryStore()
    routine = store.add(req("routine", "2026-10-01T08:00:00"))
    soon = store.add(req("soon", "2026-10-02T08:00:00"))
    urgent_late = store.add(req("urgent", "2026-10-03T09:00:00"))
    urgent_early = store.add(req("urgent", "2026-10-03T08:00:00", licence="org-b"))
    rows = store.list()
    assert [r["id"] for r in rows] == [urgent_early["id"], urgent_late["id"], soon["id"], routine["id"]]
    assert ap.queue_position(rows, routine["id"]) == 4
    store.update(urgent_early["id"], status="confirmed")
    rows = store.list()
    assert ap.queue_position(rows, urgent_late["id"]) == 1 and ap.queue_position(rows, urgent_early["id"]) is None
    assert len(store.list("org-a")) == 3          # each organisation sees only its own requests


def test_urgency_suggestion_from_analysis():
    assert ap.suggest_urgency({"finding": "Tumour tissue detected"}) == "urgent"
    assert ap.suggest_urgency({"finding": "No tumour tissue detected", "confidence": "Low"}) == "soon"
    assert ap.suggest_urgency({"finding": "No tumour tissue detected", "confidence": "High",
                               "tumor_probability": 0.01}) == "routine"
    assert ap.suggest_urgency(None) == "routine"


class FakeResp:
    def __init__(self, status, body):
        self.status_code, self._body, self.content = status, body, b"x"

    def json(self):
        return self._body


def test_supabase_client_sends_the_right_requests(monkeypatch):
    calls = []

    def fake(method, url, params=None, json=None, headers=None, timeout=None):
        calls.append((method, url, params, json, headers))
        return FakeResp(201 if method == "POST" else 200, [json or {"id": "1", "status": "pending", "priority": 1,
                                                                    "created_at": "t"}])
    monkeypatch.setattr(ap.requests, "request", fake)
    s = ap.SupabaseStore("https://abc.supabase.co", "service-key")
    s.add(req("urgent", "2026-10-03"))
    s.list("org-a")
    s.update("1", status="confirmed")
    (m1, u1, _, _, h1), (m2, _, p2, _, _), (m3, _, p3, b3, _) = calls
    assert m1 == "POST" and u1.endswith("/rest/v1/appointments") and h1["apikey"] == "service-key"
    assert m2 == "GET" and p2["licence_id"] == "eq.org-a" and p2["order"] == "priority.asc,created_at.asc"
    assert m3 == "PATCH" and p3 == {"id": "eq.1"} and b3["status"] == "confirmed"


def test_supabase_errors_are_readable(monkeypatch):
    monkeypatch.setattr(ap.requests, "request", lambda *a, **k: FakeResp(401, {"message": "Invalid API key"}))
    with pytest.raises(ap.StoreError, match="401"):
        ap.SupabaseStore("https://abc.supabase.co", "bad").list()
