"""Validação end-to-end (dados reais): WebPosto (venda+VFP) x extrato OFX real, 01-10/07/2026.

Não commitar: usa arquivos OFX reais do usuário (fora do repo, em Downloads) e credenciais reais
da API WebPosto (via WebPostoClient() / variáveis de ambiente). Executar manualmente via
``python scripts/validate_card_bank_reconciliation.py``.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.domain.reconciliation.ofx_parser import parse_ofx_file
from src.gateway.webposto_client import WebPostoClient
from src.services.bank_reconciliation.card_bank_matching_service import (
    compare_daily_card_settlements_with_lag,
    match_card_settlements,
)

# REDE deposita os creditos da pista em D+1 util (confirmado pelo usuario); Cielo (conveniencia)
# ainda nao teve o prazo de liquidacao confirmado -- mantido D0 (mesmo dia) por padrao.
ACQUIRER_LAG_BUSINESS_DAYS = {"REDE": 1}
from src.services.bank_reconciliation.card_sale_event_builder import (
    build_administradora_lookup,
    build_card_sale_events,
    build_cost_center_lookup,
)
from src.services.network_financial_overview_service import NetworkFinancialOverviewService
from src.services.webposto_cursor_paginator import WebPostoCursorPaginator

DATA_INICIAL = "2026-07-01"
DATA_FINAL = "2026-07-10"
DOWNLOADS = Path.home() / "Downloads"

COMPANIES = [
    {"nome": "Casa Caiada", "empresaCodigo": 5555, "formato": "PAGBANK", "ofx": DOWNLOADS / "PagBankCasaCaiadaAte10Julhjo.ofx"},
    {"nome": "Posto Doze Filial II", "empresaCodigo": 74014, "formato": "PAGBANK", "ofx": DOWNLOADS / "PagBankDozeFilialAte10Julho.ofx"},
    {"nome": "Posto Vip", "empresaCodigo": 11495, "formato": "ITAU", "ofx": DOWNLOADS / "Vip_Itau01a10Julho.ofx"},
]


async def _fetch_venda_e_vfp(client: WebPostoClient, empresa_codigo: int) -> tuple[list[dict], list[dict]]:
    paginator = WebPostoCursorPaginator(client)
    params = {"dataInicial": DATA_INICIAL, "dataFinal": DATA_FINAL, "empresaCodigo": empresa_codigo}

    # NAO usar collect(primary, fallback) com fallback por-pagina: _call_with_fallback so cai pro
    # fallback em erro, nao quando a resposta e' sucesso-porem-vazia (caso real de
    # venda_forma_pagamento_rede aqui). Tenta o endpoint base inteiro primeiro; so tenta o _rede
    # se o base vier totalmente vazio (mesmo padrao de CashReconciliationService._fetch_vfp).
    venda_resp = await paginator.collect("venda", "venda", params, cursor_field="vendaCodigo")
    if not venda_resp.success:
        # 500 esporadico observado em producao durante paginacao longa -- 1 retry basta.
        print(f"  [venda] erro (retry 1x): {venda_resp.error}")
        venda_resp = await paginator.collect("venda", "venda", params, cursor_field="vendaCodigo")
    if not venda_resp.success:
        print(f"  [venda] erro definitivo: {venda_resp.error}")
        venda_rows = []
    else:
        venda_rows = NetworkFinancialOverviewService._rows(venda_resp.data)

    vfp_resp = await paginator.collect("venda_forma_pagamento", "venda_forma_pagamento", params)
    vfp_rows = NetworkFinancialOverviewService._rows(vfp_resp.data) if vfp_resp.success else []
    if not vfp_resp.success:
        print(f"  [venda_forma_pagamento] erro: {vfp_resp.error}")
    if not vfp_rows:
        vfp_resp = await paginator.collect("venda_forma_pagamento_rede", "venda_forma_pagamento_rede", params)
        vfp_rows = NetworkFinancialOverviewService._rows(vfp_resp.data) if vfp_resp.success else []
        if not vfp_resp.success:
            print(f"  [venda_forma_pagamento_rede] erro: {vfp_resp.error}")

    return venda_rows, vfp_rows


async def _fetch_administradora_lookup(client: WebPostoClient, empresa_codigo: int) -> dict:
    paginator = WebPostoCursorPaginator(client)
    params = {"dataInicial": DATA_INICIAL, "dataFinal": DATA_FINAL, "empresaCodigo": empresa_codigo}
    resp = await paginator.collect("administradora_rede", "administradora_rede", params, cursor_field="codigo")
    rows = NetworkFinancialOverviewService._rows(resp.data) if resp.success else []
    if not resp.success:
        print(f"  [administradora_rede] erro: {resp.error}")
    return build_administradora_lookup(rows)


async def _fetch_cost_center_lookup(client: WebPostoClient, empresa_codigo: int) -> dict:
    """Centro de custo real (PISTA/LOJA) por venda, via /INTEGRACAO/CARTAO (achado 2026-07-21) --
    substitui a antiga tentativa de inferir isso pelo sufixo do administradoraCodigo."""
    paginator = WebPostoCursorPaginator(client)
    params = {"dataInicial": DATA_INICIAL, "dataFinal": DATA_FINAL, "empresaCodigo": empresa_codigo}
    resp = await paginator.collect("cartao", "cartao", params, cursor_field="codigo")
    rows = NetworkFinancialOverviewService._rows(resp.data) if resp.success else []
    if not resp.success:
        print(f"  [cartao] erro: {resp.error}")
    return build_cost_center_lookup(rows)


async def main() -> None:
    client = WebPostoClient()

    for company in COMPANIES:
        print(f"\n{'=' * 70}\n{company['nome']} (empresaCodigo={company['empresaCodigo']}, formato={company['formato']})\n{'=' * 70}")

        if not company["ofx"].exists():
            print(f"  OFX não encontrado: {company['ofx']}")
            continue

        statement = parse_ofx_file(str(company["ofx"]))
        print(f"  Extrato: {len(statement.transactions)} lançamentos ({statement.periodStart} a {statement.periodEnd})")

        venda_rows, vfp_rows = await _fetch_venda_e_vfp(client, company["empresaCodigo"])
        print(f"  WebPosto: {len(venda_rows)} vendas, {len(vfp_rows)} linhas de forma de pagamento")

        administradora_lookup = await _fetch_administradora_lookup(client, company["empresaCodigo"])
        print(f"  Administradoras resolvidas: {len(administradora_lookup)}")

        cost_center_lookup = await _fetch_cost_center_lookup(client, company["empresaCodigo"])
        print(f"  Centro de custo resolvido (vendas com PISTA/LOJA real via /INTEGRACAO/CARTAO): {len(cost_center_lookup)}")

        sale_events = build_card_sale_events(venda_rows, vfp_rows, administradora_lookup, cost_center_lookup)
        print(f"  CardSaleEvent construídos: {len(sale_events)}")

        if sale_events:
            from collections import Counter
            cc_dist = Counter(e.costCenter or "DESCONHECIDO" for e in sale_events)
            print(f"  Distribuição por centro de custo: {dict(cc_dist)}")

        if not sale_events:
            print("  Sem eventos de venda no cartão para comparar — pulando matching.")
            continue

        if company["formato"] == "PAGBANK":
            result = match_card_settlements(sale_events, statement.transactions)
            print(f"  Casados: {len(result.matched)} (R$ {result.matchedSalesTotal:.2f} venda / R$ {result.matchedBankTotal:.2f} banco)")
            print(f"  Vendas sem crédito bancário: {len(result.unmatchedSales)} (R$ {result.unmatchedSalesTotal:.2f})")
            print(f"  Créditos bancários sem venda: {len(result.unmatchedBankTransactions)} (R$ {result.unmatchedBankTotal:.2f})")
        else:
            comparisons = compare_daily_card_settlements_with_lag(
                sale_events, statement.transactions, acquirer_lag_business_days=ACQUIRER_LAG_BUSINESS_DAYS
            )
            divergent = [c for c in comparisons if c.bankTotal is None or abs(c.delta) > 0.05]
            print(f"  Baldes (dia+bandeira+método, já com D+1 útil da REDE aplicado): {len(comparisons)}, divergentes: {len(divergent)}")
            for c in divergent[:30]:
                bank_str = f"R$ {c.bankTotal:.2f}" if c.bankTotal is not None else "sem lançamento"
                print(f"    {c.settlementDate} {c.brand}/{c.method}: venda=R$ {c.salesTotal:.2f} banco={bank_str}")


if __name__ == "__main__":
    asyncio.run(main())
