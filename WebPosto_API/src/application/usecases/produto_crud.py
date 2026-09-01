"""
CRUD de produtos via API Quality (INTEGRACAO/PRODUTO, INCLUIR_PRODUTO, ALTERAR_PRODUTO).

Regra de centro de custo para venda aplicada em inclusão/alteração.
Troca exclusiva de preço → POST /INTEGRACAO/V1/TROCA_PRECOS_PRODUTOS.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from src.application.usecases.fetch_produtos_catalog import (
    map_raw_produto,
)
from src.domain.catalog.produto_crud_schema import (
    ProdutoCreateRequest,
    ProdutoCrudResponse,
    ProdutoPriceOnlyRequest,
    ProdutoUpdateRequest,
)
from src.domain.catalog.product_schema import WebPostoProdutoSchema
from src.services.product_cadastro_write_service import (
    ProductCadastroWriteService,
    ProductWriteBlocked,
)


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


def _patch_from_update(data: ProdutoUpdateRequest) -> dict[str, Any]:
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


def _result_to_response(result) -> ProdutoCrudResponse:
    produto = None
    if result.after and result.produto_codigo:
        # map minimal schema if possible
        try:
            produto = WebPostoProdutoSchema(
                id=int(result.produto_codigo),
                descricao=str(result.after.get("nome") or ""),
                preco_venda=result.after.get("precoA") or 0,
                preco_custo=result.after.get("custo") or 0,
                ativo=bool(result.after.get("ativo") if result.after.get("ativo") is not None else True),
                codigo_barra=result.after.get("ean"),
                ncm=result.after.get("ncm"),
                cest=result.after.get("cest"),
                tipo_produto=result.after.get("tipoProduto"),
                combustivel=False,
            )
        except Exception:
            produto = None
    cc = result.center_cost.codigo if result.center_cost else None
    return ProdutoCrudResponse(
        ok=result.ok,
        produto=produto,
        raw={
            "baseline": result.baseline,
            "after": result.after,
            "verification": result.verification,
            "centerCostGate": result.center_cost.gate if result.center_cost else None,
        },
        mensagem=result.mensagem,
        endpoint=result.endpoint,
        gate=result.gate,
        empresa_codigo=result.empresa_codigo,
        centro_custo_codigo=cc,
        verification=result.verification,
    )


async def obter_produto(
    webposto_client: Any,
    produto_id: int,
) -> Optional[WebPostoProdutoSchema]:
    from src.application.usecases.fetch_produtos_catalog import (
        _buscar_linha_empresa,
        _buscar_linha_produto,
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
    svc = ProductCadastroWriteService(webposto_client)
    body = _body_from_create(data)
    try:
        result = svc.create_with_center_cost(
            empresa_codigo=data.empresa_codigo,
            body=body,
        )
    except ProductWriteBlocked as exc:
        return ProdutoCrudResponse(
            ok=False,
            mensagem=str(exc),
            gate=exc.gate,
            empresa_codigo=data.empresa_codigo,
        )
    return _result_to_response(result)


async def atualizar_produto(
    webposto_client: Any,
    produto_id: int,
    data: ProdutoUpdateRequest,
) -> ProdutoCrudResponse:
    patch = _patch_from_update(data)
    if not patch:
        raise ValueError("Nenhum campo para atualizar")
    svc = ProductCadastroWriteService(webposto_client)
    try:
        result = svc.update_cadastro_with_center_cost(
            empresa_codigo=data.empresa_codigo,
            produto_codigo=produto_id,
            patch=patch,
        )
    except ProductWriteBlocked as exc:
        return ProdutoCrudResponse(
            ok=False,
            mensagem=str(exc),
            gate=exc.gate,
            empresa_codigo=data.empresa_codigo,
        )
    return _result_to_response(result)


async def alterar_preco_oficial(
    webposto_client: Any,
    data: ProdutoPriceOnlyRequest,
) -> ProdutoCrudResponse:
    """Troca exclusiva de preço — endpoint oficial V1 (sem centroCusto no body)."""
    svc = ProductCadastroWriteService(webposto_client)
    try:
        result = svc.change_price_only(
            empresa_codigo=data.empresa_codigo,
            produto_codigo=data.produto_codigo,
            price_level=data.price_level,
            novo_preco=float(data.novo_preco),
            hora=data.hora,
            tipo_alteracao=data.tipo_alteracao,
        )
    except ProductWriteBlocked as exc:
        return ProdutoCrudResponse(
            ok=False,
            mensagem=str(exc),
            gate=exc.gate,
            empresa_codigo=data.empresa_codigo,
        )
    return _result_to_response(result)
