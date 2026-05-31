"""Paginação completa WebPosto — sem truncar nem inventar registros."""

from __future__ import annotations

from datetime import date
from typing import Any, Callable, List, Optional


def _extract_rows(payload: Any) -> tuple[list[dict], Any]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)], None
    if isinstance(payload, dict):
        inner = payload.get("resultados") or payload.get("data") or []
        rows = [r for r in inner if isinstance(r, dict)] if isinstance(inner, list) else []
        return rows, payload.get("ultimoCodigo")
    return [], None


def fetch_all_abastecimento(
    abastecimento_api: Any,
    data_inicial: date,
    data_final: date,
    *,
    filial: Optional[List[int]] = None,
    tamanho_pagina: int = 200,
    max_requests: int = 80,
) -> list[dict]:
    """ABASTECIMENTO com cursor ultimoCodigo (igual ao dashboard operacional)."""
    todas: list[dict] = []
    ultimo_codigo: Any = None
    prev: Any = None

    for _ in range(max_requests):
        raw = abastecimento_api.listar(
            data_inicial,
            data_final,
            filial=filial,
            tamanho_pagina=tamanho_pagina,
            ultimo_codigo=ultimo_codigo,
        )
        batch, meta_ultimo = _extract_rows(raw)
        if isinstance(raw, dict) and raw.get("ultimoCodigo") is not None:
            novo = raw.get("ultimoCodigo")
        else:
            novo = meta_ultimo

        if not batch:
            break
        todas.extend(batch)
        if novo in (None, "") or novo == prev:
            break
        prev = ultimo_codigo
        ultimo_codigo = novo

    return todas


def fetch_all_paginated(
    list_fn: Callable[..., Any],
    data_inicial: date,
    data_final: date,
    *,
    filial: Optional[List[int]] = None,
    tamanho_pagina: int = 200,
    max_paginas: int = 50,
    extra_params: Optional[dict] = None,
) -> list[dict]:
    """Endpoints com pagina numérica (VENDA, CAIXA, TITULO_PAGAR, …)."""
    todas: list[dict] = []
    extra = extra_params or {}

    for pagina in range(max_paginas):
        raw = list_fn(
            data_inicial,
            data_final,
            filial=filial,
            pagina=pagina,
            tamanho_pagina=tamanho_pagina,
            **extra,
        )
        batch, _ = _extract_rows(raw)
        if not batch:
            break
        todas.extend(batch)
        if len(batch) < tamanho_pagina:
            break

    return todas
