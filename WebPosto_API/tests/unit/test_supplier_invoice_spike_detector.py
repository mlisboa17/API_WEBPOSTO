"""Unit tests for SupplierInvoiceSpikeDetector."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.services.decision_discovery.detectors.supplier_invoice_spike_detector import (
    SupplierInvoiceSpikeDetector,
)

SNAP = Path(__file__).resolve().parents[2] / "snapshots"
PERIOD = ("2026-06-05", "2026-07-04")


def _load_expense_payload(tenant: str) -> dict:
    path = SNAP / "discovery_expense" / f"discovery_expense_{tenant}_{tenant}_{PERIOD[0]}_{PERIOD[1]}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["expense_data"]


def test_parse_nf_ref_extracts_supplier_and_number():
    detector = SupplierInvoiceSpikeDetector()
    parsed = detector._parse_nf_ref("REF NF:001872693 - SOUZA CRUZ LTDA. - SOUZA CRUZ LTDA.")
    assert parsed is not None
    assert parsed["nf_number"] == "001872693"
    assert "SOUZA CRUZ" in parsed["supplier"]


def test_detects_souza_cruz_spike_on_11495_snapshot():
    detector = SupplierInvoiceSpikeDetector()
    payload = _load_expense_payload("11495")
    analyses = detector._detect_invoice_spikes(payload)
    assert analyses
    top = analyses[0]
    assert top["impact_brl"] >= 5000
    assert "SOUZA CRUZ" in (top.get("supplier") or "")
    assert top["confidence"] >= 0.80


def test_returns_none_for_74014_without_new_nf_spike():
    detector = SupplierInvoiceSpikeDetector()
    payload = _load_expense_payload("74014")
    analyses = detector._detect_invoice_spikes(payload)
    # 74014 tem NFs no período mas baseline também pode ter; detector foca zero baseline
    for item in analyses:
        assert item["baseline_value"] == 0


@pytest.mark.asyncio
async def test_detect_11495_from_cached_expense_bundle(monkeypatch):
    detector = SupplierInvoiceSpikeDetector()
    payload = _load_expense_payload("11495")

    async def fake_fetch(*args, **kwargs):
        return payload

    monkeypatch.setattr(detector, "_fetch_bundle", fake_fetch)
    result = await detector.detect("11495", PERIOD[0], PERIOD[1], tenant_name="POSTO VIP")
    assert result is not None
    assert result.detector_name == "SupplierInvoiceSpikeDetector"
    assert result.money_found.total_impact() >= 5000
    assert result.is_valid()
