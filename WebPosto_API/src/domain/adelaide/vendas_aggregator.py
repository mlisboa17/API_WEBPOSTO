"""
Agrega itens de VENDA (PDV/loja) para análise Adelaide — complementa ABASTECIMENTO.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from src.domain.adelaide.fuel_catalog import rotulo_combustivel
from src.domain.adelaide.tax_profile import (
    ExecutiveKpiSummary,
    AdelaideTaxProfile,
    _d,
    agregar_abastecimentos,
)


def _codigo_item(item: dict[str, Any]) -> str:
    for k in (
        "codigoProduto",
        "produtoCodigo",
        "codigo",
        "idProduto",
    ):
        v = item.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def _nome_item(item: dict[str, Any], codigo: str) -> str:
    for k in (
        "descricaoProduto",
        "nomeProduto",
        "produtoNome",
        "descricao",
        "nome",
    ):
        if item.get(k):
            return rotulo_combustivel(codigo, str(item[k]))
    return rotulo_combustivel(codigo)


def _valor_item(item: dict[str, Any]) -> Decimal:
    for k in ("valorTotal", "valor", "valorLiquido", "total"):
        if item.get(k) is not None:
            v = _d(item[k])
            if v > 0:
                return v
    q = _d(item.get("quantidade") or item.get("qtd") or 0)
    vu = _d(item.get("valorUnitario") or item.get("preco") or 0)
    if q > 0 and vu > 0:
        return (q * vu).quantize(Decimal("0.01"))
    return Decimal("0")


def extrair_linhas_venda(
    vendas: list[dict[str, Any]],
    *,
    codigos_produto: Optional[list[str]] = None,
) -> list[dict[str, Any]]:
    """Converte cupons VENDA em linhas no formato compatível com agregação Adelaide."""
    permitidos: Optional[set[str]] = None
    if codigos_produto is not None:
        permitidos = {str(c).strip() for c in codigos_produto if str(c).strip()}

    linhas: list[dict[str, Any]] = []
    for venda in vendas:
        itens = venda.get("itens") or venda.get("items") or []
        if not isinstance(itens, list) or not itens:
            continue
        for item in itens:
            if not isinstance(item, dict):
                continue
            cod = _codigo_item(item)
            if not cod:
                continue
            if permitidos is not None and cod not in permitidos:
                continue
            valor = _valor_item(item)
            if valor <= 0:
                continue
            linhas.append(
                {
                    "codigoProduto": cod,
                    "descricaoProduto": _nome_item(item, cod),
                    "quantidade": item.get("quantidade") or item.get("qtd") or 0,
                    "valorTotal": float(valor),
                    "origem": "VENDA",
                }
            )
    return linhas


def mesclar_summaries_adelaide(
    abast: ExecutiveKpiSummary,
    vendas: ExecutiveKpiSummary,
) -> ExecutiveKpiSummary:
    """Soma dois resumos Adelaide (abastecimento + PDV)."""
    buckets: dict[str, AdelaideTaxProfile] = {}
    for p in abast.produtos + vendas.produtos:
        if p.codigo_produto not in buckets:
            buckets[p.codigo_produto] = p
        else:
            cur = buckets[p.codigo_produto]
            buckets[p.codigo_produto] = cur.model_copy(
                update={
                    "litros": cur.litros + p.litros,
                    "faturamento_bruto": cur.faturamento_bruto + p.faturamento_bruto,
                }
            )
    produtos = list(buckets.values())
    return ExecutiveKpiSummary(
        periodo=abast.periodo,
        faturamento_total=sum((p.faturamento_bruto for p in produtos), Decimal("0")),
        custo_total=sum((p.custo_total for p in produtos), Decimal("0")),
        pis_cofins_total=sum((p.pis_cofins for p in produtos), Decimal("0")),
        taxas_cartao_total=sum((p.taxa_cartao for p in produtos), Decimal("0")),
        margem_liquida_total=sum((p.margem_liquida for p in produtos), Decimal("0")),
        litros_total=sum((p.litros for p in produtos), Decimal("0")),
        despesas_caixa=abast.despesas_caixa,
        produtos=produtos,
        fallback=abast.fallback or vendas.fallback,
        mensagem=abast.mensagem or vendas.mensagem,
    )
