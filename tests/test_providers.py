"""OpenAI client streaming and error handling against canned HTTP responses (no network, no real key)."""
import json

import pytest

from medvision.llm import ChatMessage, LLMError, OpenAIProvider, pick_model
from medvision.llm import providers as prov


class FakeResp:
    def __init__(self, status, lines=(), body=None):
        self.status_code, self._lines, self._body, self.encoding = status, list(lines), body or {}, None

    def iter_lines(self, decode_unicode=True):
        yield from self._lines

    def json(self):
        return self._body

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


def _patch(monkeypatch, resp, cap):
    def post(url, headers, json, stream, timeout):
        cap.update(url=url, headers=headers, payload=json)
        return resp
    monkeypatch.setattr(prov.requests, "post", post)
    monkeypatch.setattr(prov.time, "sleep", lambda s: None)


def test_stream_with_image(monkeypatch):
    lines = ["data: " + json.dumps({"choices": [{"delta": {"content": "A"}}]}),
             "data: " + json.dumps({"choices": [{"delta": {"content": "B"}}]}), "data: [DONE]"]
    cap = {}
    _patch(monkeypatch, FakeResp(200, lines), cap)
    out = "".join(OpenAIProvider("sk-test", "gpt-x").stream("sys", [ChatMessage("user", "hi", [b"img"])]))
    assert out == "AB"
    assert cap["headers"]["Authorization"] == "Bearer sk-test"
    assert cap["payload"]["messages"][1]["content"][1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_errors_are_readable_and_never_leak_the_key(monkeypatch):
    _patch(monkeypatch, FakeResp(401, body={"error": {"message": "Incorrect API key sk-secret-xyz"}}), {})
    with pytest.raises(LLMError) as e:
        list(OpenAIProvider("sk-secret-xyz", "gpt-x").stream("s", [ChatMessage("user", "q")]))
    assert "401" in str(e.value) and "sk-secret-xyz" not in str(e.value)


def test_retries_then_fails_on_rate_limit(monkeypatch):
    _patch(monkeypatch, FakeResp(429, body={"error": {"message": "slow down"}}), {})
    with pytest.raises(LLMError, match="429"):
        list(OpenAIProvider("k", "gpt-x").stream("s", [ChatMessage("user", "q")]))


def test_missing_key_and_model_choice():
    with pytest.raises(LLMError):
        OpenAIProvider("", "gpt-x")
    assert pick_model(["gpt-4o", "gpt-4.1-mini", "whisper-1"]) == "gpt-4.1-mini"
    assert pick_model(["dall-e-3", "gpt-9-turbo"]) == "gpt-9-turbo"
    assert pick_model(["whisper-1"]) is None


def test_no_credits_is_explained_and_not_retried(monkeypatch):
    calls = []
    body = {"error": {"message": "You have no credits remaining.", "type": "insufficient_quota",
                      "code": "credit_balance_exhausted"}}

    def post(url, headers, json, stream, timeout):
        calls.append(1)
        return FakeResp(429, body=body)
    monkeypatch.setattr(prov.requests, "post", post)
    monkeypatch.setattr(prov.time, "sleep", lambda s: None)
    with pytest.raises(prov.QuotaError, match="no credits left"):
        list(OpenAIProvider("k", "gpt-x").stream("s", [ChatMessage("user", "q")]))
    assert len(calls) == 1


def test_gemini_model_choice_prefers_newest_stable_flash():
    from medvision.llm import pick_gemini_model
    ids = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.0-flash-preview",
           "gemini-2.5-pro", "gemini-2.5-flash-preview-tts", "text-embedding-004"]
    assert pick_gemini_model(ids) == "gemini-2.5-flash"
    assert pick_gemini_model(["gemini-3.0-flash-preview"]) == "gemini-3.0-flash-preview"
    assert pick_gemini_model(["gemini-2.5-pro"]) is None


def test_fallback_to_gemini_when_openai_has_no_credits(monkeypatch):
    import streamlit as st

    from medvision.llm import QuotaError, gemini_provider
    from medvision.ui import shared

    class Fake:
        def __init__(self, name, err=None, text=""):
            self.name, self.err, self.text, self.label = name, err, text, name

        def stream(self, system, messages):
            if self.err:
                raise self.err
            yield self.text

    monkeypatch.setattr(shared, "ss", {})
    used = {}
    providers = [Fake("OpenAI", QuotaError("Your OpenAI account has no credits left.")), Fake("Google Gemini", text="hi")]
    out = "".join(shared.stream_with_fallback(providers, "s", [ChatMessage("user", "q")], used))
    assert out == "hi" and used["provider"].name == "Google Gemini"
    assert "no credits" in used["skipped"][0] and shared.ss["openai_no_credits"] is True
    with pytest.raises(LLMError, match="no credits"):
        "".join(shared.stream_with_fallback(providers[:1], "s", [ChatMessage("user", "q")], {}))
    assert gemini_provider("k", "gemini-x").base_url.startswith("https://generativelanguage.googleapis.com")


def test_google_style_error_body_is_readable(monkeypatch):
    from medvision.llm import gemini_provider
    body = [{"error": {"code": 400, "message": "API key not valid. Please pass a valid API key.",
                       "status": "INVALID_ARGUMENT"}}]
    _patch(monkeypatch, FakeResp(400, body=body), {})
    with pytest.raises(LLMError, match="Google Gemini rejected the request.*API key not valid"):
        list(gemini_provider("bad-key", "gemini-x").stream("s", [ChatMessage("user", "q")]))
