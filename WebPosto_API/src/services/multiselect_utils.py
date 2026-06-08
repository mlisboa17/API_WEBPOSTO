from __future__ import annotations

import re
from typing import Any

NETWORK_WIDE_TOKENS = frozenset({"todos", "all", "__all__"})


def is_network_wide_empresa(value: str | int | None) -> bool:
    """True quando filtro representa rede inteira (empresaCodigo omitido na API)."""
    if value is None:
        return True
    if isinstance(value, int):
        return False
    text = str(value).strip()
    if not text:
        return True
    if text.casefold() in NETWORK_WIDE_TOKENS:
        return True
    return len(parse_empresa_codigos(value)) == 0


def parse_empresa_codigos(value: str | int | None) -> list[int]:
    if value is None:
        return []
    if isinstance(value, int):
        return [value]
    text = str(value).strip()
    if not text or text.casefold() in NETWORK_WIDE_TOKENS:
        return []
    codes: list[int] = []
    for chunk in re.split(r"[,;]", text):
        item = chunk.strip()
        if item.isdigit():
            codes.append(int(item))
    return codes


def empresa_codigo_cache_key(value: str | int | None) -> str | int | None:
    codes = parse_empresa_codigos(value)
    if not codes:
        return None
    if len(codes) == 1:
        return codes[0]
    return ",".join(str(code) for code in sorted(codes))


def empresa_snapshot_suffix(value: str | int | None) -> str:
    """Chave normalizada para snapshots — nunca persiste literal 'Todos'."""
    if is_network_wide_empresa(value):
        return "all"
    key = empresa_codigo_cache_key(value)
    return str(key) if key is not None else "all"


def normalize_empresa_query_param(value: str | int | None) -> str | int | None:
    """Normaliza query param: rede → None (omitir na API)."""
    if is_network_wide_empresa(value):
        return None
    return value
