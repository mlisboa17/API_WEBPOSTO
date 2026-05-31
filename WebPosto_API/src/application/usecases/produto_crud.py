"""
CRUD de produtos via API Quality (INTEGRACAO/PRODUTO, INCLUIR_PRODUTO, ALTERAR_PRODUTO).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from src.application.usecases.fetch_produtos_catalog import (
    _rows_from_raw,
    map_raw_produto,
    parse_produto_response,
)
from src.domain.catalog.produto_crud_schema import (
    ProdutoCreateRequest,
    ProdutoCrudResponse,
    ProdutoUpdateRequest,
)
from src.domain.catalog.product_schema import WebPostoProdutoSchema


def _float(v: Decimal | float | int) -> float:
    return float(v)


def _body_from_create(data: ProdutoCreateRequest) -> dict[str, Any]:
    desc_res = (data.descricao_resumida or data.descricao[:40]).strip()
    body: dict[str, Any] = {
        "descricao": data.descricao.strip(),
        "descricaoResumida": desc_res,
        "tipoProduto": data.tipo_produto,
        "grupoCodigo": data.grupo_codigo,
        "unidadeCompra": data.unidade_compra,
        "unidadeVenda": data.unidade_venda,
        "precoCusto": _float(data.preco_custo),
        "precoCompra": _float(data.preco_compra),
        "precoVenda": _float(data.preco_venda),
        "iat": data.iat,
        "ippt": data.ippt,
        "codigoNcm": data.codigo_ncm,
        "ativo": data.ativo,
        "permiteVendaEstoqueNegativo": data.permite_venda_estoque_negativo,
        "produtoVendeFracionado": data.produto_vende_fracionado,
        "utilizaCodigoBarras": data.utiliza_codigo_barras,
        "utilizaBalanca": False,
    }
    if data.codigo_externo:
        body["codigoExterno"] = data.codigo_externo
    if data.codigo_barras:
        body["codigoBarras"] = data.codigo_barras
    if data.codigo_cest:
        body["codigoCest"] = data.codigo_cest
    if data.tributacao_monofasica is not None:
        body["tributacaoMonofasica"] = data.tributacao_monofasica
    if data.tributo_icms:
        body["tributoIcms"] = data.tributo_icms.model_dump(by_alias=True)
    else:
        body["tributoIcms"] = {
            "percentualIcmsSaida": 0,
            "cstSaida": "060",
            "percentualIcmsEntrada": 0,
            "cstEntrada": "060",
        }
    if data.tributo_pis_cofins:
        body["tributoPisCofins"] = data.tributo_pis_cofins.model_dump(by_alias=True)
    return body


def _body_from_update(data: ProdutoUpdateRequest) -> dict[str, Any]:
    body: dict[str, Any] = {}
    fields = [
        ("descricao", "descricao"),
        ("descricao_resumida", "descricaoResumida"),
        ("tipo_produto", "tipoProduto"),
        ("grupo_codigo", "grupoCodigo"),
        ("unidade_compra", "unidadeCompra"),
        ("unidade_venda", "unidadeVenda"),
        ("codigo_barras", "codigoBarras"),
        ("codigo_ncm", "codigoNcm"),
        ("codigo_cest", "codigoCest"),
        ("ativo", "ativo"),
    ]
    for attr, key in fields:
        val = getattr(data, attr)
        if val is not None:
            body[key] = val
    for price_attr, key in [
        ("preco_custo", "precoCusto"),
        ("preco_compra", "precoCompra"),
        ("preco_venda", "precoVenda"),
    ]:
        val = getattr(data, price_attr)
        if val is not None:
            body[key] = _float(val)
    if data.tributo_icms:
        body["tributoIcms"] = data.tributo_icms.model_dump(by_alias=True)
    if data.tributo_pis_cofins:
        body["tributoPisCofins"] = data.tributo_pis_cofins.model_dump(by_alias=True)
    return body


async def obter_produto(
    webposto_client: Any,
    produto_id: int,
) -> Optional[WebPostoProdutoSchema]:
    from src.application.usecases.fetch_produtos_catalog import (
        _buscar_linha_empresa,
        _buscar_linha_produto,
        map_raw_produto,
    )

    row = _buscar_linha_produto(webposto_client, produto_id)
    emp = _buscar_linha_empresa(webposto_client, produto_id)
    if not row and not emp:
        return None
    return map_raw_produto(row, empresa_row=emp)


async def criar_produto(
    webposto_client: Any,
    data: ProdutoCreateRequest,
) -> ProdutoCrudResponse:
    body = _body_from_create(data)
    endpoint = "/INTEGRACAO/INCLUIR_PRODUTO"
    try:
        raw = webposto_client.produtos.incluir(body)
    except Exception:
        endpoint = "/INTEGRACAO/PRODUTO"
        raw = webposto_client.produtos.criar(body)

    produto = None
    if isinstance(raw, dict):
        cod = raw.get("produtoCodigo") or raw.get("codigo") or raw.get("id")
        if cod is not None:
            produto = await obter_produto(webposto_client, int(cod))
    return ProdutoCrudResponse(
        ok=True,
        produto=produto,
        raw=raw,
        mensagem="Produto cadastrado na WebPosto",
        endpoint=endpoint,
    )


async def atualizar_produto(
    webposto_client: Any,
    produto_id: int,
    data: ProdutoUpdateRequest,
) -> ProdutoCrudResponse:
    body = _body_from_update(data)
    if not body:
        raise ValueError("Nenhum campo para atualizar")
    webposto_client.produtos.atualizar(produto_id, body)
    produto = await obter_produto(webposto_client, produto_id)
    return ProdutoCrudResponse(
        ok=True,
        produto=produto,
        mensagem="Produto atualizado",
        endpoint=f"/INTEGRACAO/ALTERAR_PRODUTO/{produto_id}",
    )
