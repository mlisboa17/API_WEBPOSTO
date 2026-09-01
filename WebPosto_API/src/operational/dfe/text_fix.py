"""Correção de apresentação UTF-8 (mojibake) — não altera XML original."""

from __future__ import annotations


def fix_mojibake(value: str | None) -> str | None:
    """Converte sequências típicas latin1←UTF-8 (ex.: NestlÃ© → Nestlé)."""
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    if not value:
        return value
    # Heurística: presença de padrões comuns de mojibake
    markers = ("Ã", "Â", "â€™", "â€", "Ã¡", "Ã©", "Ã­", "Ã³", "Ãº", "Ã£", "Ã§")
    if not any(m in value for m in markers):
        return value
    try:
        fixed = value.encode("latin-1").decode("utf-8")
        # só aceita se melhorou (menos marcadores)
        if sum(fixed.count(m) for m in markers) < sum(value.count(m) for m in markers):
            return fixed
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass
    return value


def fix_tree(obj):
    if isinstance(obj, str):
        return fix_mojibake(obj)
    if isinstance(obj, list):
        return [fix_tree(x) for x in obj]
    if isinstance(obj, dict):
        return {k: fix_tree(v) for k, v in obj.items()}
    return obj
