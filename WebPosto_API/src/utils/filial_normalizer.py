"""Normalização de filial UI/query → código real WebPosto (empresaCodigo).

Aliases ordinais (1/001, 2/002, 3/003) e nomes comerciais resolvem para:
  Casa Caiada → 5555 | VIP → 11495 | Real Doze → 74014
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

EMPRESA_CASA_CAIADA = 5555
EMPRESA_VIP = 11495
EMPRESA_REAL_DOZE = 74014

ORDINAL_TO_EMPRESA: dict[int, int] = {
    1: EMPRESA_CASA_CAIADA,
    2: EMPRESA_VIP,
    3: EMPRESA_REAL_DOZE,
}

EMPRESA_TO_ORDINAL: dict[int, int] = {
    EMPRESA_CASA_CAIADA: 1,
    EMPRESA_VIP: 2,
    EMPRESA_REAL_DOZE: 3,
}

_ALIAS_TO_EMPRESA: dict[str, int] = {
    "1": EMPRESA_CASA_CAIADA,
    "01": EMPRESA_CASA_CAIADA,
    "001": EMPRESA_CASA_CAIADA,
    "5555": EMPRESA_CASA_CAIADA,
    "casa": EMPRESA_CASA_CAIADA,
    "casacaiada": EMPRESA_CASA_CAIADA,
    "apcasacaiada": EMPRESA_CASA_CAIADA,
    "2": EMPRESA_VIP,
    "02": EMPRESA_VIP,
    "002": EMPRESA_VIP,
    "11495": EMPRESA_VIP,
    "vip": EMPRESA_VIP,
    "postovip": EMPRESA_VIP,
    "3": EMPRESA_REAL_DOZE,
    "03": EMPRESA_REAL_DOZE,
    "003": EMPRESA_REAL_DOZE,
    "74014": EMPRESA_REAL_DOZE,
    "doze": EMPRESA_REAL_DOZE,
    "real": EMPRESA_REAL_DOZE,
    "realdoze": EMPRESA_REAL_DOZE,
    "postodoze": EMPRESA_REAL_DOZE,
    "postoreal": EMPRESA_REAL_DOZE,
    "postorealdoze": EMPRESA_REAL_DOZE,
    "postodozefilialii": EMPRESA_REAL_DOZE,
}


def _slugify(value: str) -> str:
    norm = unicodedata.normalize("NFD", value)
    ascii_only = "".join(ch for ch in norm if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]+", "", ascii_only.lower())


def is_todas_filiais(raw: Any) -> bool:
    if raw is None or raw == "":
        return True
    if isinstance(raw, (int, float)) and int(raw) == 0:
        return True
    s = str(raw).strip().upper()
    return s in {"0", "TODAS", "ALL", "CONSOLIDADO", "TODAS AS FILIAIS"}


def resolve_empresa_codigo(raw: Any) -> int | None:
    """Resolve nome/slug/ordinal/código → empresaCodigo WebPosto. None = TODAS."""
    if is_todas_filiais(raw):
        return None

    if isinstance(raw, bool):
        return None

    if isinstance(raw, (int, float)):
        n = int(raw)
        if n in (EMPRESA_CASA_CAIADA, EMPRESA_VIP, EMPRESA_REAL_DOZE):
            return n
        if n in ORDINAL_TO_EMPRESA:
            return ORDINAL_TO_EMPRESA[n]
        return n if n > 0 else None

    text = str(raw).strip()
    if not text:
        return None

    if re.fullmatch(r"\d+", text):
        return resolve_empresa_codigo(int(text))

    slug = _slugify(text)
    if slug in _ALIAS_TO_EMPRESA:
        return _ALIAS_TO_EMPRESA[slug]

    if "caiada" in slug or ("casa" in slug and "real" not in slug):
        return EMPRESA_CASA_CAIADA
    if "vip" in slug:
        return EMPRESA_VIP
    if "doze" in slug or "real" in slug:
        return EMPRESA_REAL_DOZE

    return None
