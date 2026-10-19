"""AI Assistant conversations (kept only in the user's session) and conversion to provider messages."""
from __future__ import annotations

import uuid
from datetime import datetime

from .llm import ChatMessage, case_context


def new_conversation() -> dict:
    return {"id": uuid.uuid4().hex[:10], "title": "New chat", "created": datetime.now().strftime("%H:%M"),
            "messages": []}


def add_message(conv: dict, role: str, text: str, images: list[bytes] | None = None,
                case_id: str | None = None, kind: str = "text") -> dict:
    """kind: "text" | "error". `images` are JPEG bytes attached by the user; `case_id` links an analysed case."""
    msg = {"id": uuid.uuid4().hex[:10], "role": role, "kind": kind, "content": text, "images": images or [],
           "case_id": case_id}
    conv["messages"].append(msg)
    if role == "user" and conv["title"] == "New chat":
        label = text.strip() or ("Case discussion" if case_id else "Image question")
        conv["title"] = label[:40] + ("…" if len(label) > 40 else "")
    return msg


def build_llm_messages(conv: dict, cases: dict, max_messages: int) -> list[ChatMessage]:
    """History for the provider. Only the newest user message with pictures carries them, to limit cost."""
    msgs = [m for m in conv["messages"] if m["kind"] != "error"][-max_messages:]
    last_with_pictures = None
    for m in msgs:
        if m["role"] == "user" and (m["images"] or (m["case_id"] in cases)):
            last_with_pictures = m["id"]
    out: list[ChatMessage] = []
    for m in msgs:
        if m["role"] != "user":
            if m["content"]:
                out.append(ChatMessage("assistant", m["content"]))
            continue
        text, images = m["content"] or "", []
        case = cases.get(m["case_id"] or "")
        if case:
            text = (text or "Please explain this MedVisionAI result.") + "\n\n" + case_context(case["report_llm"])
        if m["id"] == last_with_pictures:
            if case:
                images += case["llm_images"]
                text += "\n\n(Attached: the analysed image and its Grad-CAM overlay.)"
            images += m["images"]
        elif case or m["images"]:
            text += "\n\n(Images shared earlier are no longer attached; rely on the text above.)"
        out.append(ChatMessage("user", text or "(image)", images))
    merged: list[ChatMessage] = []
    for m in out:          # providers expect alternating turns
        if merged and merged[-1].role == m.role:
            merged[-1] = ChatMessage(m.role, merged[-1].text + "\n\n" + m.text, merged[-1].images + m.images)
        else:
            merged.append(m)
    while merged and merged[0].role != "user":
        merged.pop(0)
    return merged


def conversation_markdown(conv: dict, disclaimer: str) -> str:
    lines = [f"# MedVisionAI assistant: {conv['title']}", "", f"> {disclaimer}", ""]
    for m in conv["messages"]:
        lines.append("### " + ("You" if m["role"] == "user" else "MedVisionAI"))
        if m["case_id"]:
            lines.append("_Attached: MedVisionAI analysis_")
        if m["images"]:
            lines.append(f"_Attached: {len(m['images'])} image(s)_")
        lines += [m["content"], ""]
    return "\n".join(lines)
