"""Central settings and secret lookup.

Secrets come from Streamlit secrets (`.streamlit/secrets.toml` locally, the "Secrets" box on Streamlit Community
Cloud), e.g. `st.secrets["OPENAI_API_KEY"]`, with an environment-variable fallback. They are never stored in source
code, logged, or written to disk by the app.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT / "assets"
MODELS_DIR = ROOT / "models"
EXAMPLES_DIR = ROOT / "examples"

MAX_UPLOAD_MB = 10             # keep in sync with server.maxUploadSize in .streamlit/config.toml
LLM_HISTORY_MESSAGES = 16      # most recent chat messages sent to the AI provider
LLM_IMAGE_MAX_SIDE = 1024      # images are downscaled before upload to the AI provider
DISPLAY_MAX_SIDE = 900         # images kept in the session for display


def _streamlit_secret(name: str) -> str | None:
    try:
        import streamlit as st

        loader = getattr(st.secrets, "load_if_toml_exists", None)
        if loader is not None and not loader():
            return None
        if name in st.secrets:
            value = st.secrets[name]
            return str(value) if value is not None else None
    except Exception:  # no secrets file, or running outside Streamlit
        return None
    return None


def get_secret(name: str, default: str | None = None) -> str | None:
    """Streamlit secrets first, then an environment variable. Empty values count as missing."""
    value = _streamlit_secret(name) or os.environ.get(name)
    return value.strip() if value and value.strip() else default


def get_secret_table(name: str) -> dict:
    """A [table] from Streamlit secrets as a plain dict of dicts (empty if missing)."""
    try:
        import streamlit as st

        loader = getattr(st.secrets, "load_if_toml_exists", None)
        if loader is not None and not loader():
            return {}
        table = st.secrets.get(name)
        return {k: dict(v) for k, v in dict(table).items() if hasattr(v, "items")} if table else {}
    except Exception:
        return {}
