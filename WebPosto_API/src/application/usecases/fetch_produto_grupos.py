"""
Grupos de produto: cadastro completo GET /INTEGRACAO/GRUPO + contagem via PRODUTO.
"""

from __future__ import annotations

from typing import Any, Optional

from src.application.usecases.fetch_produtos_catalog import (
    map_raw_produto,
    parse_produto_response,
)
from src.application.usecases.fetch_unidade_webposto import fetch_unidade_webposto
from src.domain.catalog.grupo_schema import GruposProdutoResponse, ProdutoGrupoItem


def _rows_from_raw(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [r for r in raw if isinstance(r, dict)]
    if isinstance(raw, dict):
        rows = raw.get("resultados") or raw.get("data") or []
        return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []
    return []


def _extrair_grupos_das_linhas(rows: list[dict[str, Any]], nomes: dict[int, str]) -> None:
    for row in rows:
        cod = row.get("grupoCodigo") or row.get("codigo")
        nome = row.get("nome") or row.get("descricao") or row.get("nomeGrupo")
        if cod is None:
            continue
        gid = int(cod)
        nomes[gid] = str(nome or f"Grupo {gid}").strip()


def _paginar_grupos_endpoint(
    webposto_client: Any,
    listar_fn: Any,
    nomes: dict[int, str],
    *,
    max_paginas: int,
) -> None:
    for pagina in range(max(1, max_paginas)):
        raw = listar_fn(pagina=pagina, tamanho_pagina=200)
        rows = _rows_from_raw(raw)
        if not rows:
            break
        _extrair_grupos_das_linhas(rows, nomes)
        if len(rows) < 200:
            break


def _carregar_todos_grupos_cadastro(
    webposto_client: Any,
    *,
    max_paginas: int = 50,
) -> dict[int, str]:
    """
    Todos os grupos: GET /INTEGRACAO/GRUPO + /INTEGRACAO/GRUPO_META
    (conforme collections oficiais Quality no Postman).
    """
    nomes: dict[int, str] = {}
    _paginar_grupos_endpoint(
        webposto_client,
        webposto_client.integracoes.listar_grupos_produto,
        nomes,
        max_paginas=max_paginas,
    )
    try:
        _paginar_grupos_endpoint(
            webposto_client,
            webposto_client.integracoes.listar_grupos_produto_meta,
            nomes,
            max_paginas=max_paginas,
        )
    except Exception:
        pass
    return nomes


def _indexar_produtos_por_grupo(
    webposto_client: Any,
    nomes_grupo: dict[int, str],
    *,
    max_paginas_produto: int = 25,
    tamanho_pagina: int = 200,
) -> tuple[dict[int, dict[str, Any]], int]:
    """Varre PRODUTO paginado e conta itens por grupoCodigo."""
    buckets: dict[int, dict[str, Any]] = {
        gid: {"codigo": gid, "nome": nome, "codigos": set()}
        for gid, nome in nomes_grupo.items()
    }
    total_produtos = 0
    for pagina in range(max(1, max_paginas_produto)):
        raw = webposto_client._http.get(
            "/INTEGRACAO/PRODUTO",
            {"pagina": pagina, "tamanhoPagina": tamanho_pagina},
        )
        rows, _ = parse_produto_response(raw, pagina + 1, tamanho_pagina)
        if not rows:
            break
        for row in rows:
            if not isinstance(row, dict):
                continue
            prod = map_raw_produto(row)
            gid_raw = prod.codigo_grupo or row.get("grupoCodigo") or row.get("codigoGrupo")
            if gid_raw is None:
                continue
            try:
                gid = int(gid_raw)
            except (TypeError, ValueError):
                continue
            if gid not in buckets:
                buckets[gid] = {
                    "codigo": gid,
                    "nome": nomes_grupo.get(gid, str(prod.nome_grupo or f"Grupo {gid}")),
                    "codigos": set(),
                }
            buckets[gid]["codigos"].add(str(prod.id))
        total_produtos += len(rows)
        if len(rows) < tamanho_pagina:
            break
    return buckets, total_produtos


async def fetch_codigos_produtos_grupos(
    webposto_client: Any,
    grupos_ids: list[int],
    *,
    max_paginas_por_grupo: int = 30,
) -> list[str]:
    """Códigos de produto por grupo (filtro grupoCodigo na API)."""
    codigos: set[str] = set()
    for gid in grupos_ids:
        for pagina in range(max_paginas_por_grupo):
            raw = webposto_client._http.get(
                "/INTEGRACAO/PRODUTO",
                {
                    "pagina": pagina,
                    "tamanhoPagina": 200,
                    "grupoCodigo": int(gid),
                },
            )
            rows, _ = parse_produto_response(raw, pagina + 1, 200)
            if not rows:
                break
            for row in rows:
                if isinstance(row, dict):
                    p = map_raw_produto(row)
                    codigos.add(str(p.id))
            if len(rows) < 200:
                break
    return sorted(codigos, key=lambda x: int(x) if str(x).isdigit() else x)


async def fetch_produto_grupos(
    webposto_client: Any,
    *,
    base_url: str = "",
    chave: str = "",
    max_paginas_grupo: int = 50,
    max_paginas_produto: int = 25,
) -> GruposProdutoResponse:
    """Todos os grupos do cadastro WebPosto, com contagem de produtos quando disponível."""
    import asyncio
    unidade = await fetch_unidade_webposto(
        webposto_client, base_url=base_url, chave=chave
    )
    nomes_grupo = await asyncio.to_thread(
        _carregar_todos_grupos_cadastro,
        webposto_client,
        max_paginas=max_paginas_grupo,
    )
    buckets, total_produtos = await asyncio.to_thread(
        _indexar_produtos_por_grupo,
        webposto_client,
        nomes_grupo,
        max_paginas_produto=max_paginas_produto,
    )

    grupos = [
        ProdutoGrupoItem(
            codigo=b["codigo"],
            nome=b["nome"],
            qtd_produtos=len(b["codigos"]),
            codigos_produto=sorted(
                b["codigos"], key=lambda x: int(x) if str(x).isdigit() else x
            ),
        )
        for b in sorted(buckets.values(), key=lambda x: x["nome"].lower())
    ]
    com_produtos = sum(1 for g in grupos if g.qtd_produtos > 0)

    return GruposProdutoResponse(
        unidade=unidade,
        total_grupos=len(grupos),
        total_grupos_sistema=len(nomes_grupo),
        grupos_com_produtos_catalogo=com_produtos,
        total_produtos_indexados=total_produtos,
        grupos=grupos,
        fonte="webposto_integracao",
    )


def codigos_produto_dos_grupos(
    grupos_resp: GruposProdutoResponse,
    grupos_ids: list[int],
) -> list[str]:
    alvo = {int(g) for g in grupos_ids}
    codigos: set[str] = set()
    for g in grupos_resp.grupos:
        if g.codigo in alvo:
            codigos.update(g.codigos_produto)
    return sorted(codigos, key=lambda x: int(x) if str(x).isdigit() else x)


def mesclar_filtro_codigos(
    codigos_tipo: Optional[list[str]],
    codigos_grupos: list[str],
) -> Optional[list[str]]:
    if codigos_tipo is None:
        return codigos_grupos
    tipo_set = {str(c).strip() for c in codigos_tipo if str(c).strip()}
    grupo_set = {str(c).strip() for c in codigos_grupos if str(c).strip()}
    return sorted(tipo_set & grupo_set)
