"""Chat clients with image input and streaming, over plain HTTPS (no vendor SDKs needed).

Two providers share one OpenAI-compatible client:
  * OpenAI         key st.secrets["OPENAI_API_KEY"]   https://api.openai.com/v1
  * Google Gemini  key st.secrets["GEMINI_API_KEY"]   Gemini's OpenAI-compatible endpoint (free tier available)

API keys are passed in by the caller, only ever placed in the Authorization header, and scrubbed from every error
message.
"""
from __future__ import annotations

import base64
import json
import re
import time
from dataclasses import dataclass, field
from typing import Iterator

import requests

DEFAULT_BASE_URL = "https://api.openai.com/v1"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
# Tried in order when no OpenAI model is configured: the first one this key can use is picked.
PREFERRED_MODELS = ("gpt-5-mini", "gpt-5", "gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini", "gpt-4o")
BILLING_URLS = {"OpenAI": "https://platform.openai.com/settings/organization/billing",
                "Google Gemini": "https://aistudio.google.com/apikey"}


class LLMError(RuntimeError):
    """User-readable error from the AI provider."""


class QuotaError(LLMError):
    """The account has no credits / quota left. Retrying does not help."""


@dataclass
class ChatMessage:
    role: str                                          # "user" | "assistant"
    text: str
    images: list[bytes] = field(default_factory=list)  # JPEG bytes, user messages only


_RETRY_STATUS = {429, 500, 502, 503, 504}
_STATUS_MESSAGES = {
    400: "{name} rejected the request (400). The model may not accept images, or the model name is wrong.",
    401: "{name} rejected the API key (401). Check {key_name} in .streamlit/secrets.toml.",
    403: "This API key is not allowed to use the model (403).",
    404: "The model was not found for this API key (404).",
    413: "The request is too large (413). Try a smaller image.",
    429: "Rate limit reached at {name} (429). Wait a minute and try again.",
}


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _error_info(resp: requests.Response) -> tuple[str, str]:
    """(message, type/code/status) from an OpenAI-style or Google-style error body."""
    try:
        body = resp.json()
        if isinstance(body, list) and body:
            body = body[0]
        err = body.get("error", body) if isinstance(body, dict) else body
        if isinstance(err, dict):
            kind = " ".join(str(err.get(k) or "") for k in ("type", "code", "status"))
            return str(err.get("message") or "")[:300], kind
        return str(err)[:300], ""
    except Exception:
        return "", ""


class OpenAIProvider:
    """Client for any OpenAI-compatible chat endpoint (OpenAI itself, or Gemini's compatibility endpoint)."""

    def __init__(self, api_key: str, model: str, base_url: str = DEFAULT_BASE_URL, timeout: int = 120,
                 name: str = "OpenAI", key_name: str = "OPENAI_API_KEY", attempts: int = 3):
        if not api_key:
            raise LLMError(f"No {name} API key is configured.")
        self._key, self.model, self.base_url, self.timeout = api_key, model, base_url.rstrip("/"), timeout
        self.name, self.key_name, self.attempts = name, key_name, max(1, attempts)

    @property
    def label(self) -> str:
        return f"{self.name} · {self.model}"

    def _clean(self, text: str) -> str:
        return text.replace(self._key, "***")

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}

    def _error(self, resp: requests.Response) -> LLMError:
        message, kind = _error_info(resp)
        if "insufficient_quota" in kind or "credit_balance" in kind:
            return QuotaError(f"Your {self.name} account has no credits left (429 insufficient_quota). Add credits at "
                              f"{BILLING_URLS.get(self.name, 'your billing page')}, then try again.")
        base = _STATUS_MESSAGES.get(resp.status_code, "{name} returned an error (" + str(resp.status_code) + ").")
        return LLMError(self._clean(f"{base.format(name=self.name, key_name=self.key_name)} {message}".strip()))

    def list_models(self) -> list[str]:
        try:
            resp = requests.get(self.base_url + "/models", headers=self._headers(), timeout=(10, 30))
        except requests.RequestException as e:
            raise LLMError(f"Could not reach {self.name} ({type(e).__name__}).") from e
        if resp.status_code != 200:
            raise self._error(resp)
        return sorted(str(m.get("id", "")).removeprefix("models/")
                      for m in resp.json().get("data", []) if isinstance(m, dict))

    def stream(self, system: str, messages: list[ChatMessage]) -> Iterator[str]:
        msgs = [{"role": "system", "content": system}]
        for m in messages:
            if m.role == "user" and m.images:
                parts = [{"type": "text", "text": m.text}]
                parts += [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_b64(img)}"}}
                          for img in m.images]
                msgs.append({"role": "user", "content": parts})
            else:
                msgs.append({"role": m.role, "content": m.text})
        payload = {"model": self.model, "messages": msgs, "stream": True}
        last = LLMError(f"The request to {self.name} failed.")
        for attempt in range(self.attempts):
            try:
                resp = requests.post(self.base_url + "/chat/completions", headers=self._headers(), json=payload,
                                     stream=True, timeout=(10, self.timeout))
            except requests.Timeout:
                last = LLMError(f"{self.name} did not respond in time. Please try again.")
            except requests.ConnectionError:
                last = LLMError(f"Could not reach {self.name}. Check the internet connection.")
            else:
                if resp.status_code == 200:
                    break
                last, code = self._error(resp), resp.status_code
                resp.close()
                if code not in _RETRY_STATUS or isinstance(last, QuotaError):
                    raise last
            if attempt < self.attempts - 1:
                time.sleep(1.5 * (attempt + 1))
        else:
            raise last
        resp.encoding = "utf-8"
        with resp:
            yield from self._events(resp)

    def _events(self, resp: requests.Response) -> Iterator[str]:
        try:
            for line in resp.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if isinstance(event, list) and event:
                    event = event[0]
                if "error" in event:
                    e = event["error"]
                    detail = e.get("message", e) if isinstance(e, dict) else e
                    raise LLMError(self._clean(f"{self.name} reported an error: {detail}"))
                for choice in event.get("choices") or []:
                    text = (choice.get("delta") or {}).get("content")
                    if text:
                        yield text
        except requests.RequestException as e:      # the model went silent or the connection dropped mid-answer
            raise LLMError(f"{self.name} did not respond in time. Please try again.") from e

    def test(self) -> str:
        reply = "".join(self.stream("Reply with the single word OK.", [ChatMessage("user", "Connection test")]))
        if not reply.strip():
            raise LLMError(f"{self.name} answered with an empty reply. Try another model.")
        return reply.strip()


def gemini_provider(api_key: str, model: str, attempts: int = 3) -> OpenAIProvider:
    return OpenAIProvider(api_key, model, GEMINI_BASE_URL, name="Google Gemini", key_name="GEMINI_API_KEY",
                          attempts=attempts)


def pick_model(available: list[str], preferred: tuple[str, ...] = PREFERRED_MODELS) -> str | None:
    """First preferred OpenAI model this key can use, else any chat-capable gpt-* model."""
    for name in preferred:
        if name in available:
            return name
    chat = [m for m in available if m.startswith("gpt-") and not any(t in m for t in ("audio", "realtime",
                                                                                         "transcribe", "tts",
                                                                                         "search", "image"))]
    return chat[0] if chat else None


def rank_gemini_models(available: list[str]) -> list[str]:
    """Chat-capable 'flash' models (fast, free tier, accept images), best first: stable before preview, full before
    lite, newest version first. Several are tried in turn because a single model can be overloaded (503)."""
    skip = ("tts", "image", "live", "audio", "embedding", "thinking", "learnlm", "gemma", "robotics", "computer",
            "omni", "latest")
    candidates = [m for m in available if m.startswith("gemini-") and "flash" in m and not any(t in m for t in skip)]

    def rank(m: str):
        v = re.match(r"gemini-(\d+(?:\.\d+)?)", m)
        return (not any(t in m for t in ("preview", "exp")), "lite" not in m, float(v.group(1)) if v else 0.0,
                -len(m))
    return sorted(candidates, key=rank, reverse=True)


def pick_gemini_model(available: list[str]) -> str | None:
    ranked = rank_gemini_models(available)
    return ranked[0] if ranked else None
