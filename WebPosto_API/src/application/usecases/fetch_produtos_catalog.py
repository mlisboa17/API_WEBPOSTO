"""
Caso de uso: catálogo paginado via GET /INTEGRACAO/PRODUTO (CHAVE na query).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal, Optional

from src.domain.catalog.product_schema import (
    PaginatedProdutosResponse,
    WebPostoProdutoSchema,
)

SituacaoProduto = Literal["todos", "ativos", "inativos"]


def is_active_fuel_product(row: dict[str, Any]) -> bool:
    if not isinstance(row, dict):
        return False

    # Check if active / status / situacao
    def _is_active(v: Any) -> bool:
        if v is None:
            return True
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        if s in ("false", "0", "inativo", "inativos", "n", "nao", "não", "inactive", "i"):
            return False
        return True

    active = True
    for key in ("ativo", "status", "situacao", "situação", "produtoAtivo"):
        if key in row and row[key] is not None:
            if not _is_active(row[key]):
                active = False
                break
    if not active:
        return False

    import unicodedata
    def _normalize(val: Any) -> str:
        if val is None:
            return ""
        s = str(val).strip().casefold()
        s = "".join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
        return s

    fuel_keywords = {"combustivel", "combustiveis", "fuel"}
    for key in (
        "tipoProduto", "tipoProdutoCodigo", "grupoProduto", "grupoProdutoCodigo",
        "produtoTipo", "produtoGrupo", "descricaoTipo", "descricaoGrupo", "tipoCombustivel"
    ):
        val = _normalize(row.get(key))
        if val in fuel_keywords or any(kw in val for kw in fuel_keywords):
            return True

    if row.get("combustivel") is True:
        return True

    tp = str(row.get("tipoProduto") or row.get("produtoTipo") or "").strip().upper()
    if tp == "C":
        return True

    desc = _normalize(row.get("nome") or row.get("descricao") or row.get("produto") or "")
    for kw in fuel_keywords:
        if kw in desc:
            return True
    for kw in {"gasolina", "etanol", "diesel", "gnv", "comb."}:
        if kw in desc:
            return True

    return False


def _primeiro(row: dict, *chaves: str, default=None):
    for k in chaves:
        if row.get(k) is not None and row.get(k) != "":
            return row.get(k)
    return default


def _parse_bool_ativo(val: Any) -> bool:
    if val is None:
        return True
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    if s in ("false", "n", "0", "inativo", "i", "nao", "não"):
        return False
    return True


def map_raw_produto(
    row: dict[str, Any],
    empresa_row: Optional[dict[str, Any]] = None,
) -> WebPostoProdutoSchema:
    """Mapeia registro bruto da Quality para o schema corporativo."""
    pid = int(
        _primeiro(row, "produtoCodigo", "codigo", "codigoProduto", "id", default=0) or 0
    )
    nome = str(_primeiro(row, "nome", "descricao", "descricaoProduto", default="") or "").strip()
    cst = _primeiro(row, "cstIcms", "cst", "cst_icms", "codigoCst")
    if cst is not None:
        cst = str(cst).zfill(3) if str(cst).isdigit() else str(cst)

    preco_venda = _primeiro(row, "precoVenda", "preco", "valorVenda", default=0)
    preco_custo = _primeiro(row, "precoCusto", "custo", default=0)
    ativo_val = row.get("ativo")

    if empresa_row:
        preco_venda = _primeiro(
            empresa_row, "precoVenda", "precoVendaA", default=preco_venda
        )
        preco_custo = _primeiro(empresa_row, "precoCusto", default=preco_custo)
        if empresa_row.get("ativo") is not None:
            ativo_val = empresa_row.get("ativo")

    return WebPostoProdutoSchema(
        id=pid,
        codigoBarras=_primeiro(row, "codigoBarras", "referenciaCodigo", "ean", "gtin"),
        descricao=nome or f"Produto {pid}",
        precoVenda=preco_venda,
        precoCusto=preco_custo,
        ativo=_parse_bool_ativo(ativo_val),
        estoqueAtual=_primeiro(
            row, "estoqueAtual", "estoque", "saldo", "quantidadeEstoque", "estoqueQtde", default=0
        ),
        unidadeMedida=str(_primeiro(row, "unidadeMedida", "unidade", "unidadeVenda", default="UN") or "UN"),
        ncm=_primeiro(row, "ncm", "codigoNcm", "NCM"),
        cest=_primeiro(row, "cest", "codigoCest"),
        cstIcms=cst,
        aliquotaIcms=_primeiro(row, "aliquotaIcms", "aliquota", "percentualIcms"),
        codigoGrupo=_primeiro(row, "grupoCodigo", "codigoGrupo", "grupo"),
        nomeGrupo=_primeiro(row, "nomeGrupo", "grupoNome", "descricaoGrupo"),
        subGrupo1Codigo=_primeiro(row, "subGrupo1Codigo", "subgrupo1Codigo"),
        subGrupo2Codigo=_primeiro(row, "subGrupo2Codigo", "subgrupo2Codigo"),
        subGrupo3Codigo=_primeiro(row, "subGrupo3Codigo", "subgrupo3Codigo"),
        tipoProduto=_primeiro(row, "tipoProduto", "tipo_produto"),
        tipoCombustivel=_primeiro(row, "tipoCombustivel", "tipo_combustivel"),
        combustivel=bool(
            row.get("combustivel")
            or row.get("tipoCombustivel")
            or str(row.get("tipoProduto") or "").upper() == "C"
        ),
    )


def _rows_from_raw(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [r for r in raw if isinstance(r, dict)]
    if isinstance(raw, dict):
        rows = raw.get("resultados") or raw.get("data") or raw.get("items") or []
        return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []
    return []


def _buscar_linha_produto(
    webposto_client: Any,
    produto_id: int,
) -> dict[str, Any]:
    """Busca cadastro em GET /INTEGRACAO/PRODUTO?codigo=."""
    try:
        raw = webposto_client.produtos.listar(
            codigo=produto_id,
            pagina=0,
            tamanho_pagina=5,
        )
        rows, _ = parse_produto_response(raw, 1, 5)
        for row in rows:
            cod = row.get("produtoCodigo") or row.get("codigo")
            if cod is not None and int(cod) == produto_id:
                return row
        if rows:
            return rows[0]
    except Exception:
        pass
    return {"produtoCodigo": produto_id, "codigo": produto_id}


def _buscar_linha_empresa(
    webposto_client: Any,
    produto_id: int,
) -> Optional[dict[str, Any]]:
    """Preço venda A e custo em GET /INTEGRACAO/PRODUTO_EMPRESA."""
    try:
        raw = webposto_client.produtos.listar_empresa(
            produto_codigo=produto_id,
            pagina=0,
            tamanho_pagina=10,
        )
        rows = _rows_from_raw(raw)
        for row in rows:
            cod = row.get("produtoCodigo") or row.get("codigo")
            if cod is not None and int(cod) == produto_id:
                return row
        if rows:
            return rows[0]
    except Exception:
        pass
    return None


def _carregar_mapa_empresa(
    webposto_client: Any,
    produto_ids: set[int],
    *,
    max_paginas: int = 3,
) -> dict[int, dict[str, Any]]:
    """Índice produtoCodigo → linha PRODUTO_EMPRESA (preço A e custo)."""
    if not produto_ids:
        return {}
    empresa_map: dict[int, dict[str, Any]] = {}
    faltam = set(produto_ids)
    for pagina in range(max_paginas):
        if not faltam:
            break
        try:
            raw = webposto_client.produtos.listar_empresa(
                pagina=pagina,
                tamanho_pagina=200,
            )
        except Exception:
            break
        rows = _rows_from_raw(raw)
        if not rows:
            break
        for row in rows:
            cod = row.get("produtoCodigo") or row.get("codigo")
            if cod is None:
                continue
            pid = int(cod)
            if pid in faltam:
                empresa_map[pid] = row
                faltam.discard(pid)
        if len(rows) < 200:
            break
    return empresa_map


def _enriquecer_precos_empresa(
    webposto_client: Any,
    produtos: list[WebPostoProdutoSchema],
    raw_rows: list[dict[str, Any]],
) -> list[WebPostoProdutoSchema]:
    """Cruza PRODUTO + PRODUTO_EMPRESA (preços reais vêm da empresa)."""
    if not produtos:
        return produtos
    rows_by_id: dict[int, dict[str, Any]] = {}
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        cod = row.get("produtoCodigo") or row.get("codigo")
        if cod is not None:
            rows_by_id[int(cod)] = row

    from concurrent.futures import ThreadPoolExecutor

    empresa_map = _carregar_mapa_empresa(webposto_client, {p.id for p in produtos})
    
    # Identificar quais produtos não estão no mapa de empresa e buscar em paralelo
    produtos_faltantes = [p for p in produtos if p.id not in empresa_map]
    if produtos_faltantes:
        with ThreadPoolExecutor(max_workers=min(15, len(produtos_faltantes))) as executor:
            futuros = {
                p.id: executor.submit(_buscar_linha_empresa, webposto_client, p.id)
                for p in produtos_faltantes
            }
            for pid, futuro in futuros.items():
                try:
                    res = futuro.result()
                    if res:
                        empresa_map[pid] = res
                except Exception:
                    pass

    enriquecidos: list[WebPostoProdutoSchema] = []
    for p in produtos:
        row = rows_by_id.get(p.id) or {"produtoCodigo": p.id, "nome": p.descricao}
        emp = empresa_map.get(p.id)
        enriquecidos.append(map_raw_produto(row, empresa_row=emp))
    return enriquecidos


def _filtrar_tipo_produto(
    produtos: list[WebPostoProdutoSchema],
    tipo_produto: Optional[str],
) -> list[WebPostoProdutoSchema]:
    if not tipo_produto or tipo_produto.lower() == "todos":
        return produtos
    alvo = tipo_produto.strip().upper()
    if alvo == "COMBUSTIVEL":
        return [p for p in produtos if p.combustivel]
    out: list[WebPostoProdutoSchema] = []
    for p in produtos:
        tp = (p.tipo_produto or ("C" if p.combustivel else "P")).upper()
        if tp == alvo:
            out.append(p)
    return out


def _filtrar_subgrupos(
    produtos: list[WebPostoProdutoSchema],
    subgrupos: Optional[list[int]],
) -> list[WebPostoProdutoSchema]:
    if not subgrupos:
        return produtos
    alvo = {int(s) for s in subgrupos}
    return [
        p
        for p in produtos
        if any(
            sg in alvo
            for sg in (p.sub_grupo_1_codigo, p.sub_grupo_2_codigo, p.sub_grupo_3_codigo)
            if sg is not None
        )
    ]


def _filtrar_subgrupo(
    produtos: list[WebPostoProdutoSchema],
    subgrupo: Optional[int],
) -> list[WebPostoProdutoSchema]:
    if subgrupo is None:
        return produtos
    return _filtrar_subgrupos(produtos, [subgrupo])


def _filtrar_situacao(
    produtos: list[WebPostoProdutoSchema],
    situacao: SituacaoProduto,
) -> list[WebPostoProdutoSchema]:
    if situacao == "todos":
        return produtos
    if situacao == "ativos":
        return [p for p in produtos if p.ativo]
    return [p for p in produtos if not p.ativo]


def parse_produto_response(
    raw: Any,
    pagina: int,
    limite: int,
) -> tuple[list[dict], int]:
    """Extrai lista e total a partir do JSON da integração."""
    if isinstance(raw, list):
        return raw, len(raw)
    if not isinstance(raw, dict):
        return [], 0
    rows = raw.get("resultados") or raw.get("data") or raw.get("items") or []
    if not isinstance(rows, list):
        rows = []
    total = raw.get("total") or raw.get("totalRegistros") or raw.get("totalElements")
    if total is None:
        total = len(rows)
    return rows, int(total)


async def fetch_produtos_catalog(
    webposto_client: Any,
    pagina: int = 1,
    limite: int = 50,
    descricao: Optional[str] = None,
    grupo: Optional[int] = None,
    grupos: Optional[list[int]] = None,
    situacao: SituacaoProduto = "todos",
    tipo_produto: Optional[str] = None,
    subgrupo: Optional[int] = None,
    subgrupos: Optional[list[int]] = None,
) -> PaginatedProdutosResponse:
    pagina_idx = max(0, pagina - 1)
    grupo_unico = grupo
    if grupo_unico is None and grupos and len(grupos) == 1:
        grupo_unico = grupos[0]

    ativo_api: Optional[bool] = None
    if situacao == "ativos":
        ativo_api = True
    elif situacao == "inativos":
        ativo_api = False

    emp_cod: Optional[int] = None
    if hasattr(webposto_client, "_config") and getattr(webposto_client._config, "empresa_codigo", None) is not None:
        emp_cod = webposto_client._config.empresa_codigo
    else:
        try:
            from src.application.usecases.fetch_unidade_webposto import fetch_unidade_webposto
            unidade = await fetch_unidade_webposto(webposto_client, chave=getattr(webposto_client._config, "chave", ""))
            if unidade and unidade.empresa_codigo is not None:
                emp_cod = unidade.empresa_codigo
                if hasattr(webposto_client, "_config"):
                    webposto_client._config.empresa_codigo = emp_cod
        except Exception:
            pass

    import asyncio

    raw = await asyncio.to_thread(
        webposto_client.produtos.listar,
        codigo=None,
        nome=descricao,
        grupo_codigo=grupo_unico if not (grupos and len(grupos) > 1) else None,
        ativo=ativo_api,
        pagina=pagina_idx,
        tamanho_pagina=min(max(limite, 1), 200),
        empresa_codigo=emp_cod,
    )
    rows, total = parse_produto_response(raw, pagina, limite)

    produtos = [map_raw_produto(r) for r in rows if isinstance(r, dict)]

    if grupos:
        gs = {int(g) for g in grupos}
        produtos = [p for p in produtos if p.codigo_grupo in gs]
    elif grupo is not None:
        produtos = [p for p in produtos if p.codigo_grupo == grupo]

    produtos = _filtrar_situacao(produtos, situacao)
    produtos = _filtrar_tipo_produto(produtos, tipo_produto)
    sg_ids = subgrupos or ([subgrupo] if subgrupo is not None else None)
    produtos = _filtrar_subgrupos(produtos, sg_ids)

    if len(produtos) > limite:
        produtos = produtos[:limite]
        rows = rows[:limite]

    if produtos:
        produtos = await asyncio.to_thread(
            _enriquecer_precos_empresa, webposto_client, produtos, rows
        )
        produtos = _filtrar_situacao(produtos, situacao)
        produtos = _filtrar_tipo_produto(produtos, tipo_produto)
        produtos = _filtrar_subgrupos(produtos, sg_ids)

    total_filtrado = (
        len(produtos)
        if (grupos and len(grupos) > 1)
        or situacao != "todos"
        or tipo_produto
        or subgrupo is not None
        or subgrupos
        else total
    )
    total_paginas = max(1, (total_filtrado + limite - 1) // limite) if limite else 1

    return PaginatedProdutosResponse(
        pagina_atual=pagina,
        total_paginas=total_paginas,
        total_registros=total_filtrado,
        produtos=produtos,
        fonte="webposto_integracao",
    )


async def fetch_produtos_catalog_completo(
    webposto_client: Any,
    *,
    descricao: Optional[str] = None,
    grupo: Optional[int] = None,
    grupos: Optional[list[int]] = None,
    situacao: SituacaoProduto = "todos",
    tipo_produto: Optional[str] = None,
    subgrupo: Optional[int] = None,
    subgrupos: Optional[list[int]] = None,
    max_paginas: int = 150,
    tamanho_pagina: int = 200,
) -> PaginatedProdutosResponse:
    """
    Varre todas as páginas do catálogo e devolve produtos únicos por código (id).
    """
    vistos: dict[int, WebPostoProdutoSchema] = {}
    pagina = 1
    total_paginas_api = 1
    limite = min(max(tamanho_pagina, 1), 200)

    while pagina <= max(1, max_paginas):
        lote = await fetch_produtos_catalog(
            webposto_client,
            pagina=pagina,
            limite=limite,
            descricao=descricao,
            grupo=grupo,
            grupos=grupos,
            situacao=situacao,
            tipo_produto=tipo_produto,
            subgrupo=subgrupo,
            subgrupos=subgrupos,
        )
        total_paginas_api = max(total_paginas_api, lote.total_paginas)
        for prod in lote.produtos:
            if prod.id not in vistos:
                vistos[prod.id] = prod
        if pagina >= lote.total_paginas or not lote.produtos:
            break
        pagina += 1

    produtos = sorted(
        vistos.values(),
        key=lambda p: (p.descricao or "").lower(),
    )
    return PaginatedProdutosResponse(
        pagina_atual=1,
        total_paginas=1,
        total_registros=len(produtos),
        produtos=produtos,
        fonte="webposto_integracao",
    )
