"""Unit tests — DIR-01 decision evidence nominal matching."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from src.services.decision_evidence.decision_evidence_service import DecisionEvidenceService
from src.services.decision_evidence.expense_evidence_builder import build_expense_evidence_items
from src.services.decision_evidence.nominal_matcher import (
    MATCH_AMBIGUOUS,
    MATCH_EXACT,
    MATCH_NO_MATCH,
    MATCH_PROBABLE,
    NominalCandidate,
    NominalMatcher,
    PrestacaoNominalMatcher,
    build_nominal_candidates_from_screen_rows,
    build_prestacao_candidates,
)
from src.services.decision_evidence.models import NominalEvidenceItem
from src.services.decision_evidence.prestacao_nominal_extractor import (
    extract_vale_funcionario_items,
    locate_prestacao_source,
    load_prestacao_nominal_items,
)

ROOT = Path(__file__).resolve().parents[2]
EXPENSE_SNAPSHOT = (
    ROOT
    / "snapshots"
    / "discovery_expense"
    / "discovery_expense_74014_74014_2026-06-05_2026-07-04.json"
)
CATEGORY = "Vale de funcionário referente a consolidação de caixa"
DECISION_ID = "175da101-6f68-42f4-9d2b-9b42e6cedea2"


@pytest.mark.skipif(not EXPENSE_SNAPSHOT.exists(), reason="snapshot real ausente")
def test_build_expense_evidence_items_from_real_snapshot():
    payload = json.loads(EXPENSE_SNAPSHOT.read_text(encoding="utf-8"))
    rows = payload["expense_data"]["current_expenses"]
    items = build_expense_evidence_items(
        rows,
        category=CATEGORY,
        tenant_id="74014",
        tenant_name="POSTO DOZE FILIAL II",
    )
    assert len(items) == 16
    total = round(sum(item.amount for item in items), 2)
    assert total == 8401.0
    assert all(item.source == "/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE" for item in items)


def test_nominal_matcher_exact_and_ambiguous():
    candidates = [
        NominalCandidate(
            empresa_codigo=74014,
            data="2026-06-14",
            valor=Decimal("150.00"),
            funcionario_codigo=299251,
            caixa_codigo=4346306,
            turno="1º TURNO",
            kind="VALE_FUN_TURNO",
        ),
        NominalCandidate(
            empresa_codigo=74014,
            data="2026-06-14",
            valor=Decimal("150.00"),
            funcionario_codigo=299252,
            caixa_codigo=4346307,
            turno="2º TURNO",
            kind="VALE_FUN_TURNO",
        ),
    ]
    matcher = NominalMatcher(candidates)
    ambiguous = matcher.match_financial_row(
        empresa_codigo=74014,
        data="2026-06-14",
        valor=150.0,
    )
    assert ambiguous.status == MATCH_AMBIGUOUS
    assert len(ambiguous.candidates) == 2

    matcher2 = NominalMatcher([candidates[0]])
    exact = matcher2.match_financial_row(
        empresa_codigo=74014,
        data="2026-06-14",
        valor=150.0,
    )
    assert exact.status == MATCH_EXACT
    assert exact.candidate.funcionario_codigo == 299251


def test_nominal_matcher_probable_by_near_date():
    cand = NominalCandidate(
        empresa_codigo=74014,
        data="2026-06-13",
        valor=Decimal("150.00"),
        funcionario_codigo=299251,
        caixa_codigo=4346306,
        turno="1º TURNO",
        kind="VALE_FUN_TURNO",
    )
    matcher = NominalMatcher([cand])
    result = matcher.match_financial_row(
        empresa_codigo=74014,
        data="2026-06-14",
        valor=150.0,
    )
    assert result.status == MATCH_PROBABLE


def test_build_nominal_candidates_from_screen_rows():
    rows = [
        {
            "origem": "caixa",
            "empresaCodigo": 74014,
            "data": "2026-06-14",
            "valor": "500.00",
            "funcionarioCodigo": 123,
            "caixaCodigo": 999,
            "turno": "1º TURNO",
            "raw": {"ap_valeFunApurado": 150.0},
        }
    ]
    cands = build_nominal_candidates_from_screen_rows(rows)
    assert len(cands) == 2
    kinds = {c.kind for c in cands}
    assert kinds == {"DESPESA_TURNO", "VALE_FUN_TURNO"}


PRESTACAO_MD = (
    ROOT.parent.parent / "NewWebLogos" / "docs" / "validation" / "RAW_DATA_POSTO_DOZE_2026-06.md"
)


@pytest.mark.skipif(not PRESTACAO_MD.exists(), reason="RAW prestacao DOZE ausente")
def test_prestacao_extractor_parses_vale_section():
    items, meta = extract_vale_funcionario_items(
        path=PRESTACAO_MD,
        empresa_codigo="74014",
        tenant_name="POSTO DOZE FILIAL II",
    )
    assert meta["items_extracted"] == len(items)
    assert len(items) >= 10
    assert all(item.source == "PRESTACAO_CONTAS" for item in items)
    assert all(item.financial_nature == "VALE_FUNCIONARIO" for item in items)
    jeymerson = [i for i in items if "JEYMERSON" in (i.person_name or "").upper()]
    assert len(jeymerson) == 1
    assert jeymerson[0].amount == 1000.0
    assert jeymerson[0].raw_amount == -1000.0


@pytest.mark.skipif(not PRESTACAO_MD.exists(), reason="RAW prestacao DOZE ausente")
def test_locate_prestacao_for_74014():
    locate = locate_prestacao_source(
        empresa_codigo=74014,
        period_start="2026-06-05",
        period_end="2026-07-04",
    )
    assert locate["found"] is True
    assert locate["empresa_codigo"] == "74014"
    assert "74014" in str(locate.get("path", "")) or "DOZE" in str(locate.get("path", "")).upper()


def test_prestacao_matcher_ambiguous_when_multiple_financial_same_amount():
    items = [
        NominalEvidenceItem(
            source="PRESTACAO_CONTAS",
            source_file="test.pdf",
            empresa_codigo="74014",
            amount=1000.0,
            raw_amount=-1000.0,
            person_name="JEYMERSON VITOR",
            financial_nature="VALE_FUNCIONARIO",
            capture_origin="ACCOUNTABILITY_REPORT",
        )
    ]
    candidates = build_prestacao_candidates(items)
    matcher = PrestacaoNominalMatcher(candidates, no_match_amount_counts={Decimal("1000.00"): 3})
    result = matcher.match_financial_row(
        empresa_codigo=74014,
        data="2026-06-16",
        valor=1000.0,
        category="Vale de funcionário referente a consolidação de caixa",
    )
    assert result.status == MATCH_AMBIGUOUS


def test_prestacao_matcher_probable_unique_amount():
    items = [
        NominalEvidenceItem(
            source="PRESTACAO_CONTAS",
            source_file="test.pdf",
            empresa_codigo="74014",
            amount=690.0,
            raw_amount=-690.0,
            person_name="LENILSON MIGUEL",
            financial_nature="VALE_FUNCIONARIO",
            capture_origin="ACCOUNTABILITY_REPORT",
            period_start="2026-06-01",
            period_end="2026-06-28",
        )
    ]
    candidates = build_prestacao_candidates(items)
    matcher = PrestacaoNominalMatcher(candidates, no_match_amount_counts={Decimal("690.00"): 1})
    result = matcher.match_financial_row(
        empresa_codigo=74014,
        data="2026-06-20",
        valor=690.0,
        category="Vale de funcionário referente a consolidação de caixa",
    )
    assert result.status == MATCH_PROBABLE
    assert result.candidate is not None
    assert "LENILSON" in (result.candidate.description or "").upper()


@pytest.mark.asyncio
async def test_evidence_service_rebuild_from_expense_cache():
    service = DecisionEvidenceService()
    candidate = {
        "id": "test-decision-74014",
        "detector": "ExpenseDetector",
        "title": "Teste",
        "summary": "Teste summary",
        "category": "COST",
        "impact_type": "cost",
        "tenant": "74014",
        "tenant_name": "POSTO DOZE FILIAL II",
        "period": {"start": "2026-06-05", "end": "2026-07-04"},
        "confidence": 0.89,
        "money_found": {"at_risk": {"value": 7501.0}},
        "evidence": {
            "category": CATEGORY,
            "current_count": 16,
            "baseline_count": 7,
            "anomaly_type": "CATEGORY_SPIKE",
        },
        "baseline": {"current_value": 8401.0, "baseline_value": 900.0},
        "source_endpoints": ["/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE"],
    }
    if not EXPENSE_SNAPSHOT.exists():
        pytest.skip("snapshot real ausente")

    items = service._load_evidence_items(candidate, candidate["evidence"])
    assert len(items) == 16
    assert round(sum(i.amount for i in items), 2) == 8401.0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_evidence_nominal_enrichment_value03():
    """Integração real com API WebPosto — decisão VALUE-03."""
    service = DecisionEvidenceService()
    result = await service.get_evidence(DECISION_ID)
    if not result:
        pytest.skip("snapshot owner_analysis DIR01 ausente")

    assert result.evidence_items_count == 16
    assert result.evidence_items_total == 8401.0
    summary = (result.source_metadata or {}).get("nominal_enrichment", {}).get("match_summary") or {}
    assert (
        summary.get("EXACT", 0)
        + summary.get("PROBABLE", 0)
        + summary.get("AMBIGUOUS", 0)
        + summary.get("NO_MATCH", 0)
        == 16
    )
    for item in result.evidence_items:
        assert item.match_status in {MATCH_EXACT, MATCH_PROBABLE, MATCH_AMBIGUOUS, MATCH_NO_MATCH, None}
        if item.match_status == MATCH_NO_MATCH:
            assert item.person_name is None
