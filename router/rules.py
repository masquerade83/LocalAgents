"""Content-aware model selection for Hermes stack router."""
from __future__ import annotations

import re
from typing import Any

# Models that are always forwarded unchanged (auxiliary vision, n8n explicit picks).
PASS_THROUGH = frozenset({"deepseek-ocr", "qwen3-vl"})

# Local Ollama chat models — no reliable tool-calling; Hermes Agent must not send tools.
NON_AGENTIC_TEXT = frozenset({"hermes3", "llama3", "deepseek-ocr"})

# Main-chat aliases that trigger content-based routing.
AUTO_ALIASES = frozenset({"hermes3", "hermes-auto", "auto", "llama3", "qwen3-vl"})

OCR_KEYWORDS = (
    "ocr",
    "extract text",
    "read this image",
    "read the image",
    "scan",
    "transcribe",
    "what does it say",
    "text from",
)

VISION_KEYWORDS = (
    "describe",
    "what is in",
    "what's in",
    "explain this image",
    "explain the image",
    "diagram",
    "what do you see",
    "identify",
    "caption",
)

# Escalate to qwen3-vl (keep tools) when the agent sends tools and the prompt needs them.
AGENT_TOOL_KEYWORDS = (
    "run ",
    "execute",
    "terminal",
    "search",
    "browse",
    "web ",
    "file",
    "read ",
    "write ",
    "code",
    "script",
    "grep",
    "install",
    "deploy",
    "curl ",
    "git ",
    "python",
    "summarize this url",
    "look up",
)


def _message_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(str(block.get("text", "")))
                elif block.get("type") == "image_url":
                    parts.append("[image]")
        return " ".join(parts)
    return str(content)


def has_image_url(messages: list[dict[str, Any]]) -> bool:
    for msg in messages or []:
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "image_url":
                return True
    return False


def extract_text(messages: list[dict[str, Any]]) -> str:
    chunks = [_message_text(m.get("content")) for m in messages or []]
    return " ".join(c for c in chunks if c).strip()


def wants_vision_description(text: str) -> bool:
    lower = text.lower()
    return any(k in lower for k in VISION_KEYWORDS)


def wants_ocr(text: str) -> bool:
    lower = text.lower()
    return any(k in lower for k in OCR_KEYWORDS)


def is_simple_text(text: str) -> bool:
    if not text:
        return True
    words = re.findall(r"\w+", text)
    return len(words) <= 10 and "\n" not in text


def wants_agent_model(text: str, has_tools: bool) -> bool:
    """Use qwen3-vl (tool-capable) for complex or action-oriented agent turns."""
    if not has_tools:
        return False
    words = re.findall(r"\w+", text)
    if len(words) > 30:
        return True
    lower = text.lower()
    return any(k in lower for k in AGENT_TOOL_KEYWORDS)


def pick_model(
    requested: str | None,
    messages: list[dict[str, Any]],
    *,
    has_tools: bool = False,
) -> tuple[str, str]:
    """Return (model_name, reason) for LiteLLM upstream."""
    model = (requested or "hermes3").strip()
    lower_model = model.lower()

    if lower_model in PASS_THROUGH:
        return lower_model, "explicit model pass-through"

    text = extract_text(messages)
    if has_image_url(messages):
        if wants_vision_description(text):
            return "qwen3-vl", "image + vision/describe keywords"
        return "deepseek-ocr", "image present (default OCR)"

    if lower_model == "llama3":
        return "llama3", "explicit llama3 text"

    if lower_model in AUTO_ALIASES or lower_model.startswith("hermes"):
        if has_tools and wants_agent_model(text, has_tools):
            return "qwen3-vl", "agent tools + action keywords or long prompt"
        if is_simple_text(text):
            return "llama3", "short text prompt"
        return "hermes3", "default text chat"

    return model, "unrecognized model forwarded as-is"


def should_strip_tools(model: str) -> bool:
    """True for local chat models that hallucinate tool_calls or return `{}` with tools."""
    return model.lower() in NON_AGENTIC_TEXT
