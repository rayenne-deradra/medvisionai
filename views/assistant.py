"""AI Assistant page: ChatGPT-style chat about analysed images, attached images, or general questions.

Providers: OpenAI first (st.secrets["OPENAI_API_KEY"]); Google Gemini (st.secrets["GEMINI_API_KEY"], free tier)
answers when OpenAI fails before replying, e.g. when the OpenAI account has no credits.
"""
from __future__ import annotations

import streamlit as st

from medvision import DISCLAIMER
from medvision.chat import add_message, build_llm_messages, conversation_markdown, new_conversation
from medvision.config import ASSETS_DIR, LLM_HISTORY_MESSAGES, LLM_IMAGE_MAX_SIDE, MAX_UPLOAD_MB, ROOT, get_secret
from medvision.imaging import ALLOWED_EXTENSIONS, ImageError, downscale, load_image, to_bytes
from medvision.llm import SYSTEM_PROMPT, LLMError
from medvision.ui.shared import ai_configured, get_providers, ss, stream_with_fallback

USER_AVATAR, ASSISTANT_AVATAR = ":material/person:", str(ASSETS_DIR / "avatar.svg")


# ----------------------------------------------------------------------------- sidebar (this page only)
def start_chat():
    conv = ss.conversations[ss.active_chat]
    if conv["messages"]:
        conv = new_conversation()
        ss.conversations[conv["id"]] = conv
        ss.active_chat = conv["id"]


def open_chat(cid):
    ss.active_chat = cid


def delete_chat(cid):
    ss.conversations.pop(cid, None)
    if ss.active_chat == cid:
        ss.active_chat = next(reversed(ss.conversations), None) if ss.conversations else None
        if ss.active_chat is None:
            conv = new_conversation()
            ss.conversations[conv["id"]] = conv
            ss.active_chat = conv["id"]


def test_connection():
    """Tests every configured provider separately (OpenAI is re-checked even if it ran out of credits earlier)."""
    ss.pop("openai_no_credits", None)
    results = []
    for provider in get_providers():
        try:
            provider.test()
            results.append(("ok", f"{provider.label}: connected"))
        except LLMError as e:
            results.append(("error", str(e)))
            if "no credits" in str(e) and provider.name == "OpenAI":
                ss.openai_no_credits = True
    ss.llm_status = results or [("error", "No AI key is set (OPENAI_API_KEY or GEMINI_API_KEY).")]


with st.sidebar:
    st.button("New chat", icon=":material/add:", type="primary", width="stretch", on_click=start_chat)
    st.markdown('<div class="mv-section">Chats</div>', unsafe_allow_html=True)
    for cid, c in reversed(list(ss.conversations.items())):
        a, b = st.columns([6, 1], vertical_alignment="center")
        active = cid == ss.active_chat
        a.button(c["title"], key=f"chat_{cid}", width="stretch", on_click=open_chat, args=(cid,),
                 type="secondary" if active else "tertiary", icon=":material/chat_bubble:" if active else None)
        b.button("", key=f"del_{cid}", icon=":material/close:", type="tertiary", help="Delete chat",
                 on_click=delete_chat, args=(cid,))
    with st.expander("Connection", icon=":material/key:"):
        keys = [name for name, k in (("OpenAI", "OPENAI_API_KEY"), ("Google Gemini", "GEMINI_API_KEY"))
                if get_secret(k)]
        st.caption("Keys loaded from secrets: " + (", ".join(keys) if keys else "none") +
                   ". OpenAI is tried first; Gemini answers when OpenAI fails (for example, no credits).")
        if keys:
            st.button("Test connection", icon=":material/network_check:", on_click=test_connection, width="stretch")
        for kind, text in ss.get("llm_status") or []:
            (st.success if kind == "ok" else st.error)(text)

conv = ss.conversations[ss.active_chat]
if conv["messages"]:
    st.sidebar.download_button("Export chat", conversation_markdown(conv, DISCLAIMER),
                               file_name="medvisionai_chat.md", mime="text/markdown",
                               icon=":material/ios_share:", type="tertiary", width="stretch")


# ----------------------------------------------------------------------------- rendering
def render(msg: dict) -> None:
    with st.chat_message(msg["role"], avatar=USER_AVATAR if msg["role"] == "user" else ASSISTANT_AVATAR):
        case = ss.cases.get(msg.get("case_id") or "")
        if case:
            r = case["report"]
            st.image(case["thumb"], width=160,
                     caption=f"Analysis: {r['filename']} · {r['finding']} · confidence {r['confidence'].lower()}")
        if msg["images"]:
            st.image([downscale(load_image(b, MAX_UPLOAD_MB), 320) for b in msg["images"]], width=160)
        if msg["kind"] == "error":
            st.error(msg["content"], icon=":material/cloud_off:")
        elif msg["content"]:
            st.markdown(msg["content"])
        if msg.get("note"):
            st.caption(msg["note"])


def send(text: str, images: list[bytes], case_id: str | None) -> None:
    user = add_message(conv, "user", text, images, case_id)
    render(user)
    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        providers = get_providers()
        if not providers:
            msg = ("The AI Assistant needs an API key. Add `OPENAI_API_KEY` or a free `GEMINI_API_KEY` to "
                   "`.streamlit/secrets.toml` and refresh the page. Tissue analysis works without it.")
            st.error(msg, icon=":material/key_off:")
            add_message(conv, "assistant", msg, kind="error")
            return
        used: dict = {}
        try:
            reply = st.write_stream(stream_with_fallback(
                providers, SYSTEM_PROMPT, build_llm_messages(conv, ss.cases, LLM_HISTORY_MESSAGES), used))
            reply = (reply if isinstance(reply, str) else "".join(map(str, reply))).strip()
        except LLMError as e:
            msg = str(e)
            if "no credits" in msg and not get_secret("GEMINI_API_KEY"):
                msg += (" Or add a free `GEMINI_API_KEY` (https://aistudio.google.com/apikey) to "
                        "`.streamlit/secrets.toml` and refresh: Gemini then answers instead.")
            st.error(msg, icon=":material/cloud_off:")
            add_message(conv, "assistant", msg, kind="error")
            return
        except Exception as e:      # network failure mid-stream; never show secrets or tracebacks
            msg = f"The answer was interrupted ({type(e).__name__}). Please try again."
            st.error(msg, icon=":material/cloud_off:")
            add_message(conv, "assistant", msg, kind="error")
            return
        note = f"{used['provider'].label} · AI answers can be wrong; verify with a specialist."
        if used.get("skipped"):
            first = used["skipped"][0]
            reason = ("OpenAI has no credits" if "no credits" in first
                      else f"{len(used['skipped'])} model(s) unavailable")
            note = f"{used['provider'].label} (fallback: {reason}) · AI answers can be wrong; verify with a specialist."
        st.caption(note)
        add_message(conv, "assistant", reply)["note"] = note


# ----------------------------------------------------------------------------- page
st.markdown('<div class="mv-eyebrow">AI Assistant</div>', unsafe_allow_html=True)
st.title("Ask about your images, or anything colorectal.")
if not ai_configured():
    secrets_file = ROOT / ".streamlit" / "secrets.toml"
    st.warning(f"The assistant is offline: no AI key found.\n\nOpen `{secrets_file}` and set "
               '`OPENAI_API_KEY = "sk-..."` and/or a free `GEMINI_API_KEY = "..."` (create one at '
               "https://aistudio.google.com/apikey), save, and refresh this page. Tissue analysis works without it.",
               icon=":material/key_off:")
elif ss.get("openai_no_credits") and not get_secret("GEMINI_API_KEY"):
    st.warning("Your OpenAI account has no credits left. Add credits at "
               "https://platform.openai.com/settings/organization/billing, or add a free `GEMINI_API_KEY` "
               "(https://aistudio.google.com/apikey) to `.streamlit/secrets.toml` and refresh.",
               icon=":material/credit_card_off:")

# attach an analysed case to the next message
case_ids = list(reversed(ss.case_order))
attach_labels = {None: "No analysis attached"} | {
    cid: f"{ss.cases[cid]['report']['filename']} · {ss.cases[cid]['report']['finding']}" for cid in case_ids}
attach_key = f"attach_case_{ss.setdefault('attach_n', 0)}"     # new key after each send resets the choice
if case_ids:
    st.selectbox("Attach an analysis to your next message", list(attach_labels), format_func=attach_labels.get,
                 key=attach_key, help="Sends the image, its Grad-CAM overlay and the classification report.")

if not conv["messages"]:
    st.markdown("Examples: *“What does cancer-associated stroma look like?”*, *“Explain this analysis”* (attach one "
                "above), or attach a picture with the **+** button below.")
for m in conv["messages"]:
    render(m)

pending = ss.pop("pending_send", None)       # "Discuss in AI Assistant" from the analysis page
prompt = st.chat_input("Message MedVisionAI…", accept_file="multiple", file_type=ALLOWED_EXTENSIONS,
                       max_chars=6000, disabled=not ai_configured())
if pending:
    send(pending["text"], [], pending["case_id"])
elif prompt:
    images, errors = [], []
    for f in (prompt.files or [])[:4]:
        try:
            images.append(to_bytes(downscale(load_image(f.getvalue(), MAX_UPLOAD_MB), LLM_IMAGE_MAX_SIDE), "JPEG"))
        except ImageError as e:
            errors.append(f"{f.name}: {e}")
    for e in errors:
        st.toast(e, icon=":material/error:")
    text = (prompt.text or "").strip()
    attached = ss.get(attach_key)
    if text or images:
        send(text, images, attached)
        if attached:
            ss.attach_n += 1
            st.rerun()
