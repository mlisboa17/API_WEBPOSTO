"""D02+ — Bridge: linhas reais WebPosto (venda + venda_forma_pagamento) -> CardSaleEvent.

Achado em dados reais (2026-07-20): ``nomeFormaPagamento`` do VFP é genérico ("CARTAO POS",
"CARTAO") e NÃO distingue bandeira/método — essa informação mora em ``administradoraCodigo``,
resolvido via lookup no endpoint CONSULTAR_ADMINISTRADORA_REDE (``descricao`` traz a bandeira,
``tipo`` traz "Crédito"/"Débito", às vezes com mojibake do servidor ex. "CrÚdito"/"DÚbito" — por
isso a checagem usa só o prefixo C/D, robusto a esse problema de encoding).

O extrato bancário guarda método em português (CREDITO/DEBITO, ver ofx_parser.py), então todo
método aqui é normalizado para o mesmo vocabulário para permitir casamento por igualdade exata em
``match_card_settlements``/``compare_daily_card_settlements``.

Administradoras "PREMMIA" (carteira digital da Vibra) ficam de fora: elas liquidam como Pix
recebido no extrato (ver ``extract_premmia_settlements``), não como MEMO de cartão — incluir essas
linhas aqui só geraria falso "venda sem crédito bancário".

Granularidade de data (sem hora) é suficiente: o casamento usa janela de dias
(``date_window_days``), não hora exata.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from src.domain.reconciliation.card_normalization import card_rows_from_vfp, normalize_card_row
from src.domain.reconciliation.payment_normalization import infer_card_brand
from src.services.bank_reconciliation.card_bank_matching_service import CardSaleEvent

_METHOD_PT = {
    "DEBIT": "DEBITO",
    "CREDIT": "CREDITO",
}


def build_administradora_lookup(administradora_rows: list[dict[str, Any]]) -> dict[Any, dict[str, str]]:
    """Mapeia administradoraCodigo -> {brand, method, descricao}, a partir de
    CONSULTAR_ADMINISTRADORA_REDE.

    ``tipo`` normalmente vem como "Crédito"/"Débito", mas o servidor às vezes devolve mojibake
    ("CrÚdito"/"DÚbito") — os dois primeiros caracteres (CR vs D) não são afetados, então a
    checagem usa apenas o prefixo.
    """
    lookup: dict[Any, dict[str, str]] = {}
    for row in administradora_rows:
        codigo = row.get("administradoraCodigo") or row.get("codigo")
        if codigo is None:
            continue
        descricao = str(row.get("descricao") or "")
        tipo = str(row.get("tipo") or "").upper()
        if tipo.startswith("CR"):
            method = "CREDITO"
        elif tipo.startswith("D"):
            method = "DEBITO"
        else:
            method = "UNKNOWN"
        lookup[codigo] = {"brand": infer_card_brand(descricao), "descricao": descricao.upper(), "method": method}
    return lookup


def _is_premmia(descricao: str) -> bool:
    return "PREMMIA" in descricao.upper()


def build_cost_center_lookup(cartao_rows: list[dict[str, Any]]) -> dict[Any, str]:
    """Mapeia vendaCodigo -> centroCustoDescricao ("PISTA"/"LOJA"), a partir do endpoint real
    /INTEGRACAO/CARTAO (achado em 2026-07-21, ver acquirer_fee_model.py e memoria do repo).

    Esse endpoint traz centro de custo REAL por transação de cartão -- substitui a tentativa
    anterior (descartada) de inferir pista/convêniência pelo sufixo do administradoraCodigo, que
    não era confiável entre bandeiras.
    """
    lookup: dict[Any, str] = {}
    for row in cartao_rows:
        venda_codigo = row.get("vendaCodigo")
        centro_custo = row.get("centroCustoDescricao")
        if venda_codigo is None or not centro_custo:
            continue
        lookup[venda_codigo] = str(centro_custo).upper()
    return lookup


def _venda_date_lookup(venda_rows: list[dict[str, Any]]) -> dict[Any, str]:
    """Mapeia vendaCodigo -> data (YYYY-MM-DD), mesma prioridade de campos usada em
    NetworkFinancialOverviewService.get_sales (data/dataEmissao/dataVenda/dataHora/dataMovimento)."""
    lookup: dict[Any, str] = {}
    for venda in venda_rows:
        venda_codigo = venda.get("vendaCodigo") or venda.get("codigo")
        if venda_codigo is None:
            continue
        data_venda = (
            venda.get("data")
            or venda.get("dataEmissao")
            or venda.get("dataVenda")
            or venda.get("dataHora")
            or venda.get("dataMovimento")
        )
        if not data_venda:
            continue
        lookup[venda_codigo] = str(data_venda)[:10]
    return lookup


def build_card_sale_events(
    venda_rows: list[dict[str, Any]],
    vfp_rows: list[dict[str, Any]],
    administradora_lookup: dict[Any, dict[str, str]] | None = None,
    cost_center_lookup: dict[Any, str] | None = None,
) -> list[CardSaleEvent]:
    """Constrói eventos de venda no cartão a partir de linhas reais VFP, herdando a data da
    venda-pai (join por vendaCodigo). Bandeira/método vêm preferencialmente do lookup de
    administradora (mais confiável) e caem para o rótulo bruto (``normalize_card_row``) quando a
    administradora não está no lookup. Linhas Premmia, sem venda-pai localizada ou com valor
    zero/negativo são descartadas.

    ``cost_center_lookup`` (opcional, ver ``build_cost_center_lookup``) preenche
    ``CardSaleEvent.costCenter`` ("PISTA"/"LOJA") com o dado real do endpoint /INTEGRACAO/CARTAO,
    quando disponível para a venda."""
    administradora_lookup = administradora_lookup or {}
    cost_center_lookup = cost_center_lookup or {}
    date_by_venda = _venda_date_lookup(venda_rows)
    events: list[CardSaleEvent] = []
    for row in card_rows_from_vfp(vfp_rows):
        venda_codigo = row.get("vendaCodigo")
        data_str = date_by_venda.get(venda_codigo)
        if not data_str:
            continue
        try:
            occurred_at = datetime.strptime(data_str, "%Y-%m-%d")
        except ValueError:
            continue

        administradora = administradora_lookup.get(row.get("administradoraCodigo"))
        if administradora and _is_premmia(administradora["descricao"]):
            continue

        card = normalize_card_row(row)
        # O banco liquida o valor LÍQUIDO (já descontada a taxa da adquirente/bandeira), não o
        # bruto da venda -- por isso usa-se expectedNet (bruto * (1 - taxaPercentual/100)) sempre
        # que a linha VFP trouxer taxaPercentual, caindo para o bruto só quando a taxa não veio.
        amount = card.expectedNet if card.expectedNet is not None else card.grossAmount
        if amount <= 0:
            continue

        if administradora:
            brand = administradora["brand"]
            method = administradora["method"]
        else:
            brand = card.normalizedBrand
            method = _METHOD_PT.get(card.normalizedMethod, card.normalizedMethod)

        reference_suffix = row.get("vendaFormaPagamentoCodigo") or row.get("codigo") or len(events)
        events.append(
            CardSaleEvent(
                reference=f"{venda_codigo}-{reference_suffix}",
                occurredAt=occurred_at,
                amount=amount,
                brand=brand,
                method=method,
                costCenter=cost_center_lookup.get(venda_codigo),
            )
        )
    return events
