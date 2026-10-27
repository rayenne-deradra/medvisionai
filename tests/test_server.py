"""FastAPI backend: public endpoints, activation and access control, referrals (no model inference here)."""
import json

import pytest

from medvision.auth import code_hash

SECRET = "test-secret-for-the-api"
CODES = {"user": "MVAI-AAAA-BBBB-CCCC-DDDD", "coord": "MVAI-EEEE-FFFF-GGGG-HHHH"}


@pytest.fixture(scope="module")
def client():
    mp = pytest.MonkeyPatch()
    # isolate from .streamlit/secrets.toml: no real AI keys, no real Supabase (requests go to the in-memory store)
    mp.setenv("MEDVISION_SECRETS", "# test")
    for key in ("SUPABASE_URL", "SUPABASE_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
        mp.delenv(key, raising=False)
    mp.setenv("ACTIVATION_SECRET", SECRET)
    mp.setenv("OPEN_ACCESS", "false")
    mp.setenv("ACTIVATION_CODES", json.dumps({
        "t-user": {"hash": code_hash(CODES["user"], SECRET), "organisation": "Test clinic", "plan": "Research"},
        "t-coord": {"hash": code_hash(CODES["coord"], SECRET), "organisation": "Test coordination", "role": "coordinator"},
    }))
    from fastapi.testclient import TestClient

    from server import settings
    settings._toml.cache_clear()
    settings.licences.cache_clear()
    from server.main import app, store
    assert not store().persistent, "tests must never write to a real database"
    yield TestClient(app)
    mp.undo()


def token(client, who):
    r = client.post("/api/auth/activate", json={"code": CODES[who]})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_public_endpoints(client):
    assert client.get("/api/health").json()["status"] == "ok"
    cfg = client.get("/api/config").json()
    assert cfg["licensing"] and {s["id"] for s in cfg["specialists"]} >= {"neuro-oncology", "gi-pathology"}
    samples = client.get("/api/samples").json()
    assert len(samples["brain"]) == 10 and len(samples["colorectal"]) == 11


def test_access_control(client):
    assert client.post("/api/analyze/brain", data={"sample": "glioma_axial_t1.jpg"}).status_code == 401
    assert client.get("/api/appointments", headers={"Authorization": "Bearer forged.123.abc"}).status_code == 401
    assert client.post("/api/auth/activate", json={"code": "MVAI-ZZZZ-ZZZZ-ZZZZ-ZZZZ"}).status_code == 400
    assert client.get("/api/auth/me", headers=token(client, "user")).json()["organisation"] == "Test clinic"


def test_open_access(client, monkeypatch):
    monkeypatch.setenv("OPEN_ACCESS", "true")
    assert client.get("/api/config").json()["open_access"]
    a = client.get("/api/appointments", headers={"X-Visitor": "aaa111"})
    assert a.status_code == 200 and a.json()["mine"] == []
    # a forged token is still refused, and a real code still signs in as its licence
    assert client.get("/api/appointments", headers={"Authorization": "Bearer forged.123.abc"}).status_code == 401
    assert client.get("/api/auth/me", headers=token(client, "user")).json()["organisation"] == "Test clinic"


def test_referral_and_triage(client):
    user, coord = token(client, "user"), token(client, "coord")
    body = {"specialist_id": "neuroradiology", "urgency": "urgent", "reason": "check", "requester": "Dr A",
            "contact": "a@x", "consent": True}
    assert client.post("/api/appointments", headers=user, json=body | {"consent": False}).status_code == 400
    row = client.post("/api/appointments", headers=user, json=body).json()
    assert row["position"] == 1 and row["status"] == "pending"
    confirm = {"status": "confirmed", "appointment_at": "2030-01-02T09:00", "location": "Room 1"}
    assert client.patch(f"/api/appointments/{row['id']}", headers=user, json=confirm).status_code == 403
    assert client.patch(f"/api/appointments/{row['id']}", headers=coord, json=confirm).json()["status"] == "confirmed"
    assert "queue" in client.get("/api/appointments", headers=coord).json()
    assert "queue" not in client.get("/api/appointments", headers=user).json()


def test_spa_fallback_and_docs(client):
    assert client.get("/docs").status_code == 200
    assert client.get("/api/unknown").status_code == 404
