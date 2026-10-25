"""State and resources shared by both pages. Everything lives in st.session_state, so analyses and chats survive
switching between pages for the whole browser session (and are never written to disk)."""
from __future__ import annotations

from typing import Iterator

import streamlit as st

from ..chat import new_conversation
from ..classifier import load_classifier
from ..config import get_secret
from ..llm import (PREFERRED_MODELS, ChatMessage, LLMError, OpenAIProvider, QuotaError, gemini_provider,
                   pick_model, rank_gemini_models)
from ..llm.providers import DEFAULT_BASE_URL

ss = st.session_state
GEMINI_FALLBACK_MODEL = "gemini-flash-latest"  # used only if the model list cannot be read


@st.cache_resource(show_spinner=False)
def get_classifier():
    """Loaded once per server process and shared by all sessions (the model is read-only)."""
    return load_classifier()


@st.cache_resource(show_spinner=False)
def get_brain_engine():
    """Brain MRI models (CNN ensemble, U-Net, classical radiomics), loaded once per server process."""
    from ..brain import BrainEngine
    return BrainEngine()


def cases_of(modality: str) -> list[str]:
    """Case ids of one modality ("colorectal" or "brain_mri"), newest first."""
    return [cid for cid in reversed(ss.get("case_order", []))
            if ss.cases[cid].get("modality", "colorectal") == modality]


def init_state() -> None:
    ss.setdefault("cases", {})            # case_id -> analysed case (report, images, heatmap)
    ss.setdefault("case_order", [])       # newest last
    ss.setdefault("current_case", None)   # colorectal case shown on Colorectal tissue
    ss.setdefault("current_brain", None)  # brain MRI case shown on Brain tumour MRI
    ss.setdefault("conversations", {})
    if not ss.get("active_chat") or ss.active_chat not in ss.conversations:
        conv = new_conversation()
        ss.conversations[conv["id"]] = conv
        ss.active_chat = conv["id"]


def ai_configured() -> bool:
    return bool(get_secret("OPENAI_API_KEY") or get_secret("GEMINI_API_KEY"))


def _openai() -> OpenAIProvider | None:
    key = get_secret("OPENAI_API_KEY")
    if not key:
        return None
    base_url = get_secret("OPENAI_BASE_URL", DEFAULT_BASE_URL)
    model = get_secret("OPENAI_MODEL") or ss.get("openai_model")
    if not model:                       # pick the first preferred model this key can use, once per session
        try:
            model = pick_model(OpenAIProvider(key, "", base_url).list_models())
        except LLMError:
            model = None
        model = ss["openai_model"] = model or PREFERRED_MODELS[0]
    return OpenAIProvider(key, model, base_url)


def _gemini() -> list[OpenAIProvider]:
    """Several Gemini models, best first: up to 3 full 'flash' models, then up to 3 'flash-lite' models (larger
    free-tier quota, less demand). Each gets one quick try, so an overloaded or over-quota model fails over fast."""
    key = get_secret("GEMINI_API_KEY")
    if not key:
        return []
    configured = get_secret("GEMINI_MODEL")
    if configured:
        return [gemini_provider(key, configured)]
    models = ss.get("gemini_models")
    if not models:                      # read the model list once per session
        try:
            available = gemini_provider(key, "").list_models()
            ranked = rank_gemini_models(available)
            models = ([m for m in ranked if "lite" not in m][:3] + [m for m in ranked if "lite" in m][:3] +
                      [m for m in ("gemini-flash-latest", "gemini-flash-lite-latest") if m in available])
        except LLMError:
            models = []
        models = ss["gemini_models"] = models or [GEMINI_FALLBACK_MODEL]
    return [gemini_provider(key, m, attempts=1 if i < len(models) - 1 else 2) for i, m in enumerate(models)]


def get_providers() -> list[OpenAIProvider]:
    """Configured providers in the order they are tried: OpenAI first, Google Gemini as the fallback.

    OpenAI is skipped for the rest of the session once it reports no credits or rejects the key.
    """
    providers = [] if (ss.get("openai_no_credits") or ss.get("openai_bad_key")) else [_openai()]
    return [p for p in providers if p is not None] + _gemini()


class AllProvidersFailed(LLMError):
    """No provider could answer. `str()` is a short, readable summary; `details` holds every raw error."""

    def __init__(self, summary: str, details: list[str]):
        super().__init__(summary)
        self.details = details


def summarize_failures(failures: list[tuple[str, str]]) -> str:
    """Turn (provider name, error) pairs into one plain-language message."""
    parts = []
    openai = [e for n, e in failures if n == "OpenAI"]
    if openai:
        e = openai[0]
        if "no credits" in e:
            parts.append("OpenAI: the account has no credits.")
        elif "(401)" in e:
            parts.append("OpenAI: the API key was rejected. Check OPENAI_API_KEY in the app's Secrets "
                         "(or remove that line to use Gemini only).")
        else:
            parts.append("OpenAI: unavailable.")
    gemini = [e for n, e in failures if n == "Google Gemini"]
    if gemini:
        quota = sum("(429)" in e for e in gemini)
        busy = sum("(503)" in e or "high demand" in e for e in gemini)
        other = len(gemini) - quota - busy
        bits = [f"{quota} over the free-tier quota" if quota else "", f"{busy} overloaded" if busy else "",
                f"{other} unavailable" if other else ""]
        parts.append(f"Gemini: tried {len(gemini)} models ({', '.join(b for b in bits if b)}).")
        if any("(401)" in e or "(400)" in e and "API key" in e for e in gemini):
            parts.append("The Gemini key looks invalid; check GEMINI_API_KEY in the app's Secrets.")
    return ("No AI model could answer right now. " + " ".join(parts) +
            " Overload and free-tier limits are temporary: please try again in a minute.")


def stream_with_fallback(providers: list[OpenAIProvider], system: str, messages: list[ChatMessage],
                         used: dict) -> Iterator[str]:
    """Stream from the first provider that answers. A provider that fails before sending any text (no credits,
    rate limit, network error...) hands over to the next one; `used` receives the provider and skipped errors."""
    used.setdefault("skipped", [])
    failures: list[tuple[str, str]] = []
    for provider in providers:
        started = False
        try:
            for chunk in provider.stream(system, messages):
                if not started:
                    started = True
                    used["provider"] = provider
                yield chunk
            if started:
                return
            raise LLMError(f"{provider.name} returned an empty answer.")
        except LLMError as e:
            if started:
                raise
            if provider.name == "OpenAI":
                if isinstance(e, QuotaError):
                    ss["openai_no_credits"] = True
                elif "(401)" in str(e):
                    ss["openai_bad_key"] = True
            failures.append((provider.name, f"{provider.label}: {e}"))
            used["skipped"].append(str(e))
    details = [d for _, d in failures]
    raise AllProvidersFailed(summarize_failures(failures) if failures else "No AI provider is configured.", details)


@st.cache_resource(show_spinner=False)
def _memory_store():
    from ..appointments import MemoryStore
    return MemoryStore()              # one demo store for all sessions of this app process


def get_store():
    """Supabase when SUPABASE_URL and SUPABASE_KEY are set, otherwise the in-memory demo store."""
    from ..appointments import SupabaseStore
    url, key = get_secret("SUPABASE_URL"), get_secret("SUPABASE_KEY")
    return SupabaseStore(url, key) if url and key else _memory_store()
