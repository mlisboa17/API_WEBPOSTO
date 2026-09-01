"""Sanitização de logs e respostas operacionais do SDS. Nunca preserva segredo."""

from __future__ import annotations

import re
from typing import Any

_SENSITIVE_KEY = re.compile(
    r"(token|chave|password|passwd|secret|authorization|cookie|api[_-]?key|bearer|refresh)",
    re.IGNORECASE,
)
_INLINE_SECRET = re.compile(
    r"(?i)\b(chave|token|bearer|password|authorization|api[_-]?key)=[^\s&]+"
)
_URL_WITH_QUERY = re.compile(r"https?://[^\s]+", re.IGNORECASE)


def sanitize_text(value: str) -> str:
    text = _INLINE_SECRET.sub(r"\1=[redacted]", value)
    text = _URL_WITH_QUERY.sub("[url-redacted]", text)
    return text


def sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if _SENSITIVE_KEY.search(str(key)):
                out[str(key)] = "[redacted]"
                continue
            out[str(key)] = sanitize_value(item)
        return out
    if isinstance(value, list):
        return [sanitize_value(item) for item in value]
    if isinstance(value, str):
        return sanitize_text(value)
    return value
