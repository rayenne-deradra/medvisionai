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

    def to_dict(self) -> dict:
        return {"licence_id": self.licence_id, "organisation": self.organisation, "plan": self.plan,
                "expires": self.expires.isoformat() if self.expires else None}


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
    return Licence(licence_id, str(entry.get("organisation", licence_id)), str(entry.get("plan", "")), expires)


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
