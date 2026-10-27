"""Server configuration: secrets from the environment (Hugging Face Space secrets) or a local secrets file.

Sources, in order:
  1. Environment variables: ACTIVATION_SECRET, OPENAI_API_KEY, GEMINI_API_KEY, SUPABASE_URL, SUPABASE_KEY,
     HOSPITAL_NAME, ... and ACTIVATION_CODES as one line of JSON ({"judges": {"hash": ..., "organisation": ...}}).
  2. MEDVISION_SECRETS: the full text of a secrets.toml file, in one environment variable.
  3. .streamlit/secrets.toml next to the app (local development; the same file the Streamlit app uses).
Secret values are never logged or returned by the API.
"""
from __future__ import annotations

import json
import os
import tomllib
from functools import lru_cache

from medvision.config import ROOT


@lru_cache(maxsize=1)
def _toml() -> dict:
    text = os.environ.get("MEDVISION_SECRETS")
    if not text:
        path = ROOT / ".streamlit" / "secrets.toml"
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
    try:
        return tomllib.loads(text) if text else {}
    except tomllib.TOMLDecodeError:
        return {}


def secret(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name) or _toml().get(name)
    return str(value).strip() if value and str(value).strip() else default


@lru_cache(maxsize=1)
def licences() -> dict:
    raw = os.environ.get("ACTIVATION_CODES")
    if raw:
        try:
            return {k: dict(v) for k, v in json.loads(raw).items()}
        except (ValueError, AttributeError):
            return {}
    return {k: dict(v) for k, v in (_toml().get("activation_codes") or {}).items() if isinstance(v, dict)}


def licensing_on() -> bool:
    return bool(secret("ACTIVATION_SECRET") and licences())


def open_access() -> bool:
    """Open demo access: every feature works without a code (activation stays available). OPEN_ACCESS=false turns it off."""
    return (secret("OPEN_ACCESS", "true") or "").lower() not in ("0", "false", "no", "off")


def export_to_env() -> None:
    """The shared medvision code reads secrets with get_secret(), which falls back to environment variables."""
    for key, value in _toml().items():
        if isinstance(value, (str, int, float)) and key not in os.environ:
            os.environ[key] = str(value)
