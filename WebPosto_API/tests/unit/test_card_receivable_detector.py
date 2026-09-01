"""Unit tests — CardReceivableDetector (VALUE-04), incluindo o sinal LEVEL 2
(CARD_SETTLEMENT_GAP_V2) introduzido em 2026-07-21 via /INTEGRACAO/CARTAO."""

from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal

from src.services.decision_discovery.detectors.card_receivable_detector import (
    CardReceivableDetector,
)


def _base_payload(**overrides):
    payload = {
        "buckets": {"vencido": [], "recebido": [], "pendente": []},
        "card_sales_count": 0,
        "card_sales_gross": 0.0,
        "bank_credits": 0.0,
        "data_quality": 0.85,
        "card_data_available": False,
        "cartao_gross_v2": 0.0,
        "cartao_net_expected_v2": 0.0,
        "cartao_txn_count_v2": 0,
        "card_data_available_v2": False,
    }
    payload.update(overrides)
    return payload


def test_overdue_receivable_signal_detected():
    detector = CardReceivableDetector()
    payload = _base_payload(
        buckets={
            "vencido": [
                {"valor": "3000.00", "vencimento": "2026-06-01", "cliente": "Cliente A"},
            ],
            "recebido": [],
            "pendente": [],
        }
    )
    analyses = detector._detect_signals(payload, ref_date=date(2026, 7, 21))
    signals = [a["signal_type"] for a in analyses]
    assert "OVERDUE_RECEIVABLE" in signals


def test_no_signal_when_gap_below_threshold():
    detector = CardReceivableDetector()
    payload = _base_payload(
        buckets={
            "vencido": [{"valor": "100.00", "vencimento": "2026-06-01", "cliente": "Cliente A"}],
            "recebido": [],
            "pendente": [],
        }
    )
    analyses = detector._detect_signals(payload, ref_date=date(2026, 7, 21))
    assert analyses == []


def test_card_settlement_gap_v2_signal_uses_real_taxa():
    detector = CardReceivableDetector()
    payload = _base_payload(
        buckets={"vencido": [], "recebido": [], "pendente": []},
        card_data_available_v2=True,
        cartao_gross_v2=10000.0,
        cartao_net_expected_v2=9700.0,  # liquido esperado real (ja descontada a taxa por venda)
        cartao_txn_count_v2=42,
    )
    analyses = detector._detect_signals(payload, ref_date=date(2026, 7, 21))
    v2 = next((a for a in analyses if a["signal_type"] == "CARD_SETTLEMENT_GAP_V2"), None)
    assert v2 is not None
    assert v2["evidence"]["reconciliation_level"] == CardReceivableDetector.RECONCILIATION_LEVEL_V2
    assert v2["evidence"]["gross_v2"] == 10000.0
    assert v2["gap_value"] == 9700.0  # settled_value=0 nesse payload
    assert "taxa REAL" in v2["evidence"]["limitation"]


def test_card_settlement_gap_v2_absent_without_cartao_data():
    detector = CardReceivableDetector()
    payload = _base_payload(card_data_available_v2=False, cartao_net_expected_v2=0.0)
    analyses = detector._detect_signals(payload, ref_date=date(2026, 7, 21))
    assert all(a["signal_type"] != "CARD_SETTLEMENT_GAP_V2" for a in analyses)


def test_card_settlement_gap_v2_attaches_evidence_items():
    detector = CardReceivableDetector()
    payload = _base_payload(
        card_data_available_v2=True,
        cartao_gross_v2=15000.0,
        cartao_net_expected_v2=14721.0,
        cartao_txn_count_v2=2,
        cartao_rows_v2=[
            {
                "empresaCodigo": 74014,
                "codigo": 1,
                "vendaCodigo": 501,
                "valor": "10000.00",
                "taxaPercentual": "2.79",
                "nsu": "111222",
                "autorizacao": "999888",
                "administradoraCodigo": 12345,
                "codigoBandeira": "VISA",
                "centroCustoDescricao": "PISTA",
                "pendente": False,
                "dataMovimento": "2026-07-10",
            },
            {
                "empresaCodigo": 74014,
                "codigo": 2,
                "vendaCodigo": 502,
                "valor": "4721.00",
                "taxaPercentual": None,
                "nsu": "333444",
                "autorizacao": "777666",
                "administradoraCodigo": 12345,
                "codigoBandeira": "VISA",
                "centroCustoDescricao": "LOJA",
                "pendente": True,
                "dataMovimento": "2026-07-10",
            },
        ],
    )
    analyses = detector._detect_signals(
        payload, ref_date=date(2026, 7, 21), tenant_code="74014", tenant_name="Posto Doze"
    )
    v2 = next(a for a in analyses if a["signal_type"] == "CARD_SETTLEMENT_GAP_V2")
    items = v2["evidence"]["evidence_items"]
    assert len(items) == 2
    assert v2["evidence"]["evidence_items_count"] == 2
    first = items[0]  # maior valor primeiro
    assert first["amount"] == 10000.0
    assert first["document_reference"] == "111222"
    assert first["raw_reference"]["centroCustoDescricao"] == "PISTA"
    assert first["tenant_id"] == "74014"
    assert first["tenant_name"] == "Posto Doze"


def test_fetch_cartao_v2_applies_per_transaction_rate():
    class FakeResp:
        def __init__(self, data):
            self.success = True
            self.data = data

    class FakeClient:
        def __init__(self):
            self.calls = 0

        async def call_endpoint(self, key, params=None):
            self.calls += 1
            if self.calls == 1:
                return FakeResp(
                    {
                        "resultados": [
                            {"codigo": 1, "valor": "1000.00", "taxaPercentual": "2.79"},
                            {"codigo": 2, "valor": "500.00", "taxaPercentual": None},
                        ]
                    }
                )
            return FakeResp({"resultados": []})

    gross, net, count, rows = asyncio.run(
        CardReceivableDetector._fetch_cartao_v2(FakeClient(), "74014", "2026-07-01", "2026-07-10")
    )
    assert gross == Decimal("1500.00")
    assert count == 2
    assert len(rows) == 2
    # 1000 * (1 - 0.0279) + 500 (sem taxa, usa valor cheio)
    assert net == Decimal("1000.00") * (Decimal("1") - Decimal("2.79") / Decimal("100")) + Decimal("500.00")


def test_fetch_cartao_v2_returns_zero_when_endpoint_fails():
    class FakeResp:
        def __init__(self):
            self.success = False
            self.data = None
            self.error = "boom"

    class FakeClient:
        async def call_endpoint(self, key, params=None):
            return FakeResp()

    gross, net, count, rows = asyncio.run(
        CardReceivableDetector._fetch_cartao_v2(FakeClient(), "74014", "2026-07-01", "2026-07-10")
    )
    assert (gross, net, count, rows) == (Decimal("0"), Decimal("0"), 0, [])
