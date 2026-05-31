"""Busca paginada de vendas PDV no período."""

from __future__ import annotations

import asyncio
from datetime import date
from typing import Any, Optional


async def fetch_vendas_periodo(
    webposto_client: Any,
    data_inicial: date,
    data_final: date,
    *,
    filial: Optional[list[int]] = None,
    max_paginas: int = 40,
    tamanho_pagina: int = 200,
) -> list[dict[str, Any]]:
    todas: list[dict[str, Any]] = []
    ultimo_codigo: Optional[int] = None
    prev_codigo: Optional[int] = None

    for _ in range(max_paginas):
        raw = await asyncio.to_thread(
            webposto_client.integracoes.listar_vendas,
            data_inicial,
            data_final,
            filial=filial,
            tamanho_pagina=tamanho_pagina,
            ultimo_codigo=ultimo_codigo,
        )
        if isinstance(raw, list):
            batch = raw
            novo_ultimo = None
        elif isinstance(raw, dict):
            batch = raw.get("resultados") or raw.get("data") or []
            novo_ultimo = raw.get("ultimoCodigo")
        else:
            batch = []
            novo_ultimo = None

        if not batch:
            break

        todas.extend(r for r in batch if isinstance(r, dict))
        if novo_ultimo in (None, "") or novo_ultimo == prev_codigo or len(batch) < tamanho_pagina:
            break

        prev_codigo = ultimo_codigo
        ultimo_codigo = novo_ultimo

    return todas
