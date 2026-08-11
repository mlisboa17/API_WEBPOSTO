"""FR-01 — FuelingSettlementTrace unit tests (fatos; sem alteração de score)."""

from __future__ import annotations

from src.services.fraud_detection_engine import FraudDetectionEngine, _is_eletronico
from src.services.fraud_audit_settings_service import AuditFraudSettingsDTO
from src.services.fueling_settlement_trace import (
    FuelingFact,
    SaleFact,
    build_fueling_settlement_trace,
)
from src.services.webposto_pista_service import AbastecimentoRestV1


NSU_A = "965ed3af-6dd0-47ab-8fd4-9ba1d24ca3a6"
NSU_B = "b94d9b39-1044-4d84-88a9-e2aaa0b52c20"


def _settings() -> AuditFraudSettingsDTO:
    return AuditFraudSettingsDTO(
        empresa_id=0,
        tempo_retencao_critico_min=10,
        tempo_retencao_atencao_min=5,
        tempo_agrupamento_max_min=15,
        percentual_desconto_suspeito_pct=10.0,
        recorrencia_cpf_cartao_limite=3,
    )


def test_case_a_single_fueling_cash_explained():
    sale = SaleFact(sale_id=1, cupom="1", timestamp="2026-08-10T10:00:00", total=100.0, employee_id=1)
    fuelings = [
        FuelingFact(
            fueling_id=10,
            sale_id=1,
            venda_item_id=100,
            timestamp="2026-08-10T09:50:00",
            settlement_timestamp="2026-08-10T10:00:00",
            amount=100.0,
            employee_id=1,
        )
    ]
    payments = [
        {
            "nomeFormaPagamento": "DINHEIRO",
            "tipoFormaPagamento": "D",
            "valorPagamento": 100.0,
            "financeiroCodigo": None,
        }
    ]
    tr = build_fueling_settlement_trace(sale=sale, fuelings=fuelings, payment_rows=payments, card_rows=[])
    assert tr.trace_status == "EXPLAINED"
    assert len(tr.fuelings) == 1
    assert len(tr.payments) == 1
    assert len(tr.cards) == 0
    assert tr.payment_mode == "SINGLE_CASH"
    assert tr.reconciliation.fueling_to_sale_status == "EXACT"
    assert tr.reconciliation.sale_to_payment_status == "EXACT"


def test_case_b_golden_3_3_2():
    sale = SaleFact(
        sale_id=366670631,
        cupom="3974",
        timestamp="2026-08-10T18:16:11-03:00",
        total=408.73,
        employee_id=299254,
        employee_name="CAIO FERREIRA BONFIM",
        empresa_codigo=74014,
    )
    fuelings = [
        FuelingFact(
            fueling_id=391470186,
            sale_id=366670631,
            venda_item_id=765421860,
            timestamp="2026-08-10T17:41:10-03:00",
            settlement_timestamp="2026-08-10T18:16:11-03:00",
            amount=100.0,
            volume=14.599,
            employee_id=299254,
        ),
        FuelingFact(
            fueling_id=391470185,
            sale_id=366670631,
            venda_item_id=765421859,
            timestamp="2026-08-10T17:58:06-03:00",
            settlement_timestamp="2026-08-10T18:16:11-03:00",
            amount=268.73,
            volume=39.231,
            employee_id=299254,
        ),
        FuelingFact(
            fueling_id=391470184,
            sale_id=366670631,
            venda_item_id=765421858,
            timestamp="2026-08-10T18:02:55-03:00",
            settlement_timestamp="2026-08-10T18:16:11-03:00",
            amount=40.0,
            volume=8.351,
            employee_id=299254,
        ),
    ]
    payments = [
        {
            "nomeFormaPagamento": "CARTAO POS",
            "valorPagamento": 100.0,
            "financeiroCodigo": 206519984,
            "administradoraCodigo": 136957,
            "tipoFormaPagamento": "R",
        },
        {
            "nomeFormaPagamento": "CARTAO POS",
            "valorPagamento": 268.73,
            "financeiroCodigo": 206519985,
            "administradoraCodigo": 136956,
            "tipoFormaPagamento": "R",
        },
        {
            "nomeFormaPagamento": "DINHEIRO",
            "valorPagamento": 40.0,
            "financeiroCodigo": None,
            "tipoFormaPagamento": "D",
        },
    ]
    cards = [
        {
            "cartaoCodigo": 206519984,
            "vendaCodigo": 366670631,
            "valor": 100.0,
            "nsu": NSU_A,
            "autorizacao": NSU_A,
            "nsuTef": None,
            "adiministradoraDescricao": "PREMMIA PIX",
            "tipoInclusao": "PDV-TEF",
            "empresaCodigo": 74014,
        },
        {
            "cartaoCodigo": 206519985,
            "vendaCodigo": 366670631,
            "valor": 268.73,
            "nsu": NSU_B,
            "autorizacao": NSU_B,
            "nsuTef": None,
            "adiministradoraDescricao": "PREMMIA CREDITO",
            "tipoInclusao": "PDV-TEF",
            "empresaCodigo": 74014,
        },
    ]
    tr = build_fueling_settlement_trace(
        sale=sale, fuelings=fuelings, payment_rows=payments, card_rows=cards
    )
    assert len(tr.fuelings) == 3
    assert len(tr.payments) == 3
    assert len(tr.cards) == 2
    assert tr.reconciliation.fueling_total == 408.73
    assert tr.reconciliation.sale_total == 408.73
    assert tr.reconciliation.payment_total == 408.73
    assert tr.reconciliation.fueling_to_sale_status == "EXACT"
    assert tr.reconciliation.sale_to_payment_status == "EXACT"
    assert tr.trace_status == "EXPLAINED"
    assert tr.payment_mode == "MIXED"
    assert all(c.amount != 408.73 for c in tr.cards)
    assert {c.raw_nsu for c in tr.cards} == {NSU_A, NSU_B}
    # VFP→CARTAO via financeiroCodigo
    p100 = next(p for p in tr.payments if p.amount == 100.0)
    assert p100.card_id == 206519984
    p40 = next(p for p in tr.payments if p.amount == 40.0)
    assert p40.is_cash is True
    assert p40.card_id is None
    # retenções individuais ~35/18/13
    rets = [f.retention_minutes for f in tr.fuelings]
    assert rets == [35, 18, 13]
    assert tr.retention.max_retention_minutes == 35
    assert tr.retention.min_retention_minutes == 13


def test_case_c_three_fuelings_one_payment_allowed():
    sale = SaleFact(sale_id=2, total=300.0)
    fuelings = [
        FuelingFact(fueling_id=i, sale_id=2, amount=100.0, timestamp="2026-08-10T10:00:00", settlement_timestamp="2026-08-10T10:30:00")
        for i in (1, 2, 3)
    ]
    payments = [{"nomeFormaPagamento": "CARTAO POS", "valorPagamento": 300.0, "financeiroCodigo": 9}]
    cards = [{"cartaoCodigo": 9, "valor": 300.0, "nsu": "111", "nsuTef": "111"}]
    tr = build_fueling_settlement_trace(sale=sale, fuelings=fuelings, payment_rows=payments, card_rows=cards)
    assert len(tr.fuelings) == 3
    assert len(tr.payments) == 1
    assert tr.trace_status == "EXPLAINED"
    assert tr.payment_mode == "SINGLE_ELECTRONIC"


def test_case_d_unsettled():
    fuelings = [
        FuelingFact(fueling_id=1, amount=50.0, timestamp="2026-08-10T10:00:00", status="PENDENTE")
    ]
    tr = build_fueling_settlement_trace(sale=None, fuelings=fuelings, payment_rows=[], card_rows=[])
    assert tr.trace_status == "UNSETTLED"


def test_case_e_fueling_sale_mismatch():
    sale = SaleFact(sale_id=3, total=200.0)
    fuelings = [FuelingFact(fueling_id=1, sale_id=3, amount=100.0)]
    payments = [{"nomeFormaPagamento": "DINHEIRO", "valorPagamento": 200.0, "tipoFormaPagamento": "D"}]
    tr = build_fueling_settlement_trace(sale=sale, fuelings=fuelings, payment_rows=payments)
    assert tr.reconciliation.fueling_to_sale_status == "MISMATCH"
    assert tr.trace_status == "MISMATCH"


def test_case_f_sale_payment_mismatch():
    sale = SaleFact(sale_id=4, total=100.0)
    fuelings = [FuelingFact(fueling_id=1, sale_id=4, amount=100.0)]
    payments = [{"nomeFormaPagamento": "DINHEIRO", "valorPagamento": 90.0, "tipoFormaPagamento": "D"}]
    tr = build_fueling_settlement_trace(sale=sale, fuelings=fuelings, payment_rows=payments)
    assert tr.reconciliation.sale_to_payment_status == "MISMATCH"
    assert tr.trace_status == "MISMATCH"


def test_case_g_two_cards_two_nsus():
    sale = SaleFact(sale_id=5, total=150.0)
    fuelings = [FuelingFact(fueling_id=1, sale_id=5, amount=150.0)]
    payments = [
        {"nomeFormaPagamento": "CARTAO POS", "valorPagamento": 50.0, "financeiroCodigo": 1},
        {"nomeFormaPagamento": "CARTAO POS", "valorPagamento": 100.0, "financeiroCodigo": 2},
    ]
    cards = [
        {"cartaoCodigo": 1, "valor": 50.0, "nsu": NSU_A, "nsuTef": None},
        {"cartaoCodigo": 2, "valor": 100.0, "nsu": NSU_B, "nsuTef": None},
    ]
    tr = build_fueling_settlement_trace(sale=sale, fuelings=fuelings, payment_rows=payments, card_rows=cards)
    assert len(tr.cards) == 2
    assert {c.raw_nsu for c in tr.cards} == {NSU_A, NSU_B}
    assert all(c.nsu_kind == "RAW_UUID_OR_TOKEN" for c in tr.cards)


def test_case_h_mixed_payment_mode():
    sale = SaleFact(sale_id=6, total=140.0)
    fuelings = [FuelingFact(fueling_id=1, sale_id=6, amount=140.0)]
    payments = [
        {"nomeFormaPagamento": "CARTAO POS", "valorPagamento": 100.0, "financeiroCodigo": 1},
        {"nomeFormaPagamento": "DINHEIRO", "valorPagamento": 40.0, "tipoFormaPagamento": "D"},
    ]
    cards = [{"cartaoCodigo": 1, "valor": 100.0, "nsu": NSU_A}]
    tr = build_fueling_settlement_trace(sale=sale, fuelings=fuelings, payment_rows=payments, card_rows=cards)
    assert tr.payment_mode == "MIXED"
    assert tr.payment_mode != "SINGLE_ELECTRONIC"


def test_case_i_employee_difference_preserved():
    sale = SaleFact(sale_id=7, total=100.0, employee_id=111, employee_name="VENDEDOR")
    fuelings = [
        FuelingFact(
            fueling_id=1,
            sale_id=7,
            amount=100.0,
            employee_id=222,
            employee_name="FRENTISTA",
        )
    ]
    payments = [{"nomeFormaPagamento": "DINHEIRO", "valorPagamento": 100.0, "tipoFormaPagamento": "D"}]
    tr = build_fueling_settlement_trace(sale=sale, fuelings=fuelings, payment_rows=payments)
    assert tr.sale and tr.sale.employee_id == 111
    assert tr.fuelings[0].employee_id == 222


def test_case_j_explained_does_not_change_legacy_score():
    """TRACE=EXPLAINED e score legado 95 podem coexistir (FR-02)."""
    # Trace factual
    sale = SaleFact(sale_id=366670631, total=408.73, employee_id=299254)
    fuelings = [
        FuelingFact(
            fueling_id=1,
            sale_id=366670631,
            amount=100.0,
            timestamp="2026-08-10T17:41:10-03:00",
            settlement_timestamp="2026-08-10T18:16:11-03:00",
            employee_id=299254,
        ),
        FuelingFact(
            fueling_id=2,
            sale_id=366670631,
            amount=268.73,
            timestamp="2026-08-10T17:58:06-03:00",
            settlement_timestamp="2026-08-10T18:16:11-03:00",
            employee_id=299254,
        ),
        FuelingFact(
            fueling_id=3,
            sale_id=366670631,
            amount=40.0,
            timestamp="2026-08-10T18:02:55-03:00",
            settlement_timestamp="2026-08-10T18:16:11-03:00",
            employee_id=299254,
        ),
    ]
    payments = [
        {"nomeFormaPagamento": "CARTAO POS", "valorPagamento": 100.0, "financeiroCodigo": 1},
        {"nomeFormaPagamento": "CARTAO POS", "valorPagamento": 268.73, "financeiroCodigo": 2},
        {"nomeFormaPagamento": "DINHEIRO", "valorPagamento": 40.0, "tipoFormaPagamento": "D"},
    ]
    cards = [
        {"cartaoCodigo": 1, "valor": 100.0, "nsu": NSU_A},
        {"cartaoCodigo": 2, "valor": 268.73, "nsu": NSU_B},
    ]
    tr = build_fueling_settlement_trace(
        sale=sale, fuelings=fuelings, payment_rows=payments, card_rows=cards
    )
    assert tr.trace_status == "EXPLAINED"

    # Score legado continua 95 com projeção N→1 (Premmia no total)
    items = [
        AbastecimentoRestV1(
            idAbastecimento=391470186,
            uuid="a",
            dataHora="2026-08-10T17:41:10-03:00",
            bico=11,
            litros=14.599,
            precoUnitario=6.85,
            valorTotal=100.0,
            idFrentista=299254,
            nomeFrentista="CAIO",
            idEmpresa=74014,
            idVenda=366670631,
            formaPagamento="Cartão Premmia",
            dataHoraBaixa="2026-08-10T18:16:11-03:00",
            cartaoBandeira="Premmia",
            cartaoNsu=NSU_A,
            cartaoAutorizacao=NSU_A,
            isEspecie=False,
        ),
        AbastecimentoRestV1(
            idAbastecimento=391470185,
            uuid="b",
            dataHora="2026-08-10T17:58:06-03:00",
            bico=8,
            litros=39.231,
            precoUnitario=6.85,
            valorTotal=268.73,
            idFrentista=299254,
            nomeFrentista="CAIO",
            idEmpresa=74014,
            idVenda=366670631,
            formaPagamento="Cartão Premmia",
            dataHoraBaixa="2026-08-10T18:16:11-03:00",
            cartaoBandeira="Premmia",
            cartaoNsu=NSU_A,
            isEspecie=False,
        ),
        AbastecimentoRestV1(
            idAbastecimento=391470184,
            uuid="c",
            dataHora="2026-08-10T18:02:55-03:00",
            bico=19,
            litros=8.351,
            precoUnitario=4.79,
            valorTotal=40.0,
            idFrentista=299254,
            nomeFrentista="CAIO",
            idEmpresa=74014,
            idVenda=366670631,
            formaPagamento="Cartão Premmia",
            dataHoraBaixa="2026-08-10T18:16:11-03:00",
            cartaoBandeira="Premmia",
            cartaoNsu=NSU_A,
            isEspecie=False,
        ),
    ]
    assert _is_eletronico(items[0]) is True
    occ = FraudDetectionEngine()._detect(items, _settings())
    assert len(occ) == 1
    assert occ[0].scoreGravidade == 95
    assert occ[0].nivelRisco == "ALTO"
    # tensão deliberada FR-01 vs FR-02
    assert tr.trace_status == "EXPLAINED"
    assert occ[0].scoreGravidade == 95
