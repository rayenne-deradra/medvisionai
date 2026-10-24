"""Activation-code licensing.

A customer organisation receives an activation code (e.g. MVAI-7KQ2-XRT9-4HDM-PW3C) after payment. The app never
stores codes in plain text: Streamlit secrets hold only an HMAC-SHA256 of each code, keyed with ACTIVATION_SECRET,
plus the licence details. A leaked secrets file without the secret, or the source code, reveals no usable code.

Secrets layout (.streamlit/secrets.toml locally, App settings -> Secrets on Streamlit Community Cloud):

    ACTIVATION_SECRET = "long random string"        # generated once by tools/make_activation_code.py

    [activation_codes.acme-hospital]                 # one table per licence; the name is only a label
    hash = "3f1c..."                                 # printed by tools/make_activation_code.py
    organisation = "Acme Hospital, Pathology Dept."
    plan = "Research"                                # free text shown to the user
    expires = "2027-10-31"                           # optional, ISO date; the code stops working after it
    active = true                                    # set to false to revoke immediately
    role = "user"                                    # optional: "coordinator" for hospital staff (triage queue)

If no licences are configured, the app runs in open demo mode so that local development keeps working.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets as pysecrets
import time
from dataclasses import dataclass
from datetime import date

ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"     # no 0/O, 1/I/L: easy to read out and type
PREFIX = "MVAI"
GROUPS, GROUP_LEN = 4, 4
MAX_ATTEMPTS, LOCKOUT_SECONDS = 5, 60


@dataclass(frozen=True)
class Licence:
    licence_id: str
    organisation: str
    plan: str
    expires: date | None
    role: str = "user"              # "user" or "coordinator" (hospital staff: sees the triage queue)

    @property
    def is_coordinator(self) -> bool:
        return self.role == "coordinator"

    def to_dict(self) -> dict:
        return {"licence_id": self.licence_id, "organisation": self.organisation, "plan": self.plan,
                "expires": self.expires.isoformat() if self.expires else None, "role": self.role}


class ActivationError(ValueError):
    """User-readable reason why a code was not accepted."""


def generate_code() -> str:
    groups = ["".join(pysecrets.choice(ALPHABET) for _ in range(GROUP_LEN)) for _ in range(GROUPS)]
    return "-".join([PREFIX, *groups])


def normalise(code: str) -> str:
    """Upper-case, drop spaces/dashes, then re-insert dashes in the canonical places. Returns "" if malformed."""
    raw = re.sub(r"[\s\-_]", "", (code or "").upper())
    if raw.startswith(PREFIX):
        raw = raw[len(PREFIX):]
    if len(raw) != GROUPS * GROUP_LEN or any(c not in ALPHABET for c in raw):
        return ""
    return "-".join([PREFIX] + [raw[i:i + GROUP_LEN] for i in range(0, len(raw), GROUP_LEN)])


def code_hash(code: str, secret: str) -> str:
    return hmac.new(secret.encode(), normalise(code).encode(), hashlib.sha256).hexdigest()


def _parse_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def verify(code: str, secret: str, licences: dict, today: date | None = None) -> Licence:
    """Return the matching licence or raise ActivationError. Every stored hash is compared in constant time."""
    if not normalise(code):
        raise ActivationError("That doesn't look like an activation code. It has the form MVAI-XXXX-XXXX-XXXX-XXXX.")
    if not secret:
        raise ActivationError("Licensing is not configured on this server (ACTIVATION_SECRET is missing).")
    digest = code_hash(code, secret)
    match = None
    for licence_id, entry in (licences or {}).items():
        stored = str(entry.get("hash", "")) if hasattr(entry, "get") else ""
        if stored and hmac.compare_digest(stored.lower(), digest) and match is None:
            match = (licence_id, entry)
    if match is None:
        raise ActivationError("This activation code is not valid. Check it for typos, or contact MedVisionAI.")
    licence_id, entry = match
    if not entry.get("active", True):
        raise ActivationError("This licence has been deactivated. Please contact MedVisionAI.")
    expires = _parse_date(entry.get("expires"))
    if expires and (today or date.today()) > expires:
        raise ActivationError(f"This licence expired on {expires:%d %B %Y}. Please contact MedVisionAI to renew.")
    return Licence(licence_id, str(entry.get("organisation", licence_id)), str(entry.get("plan", "")), expires,
                   str(entry.get("role", "user")))


class AttemptLimiter:
    """Simple per-session brute-force protection: MAX_ATTEMPTS failures, then a LOCKOUT_SECONDS pause."""

    def __init__(self, state: dict):
        self.state = state

    def locked_for(self) -> int:
        until = self.state.get("auth_locked_until", 0)
        return max(0, int(until - time.time()))

    def failed(self) -> None:
        n = self.state.get("auth_failures", 0) + 1
        self.state["auth_failures"] = n
        if n >= MAX_ATTEMPTS:
            self.state["auth_failures"] = 0
            self.state["auth_locked_until"] = time.time() + LOCKOUT_SECONDS

    def succeeded(self) -> None:
        self.state["auth_failures"] = 0
        self.state.pop("auth_locked_until", None)


# ----------------------------------------------------------------------------- remember this device
DEVICE_KEY = "mvai_device"        # localStorage key in the browser
DEVICE_PARAM = "device"           # one-time query parameter used to hand the token to the server
DEVICE_DAYS = 30


def _b64(data: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    import base64
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _device_sig(payload: str, secret: str) -> str:
    return _b64(hmac.new(secret.encode(), b"device|" + payload.encode(), hashlib.sha256).digest())


def make_device_token(licence: Licence, secret: str, days: int = DEVICE_DAYS, now: float | None = None) -> str:
    """Signed token for 'remember this device'. It holds no activation code, only the licence id and an
    expiry (at most `days`, never past the licence's own expiry)."""
    exp = int((now or time.time()) + days * 86400)
    if licence.expires:
        exp = min(exp, int(time.mktime(licence.expires.timetuple())) + 86400)
    payload = f"{_b64(licence.licence_id.encode())}.{exp}"
    return f"{payload}.{_device_sig(payload, secret)}"


def read_device_token(token: str, secret: str, licences: dict, now: float | None = None) -> Licence | None:
    """The licence a remembered device belongs to, or None. The licence is re-checked on every visit, so revoking
    or expiring it also signs out remembered devices."""
    try:
        id_part, exp_part, sig = (token or "").split(".")
        payload = f"{id_part}.{exp_part}"
        if not secret or not hmac.compare_digest(sig, _device_sig(payload, secret)):
            return None
        if int(exp_part) < (now or time.time()):
            return None
        licence_id = _unb64(id_part).decode()
    except (ValueError, UnicodeDecodeError):
        return None
    entry = (licences or {}).get(licence_id)
    if not entry or not entry.get("active", True):
        return None
    expires = _parse_date(entry.get("expires"))
    if expires and date.today() > expires:
        return None
    return Licence(licence_id, str(entry.get("organisation", licence_id)), str(entry.get("plan", "")), expires,
                   str(entry.get("role", "user")))


def storage_script(token: str | None) -> str:
    """Browser script that saves (token) or deletes (None) the remember-device token in localStorage.

    A cookie is not used because Streamlit Community Cloud's proxy does not pass cookies to the app."""
    import json
    body = (f"localStorage.setItem({json.dumps(DEVICE_KEY)}, {json.dumps(token)});" if token
            else f"localStorage.removeItem({json.dumps(DEVICE_KEY)});")
    return f"<script>(function(){{try{{{body}}}catch(e){{}}}})();</script>"


def restore_script() -> str:
    """Browser script for a signed-out visit: if this browser has a saved token, reload the page once with it in the
    `device` query parameter. The server checks it, signs in and removes it from the address straight away."""
    import json
    key, param = json.dumps(DEVICE_KEY), json.dumps(DEVICE_PARAM)
    return ("<script>(function(){try{var t=localStorage.getItem(" + key + ");if(!t)return;"
            "var u=new URL(window.location.href);if(u.searchParams.get(" + param + "))return;"
            "u.searchParams.set(" + param + ",t);window.location.replace(u.toString());}catch(e){}})();</script>")
