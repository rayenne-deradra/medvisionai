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


def init_state() -> None:
    ss.setdefault("cases", {})            # case_id -> analysed case (report, images, heatmap)
    ss.setdefault("case_order", [])       # newest last
    ss.setdefault("current_case", None)
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
        model = ss.openai_model = model or PREFERRED_MODELS[0]
    return OpenAIProvider(key, model, base_url)


def _gemini() -> list[OpenAIProvider]:
    """Up to 4 Gemini models, best first, each with one quick retry, so an overloaded model fails over fast."""
    key = get_secret("GEMINI_API_KEY")
    if not key:
        return []
    configured = get_secret("GEMINI_MODEL")
    if configured:
        return [gemini_provider(key, configured)]
    models = ss.get("gemini_models")
    if not models:                      # read the model list once per session
        try:
            models = rank_gemini_models(gemini_provider(key, "").list_models())[:4]
        except LLMError:
            models = []
        models = ss["gemini_models"] = models or [GEMINI_FALLBACK_MODEL]
    return [gemini_provider(key, m, attempts=1 if i < len(models) - 1 else 2) for i, m in enumerate(models)]


def get_providers() -> list[OpenAIProvider]:
    """Configured providers in the order they are tried: OpenAI first, Google Gemini as the fallback.

    Once OpenAI reports that the account has no credits, it is skipped for the rest of the session.
    """
    providers = [] if ss.get("openai_no_credits") else [_openai()]
    return [p for p in providers if p is not None] + _gemini()


def stream_with_fallback(providers: list[OpenAIProvider], system: str, messages: list[ChatMessage],
                         used: dict) -> Iterator[str]:
    """Stream from the first provider that answers. A provider that fails before sending any text (no credits,
    rate limit, network error...) hands over to the next one; `used` receives the provider and skipped errors."""
    used.setdefault("skipped", [])
    for i, provider in enumerate(providers):
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
            if isinstance(e, QuotaError) and provider.name == "OpenAI":
                ss["openai_no_credits"] = True
            if started:
                raise
            used["skipped"].append(str(e))
            if i == len(providers) - 1:
                raise LLMError(" ".join(used["skipped"])) from e
