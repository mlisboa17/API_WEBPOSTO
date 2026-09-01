"""Testes D02 — normalização e pré-conferência."""
from __future__ import annotations

from src.domain.reconciliation.models import PaymentNatureCode, ReconciliationItem, ReconciliationStatus
from src.domain.reconciliation.payment_normalization import (
    infer_acquirer,
    infer_capture_origin,
    map_vfp_to_payment_nature,
)
from src.domain.reconciliation.nature_strategies import classify_pre_check
from src.services.cash_reconciliation.pre_reconciliation_engine import PreReconciliationEngine


def test_pos_is_capture_origin_not_nature():
    origin = infer_capture_origin("VISA CREDITO POS MANUAL", "CARTAO")
    assert origin.value == "POS_MANUAL"
    nature = map_vfp_to_payment_nature({"nomeFormaPagamento": "VISA CREDITO POS MANUAL", "tipoFormaPagamento": "CARTAO"})
    assert nature == PaymentNatureCode.CARTAO


def test_tef_is_capture_origin():
    origin = infer_capture_origin("MAESTRO TEF", "DEBITO")
    assert origin.value == "TEF"


def test_acquirer_unknown_when_no_evidence():
    assert infer_acquirer("VISA CREDITO") == "UNKNOWN"


def test_pre_reconciliation_auto_match():
    item = ReconciliationItem(
        id="1:2:DINHEIRO",
        filial=11495,
        caixaCodigo=1,
        periodoInicio="2026-06-29",
        periodoFim="2026-07-05",
        paymentNature=PaymentNatureCode.DINHEIRO,
        valorApresentado=100.0,
        valorApurado=100.0,
        diferenca=0.0,
    )
    engine = PreReconciliationEngine()
    items, summary = engine.run([item])
    assert items[0].status == ReconciliationStatus.AUTO_MATCHED
    assert summary.autoMatched == 1


def test_divergent_above_threshold():
    item = ReconciliationItem(
        id="1:2:DINHEIRO",
        filial=11495,
        caixaCodigo=1,
        periodoInicio="2026-06-29",
        periodoFim="2026-07-05",
        paymentNature=PaymentNatureCode.DINHEIRO,
        valorApresentado=1000.0,
        valorApurado=980.0,
        diferenca=20.0,
    )
    outcome, status = classify_pre_check(item)
    assert status == ReconciliationStatus.DIVERGENT


def test_matches_empresa_single_codigo():
    from src.services.analytics_multiselect import build_finance_center_filters
    from src.services.cash_operations_service import CashOperationsService

    filters = build_finance_center_filters("2026-06-29", "2026-07-05", "11495")
    assert CashOperationsService._matches_empresa({"empresaCodigo": 11495}, filters) is True
    assert CashOperationsService._matches_empresa({"empresaCodigo": 5555}, filters) is False
