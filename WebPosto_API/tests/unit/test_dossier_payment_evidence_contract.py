"""Contrato FR-01 para dossiê: não colapsar N cartões em 1 NSU no total misto.

Espelha a regra de `buildDossierPaymentEvidence` (export-fraud-legal-dossier.ts):
quando há settlementTrace.payments, cada cartão mantém seu amount/raw_nsu.
"""

from __future__ import annotations

from src.services.fueling_settlement_trace import (
    FuelingFact,
    SaleFact,
    build_fueling_settlement_trace,
)

NSU_A = "965ed3af-6dd0-47ab-8fd4-9ba1d24ca3a6"
NSU_B = "b94d9b39-1044-4d84-88a9-e2aaa0b52c20"


def _golden_trace():
    sale = SaleFact(sale_id=366670631, cupom="3974", total=408.73, employee_id=299254)
    fuelings = [
        FuelingFact(fueling_id=1, sale_id=366670631, amount=100.0),
        FuelingFact(fueling_id=2, sale_id=366670631, amount=268.73),
        FuelingFact(fueling_id=3, sale_id=366670631, amount=40.0),
    ]
    payments = [
        {"nomeFormaPagamento": "CARTAO POS", "valorPagamento": 100.0, "financeiroCodigo": 206519984},
        {"nomeFormaPagamento": "CARTAO POS", "valorPagamento": 268.73, "financeiroCodigo": 206519985},
        {"nomeFormaPagamento": "DINHEIRO", "valorPagamento": 40.0, "tipoFormaPagamento": "D"},
    ]
    cards = [
        {
            "cartaoCodigo": 206519984,
            "valor": 100.0,
            "nsu": NSU_A,
            "autorizacao": NSU_A,
            "nsuTef": None,
            "adiministradoraDescricao": "PREMMIA PIX",
        },
        {
            "cartaoCodigo": 206519985,
            "valor": 268.73,
            "nsu": NSU_B,
            "autorizacao": NSU_B,
            "nsuTef": None,
            "adiministradoraDescricao": "PREMMIA CREDITO",
        },
    ]
    return build_fueling_settlement_trace(
        sale=sale, fuelings=fuelings, payment_rows=payments, card_rows=cards
    )


def test_dossier_must_not_attribute_single_nsu_to_mixed_total():
    tr = _golden_trace()
    assert tr.payment_mode == "MIXED"
    assert len(tr.cards) == 2
    # Nenhum cartão individual cobre o total da venda
    assert all(c.amount != tr.reconciliation.sale_total for c in tr.cards)
    # Dois tokens distintos
    assert {c.raw_nsu for c in tr.cards} == {NSU_A, NSU_B}
    # Dinheiro sem cartão/NSU
    cash = next(p for p in tr.payments if p.is_cash)
    assert cash.card_id is None
    assert cash.amount == 40.0
    # UUID não é TEF clássico
    assert all(c.nsu_kind == "RAW_UUID_OR_TOKEN" for c in tr.cards)


def test_legacy_projection_fields_marked_deprecated_on_trace():
    tr = _golden_trace()
    assert tr.legacy_projection.cartaoNsu == "DEPRECATED_PROJECTION"
    assert tr.legacy_projection.valorTotalCartao == "DEPRECATED_PROJECTION"
