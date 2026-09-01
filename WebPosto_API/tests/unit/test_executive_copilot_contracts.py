"""Frente C — contrato e gate de verdade do Copiloto Executivo. Sem rede."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from src.services.executive_copilot.contracts import (
    WEBPOSTO_WRITES,
    ClaimStatus,
    Confidence,
    ConfidenceLevel,
    CopilotAnswer,
    EvidenceItem,
    Impact,
    LineageItem,
    PeriodWindow,
    SourceNature,
)
from src.services.executive_copilot.source_registry import (
    BLOCKED_COMPANY,
    FORBIDDEN_DEMO_CODES,
    StaticCompleteSdsDateProvider,
    TruthGate,
    dre_numeric_status,
    resolve_executive_units,
)
from src.services.sds_identity import LICENSED_SDS_CODES
from src.services.sds_sanitize import sanitize_value

SDS_TEST_COMPLETE_DEFAULT = date(2026, 8, 28)


def _period(day: date = SDS_TEST_COMPLETE_DEFAULT) -> dict:
    iso = day.isoformat()
    return {"inicio": iso, "fim": iso}


def _lineage(
    *,
    day: date = SDS_TEST_COMPLETE_DEFAULT,
    unit: int = 5555,
    nature: SourceNature = SourceNature.CHECKPOINT,
    consolidated: bool = False,
) -> list[dict]:
    item: dict = {
        "origem": "sds",
        "fonte": "sds_day_status",
        "periodo": _period(day),
        "referencia": f"sds-checkpoint-{unit}-{day.isoformat()}",
        "naturezaFonte": nature,
    }
    if consolidated:
        item["escopoConsolidado"] = True
    else:
        item["empresaCodigo"] = unit
    return [item]


def _evidence(
    *,
    day: date = SDS_TEST_COMPLETE_DEFAULT,
    unit: int = 5555,
    status: ClaimStatus = ClaimStatus.FACT,
    consolidated: bool = False,
) -> list[dict]:
    item: dict = {
        "id": f"sds-{unit}-{day.isoformat()}",
        "fonte": "SDS",
        "resumo": "Abastecimentos consolidados",
        "claimStatus": status,
        "periodo": _period(day),
    }
    if consolidated:
        item["escopoConsolidado"] = True
    else:
        item["empresaCodigo"] = unit
    return [item]


def _gate(complete: date | None = SDS_TEST_COMPLETE_DEFAULT) -> TruthGate:
    return TruthGate(sds_complete_provider=StaticCompleteSdsDateProvider(complete))


def test_licensed_scope_matches_sds_units() -> None:
    assert LICENSED_SDS_CODES == (5555, 11495, 74014)
    assert SDS_TEST_COMPLETE_DEFAULT == date(2026, 8, 28)
    assert BLOCKED_COMPANY == 118508
    assert FORBIDDEN_DEMO_CODES == frozenset({5333, 15880})
    assert WEBPOSTO_WRITES == 0
    assert not hasattr(TruthGate(), "SDS_FACT_UNTIL")


def test_sds_complete_date_comes_from_provider() -> None:
    gate = _gate(date(2026, 8, 28))
    assert gate.period_status(date(2026, 8, 28)) == ClaimStatus.FACT
    assert gate.period_status(date(2026, 8, 29)) == ClaimStatus.BLOCKED
    assert gate.last_complete_date() == date(2026, 8, 28)

    later = _gate(date(2026, 8, 29))
    assert later.period_status(date(2026, 8, 29)) == ClaimStatus.FACT
    assert later.last_complete_date() == date(2026, 8, 29)

    missing = TruthGate(sds_complete_provider=StaticCompleteSdsDateProvider(None))
    assert missing.period_status(date(2026, 8, 28)) == ClaimStatus.BLOCKED
    assert missing.last_complete_date() is None
    absent = TruthGate()
    assert absent.period_status(date(2026, 8, 28)) == ClaimStatus.BLOCKED


def test_sds_complete_date_appears_in_lineage() -> None:
    answer = _gate(date(2026, 8, 28)).build_answer(
        specialist="OPERACIONAL",
        question="Volume SDS",
        fact="Volume consolidado SDS.",
        period_end=date(2026, 8, 28),
        impact=Impact(amount=None, currency="BRL", status=ClaimStatus.FACT),
        evidence=_evidence(),
        lineage=_lineage(),
        units=[5555],
    )
    payload = answer.to_public_payload()
    assert "2026-08-28" in str(payload["lineage"])
    assert payload["lineage"][0]["sdsCompletoAte"] == "2026-08-28"


def test_profit_without_cmv_has_no_number() -> None:
    gate = _gate()
    impact = gate.profit_impact(revenue=22421.52, cmv=None, evidence=_evidence(), lineage=_lineage())
    assert impact.amount is None
    assert impact.status in {ClaimStatus.UNAVAILABLE, ClaimStatus.BLOCKED}
    answer = gate.build_answer(
        specialist="FINANCEIRO",
        question="Onde estamos perdendo margem?",
        fact="CMV ausente; lucro não pode ser publicado.",
        impact=impact,
        evidence=_evidence(),
        lineage=_lineage(),
        units=[5555],
    )
    dumped = answer.to_public_payload()
    assert dumped["impact"]["amount"] is None
    assert "22421" not in str(dumped.get("fact", ""))
    assert dumped["webpostoWrites"] == 0


def test_economy_without_evidence_is_not_fact() -> None:
    impact = _gate().economy_impact(amount=15000.0, evidence=[], lineage=[])
    assert impact.status != ClaimStatus.FACT
    assert impact.status in {ClaimStatus.ESTIMATED, ClaimStatus.UNAVAILABLE, ClaimStatus.BLOCKED}
    if impact.status != ClaimStatus.ESTIMATED:
        assert impact.amount is None


def test_automatic_expense_is_auto_classified() -> None:
    gate = _gate()
    status = gate.expense_claim_status(method="KEYWORD", homologated=False)
    assert status == ClaimStatus.AUTO_CLASSIFIED
    answer = gate.build_answer(
        specialist="FINANCEIRO",
        question="Quais despesas cresceram sem justificativa?",
        fact="Despesas auto-classificadas por palavra-chave.",
        impact=Impact(amount=36101.56, currency="BRL", status=status),
        evidence=_evidence(status=ClaimStatus.AUTO_CLASSIFIED),
        lineage=_lineage(),
        units=[5555],
    )
    assert answer.impact.status == ClaimStatus.AUTO_CLASSIFIED
    assert answer.confidence.level != ConfidenceLevel.ALTA


def test_expense_method_matrix() -> None:
    gate = _gate()
    assert gate.expense_claim_status(method="KEYWORD", homologated=False) == ClaimStatus.AUTO_CLASSIFIED
    assert gate.expense_claim_status(method="KEYWORD", homologated=True) == ClaimStatus.AUTO_CLASSIFIED
    assert gate.expense_claim_status(method="  manual_review ", homologated=True) == ClaimStatus.FACT
    assert gate.expense_claim_status(method="MANUAL", homologated=False) == ClaimStatus.UNAVAILABLE
    assert gate.expense_claim_status(method="", homologated=True) in {ClaimStatus.UNAVAILABLE, ClaimStatus.BLOCKED}
    assert gate.expense_claim_status(method=None, homologated=True) in {ClaimStatus.UNAVAILABLE, ClaimStatus.BLOCKED}
    assert gate.expense_claim_status(method="TELEPATIA", homologated=True) in {
        ClaimStatus.UNAVAILABLE,
        ClaimStatus.BLOCKED,
    }


def test_simulation_is_always_estimated() -> None:
    answer = _gate().build_answer(
        specialist="FINANCEIRO",
        question="Quanto economizaríamos?",
        fact="",
        inference="Projeção sem base realizada.",
        recommendation="Revisar premissas.",
        impact=Impact(amount=8000.0, currency="BRL", status=ClaimStatus.FACT),
        simulation={"economiaRs": 8000.0, "premissas": {"volume": 1000}},
        evidence=_evidence(),
        lineage=_lineage(),
        units=[5555],
    )
    assert answer.simulation is not None
    assert answer.impact.status == ClaimStatus.ESTIMATED


def test_unit_outside_scope_is_blocked() -> None:
    resolved = resolve_executive_units([999999])
    assert resolved.blocked is not None
    assert resolved.units == []
    answer = _gate().blocked_answer(
        specialist="PRESIDENTE",
        question="Compare 999999",
        reason=resolved.blocked["message"],
        code=resolved.blocked["code"],
    )
    assert answer.blocked is not None
    assert answer.units == []
    assert answer.impact.status == ClaimStatus.BLOCKED


def test_empty_units_only_when_blocked() -> None:
    with pytest.raises(ValidationError):
        CopilotAnswer(
            specialist="PRESIDENTE",
            answer="x",
            impact=Impact(amount=None, currency="BRL", status=ClaimStatus.UNAVAILABLE),
            units=[],
            consolidatedScope=True,
        )
    ok = CopilotAnswer(
        specialist="PRESIDENTE",
        answer="bloqueado",
        impact=Impact(amount=None, currency="BRL", status=ClaimStatus.BLOCKED),
        units=[],
        blocked={"code": "PERIOD_BLOCKED", "message": "sem data SDS"},
    )
    assert ok.units == []
    assert ok.blocked is not None


def test_lineage_requires_source_nature() -> None:
    with pytest.raises(ValidationError):
        LineageItem.model_validate(
            {
                "origem": "sds",
                "fonte": "sds_day_status",
                "periodo": _period(),
                "empresaCodigo": 5555,
                "referencia": "sds-checkpoint-5555-2026-08-28",
            }
        )


@pytest.mark.parametrize("code", [5333, 15880, 6666])
def test_direct_forbidden_unit_is_rejected(code: int) -> None:
    with pytest.raises(ValidationError):
        CopilotAnswer(
            specialist="PRESIDENTE",
            answer="x",
            impact=Impact(amount=None, currency="BRL", status=ClaimStatus.BLOCKED),
            units=[code],
            blocked={"code": "X", "message": "x"},
        )


def test_unknown_unit_does_not_disappear() -> None:
    with pytest.raises(ValidationError):
        CopilotAnswer(
            specialist="PRESIDENTE",
            answer="x",
            impact=Impact(amount=None, currency="BRL", status=ClaimStatus.UNAVAILABLE),
            units=[5555, 999999],
        )
    resolved = resolve_executive_units([999999])
    assert resolved.blocked is not None
    assert 999999 not in resolved.units


def test_6666_is_normalized_and_never_persisted() -> None:
    resolved = resolve_executive_units([6666])
    assert resolved.blocked is None
    assert resolved.units == [11495]
    assert 6666 not in resolved.persisted_units
    payload = _gate().build_answer(
        specialist="PRESIDENTE",
        question="Compare 6666",
        fact="VIP resolvido pelo alias.",
        units=resolved.units,
        evidence=_evidence(unit=11495),
        lineage=_lineage(unit=11495),
        impact=Impact(amount=None, currency="BRL", status=ClaimStatus.UNAVAILABLE),
    ).to_public_payload()
    assert 6666 not in (payload.get("units") or [])
    assert "6666" not in str(payload.get("units"))
    assert 11495 in payload["units"]


def test_118508_is_licensed_loja_unit() -> None:
    resolved = resolve_executive_units([118508])
    assert resolved.blocked is None
    assert resolved.units == [118508]
    assert 6666 not in resolved.persisted_units
    for forbidden in FORBIDDEN_DEMO_CODES:
        other = resolve_executive_units([forbidden])
        assert other.blocked is not None


def test_fact_requires_typed_evidence_and_lineage() -> None:
    gate = _gate()
    with pytest.raises((ValueError, ValidationError)):
        gate.build_answer(
            specialist="OPERACIONAL",
            question="Volume SDS",
            fact="3.630 L",
            impact=Impact(amount=3630.74, currency="BRL", status=ClaimStatus.FACT),
            evidence=[],
            lineage=[],
            units=[5555],
        )
    with pytest.raises((ValueError, ValidationError)):
        CopilotAnswer(
            specialist="OPERACIONAL",
            answer="x",
            impact=Impact(amount=None, currency="BRL", status=ClaimStatus.FACT),
            units=[5555],
            evidence=[{}],
            lineage=_lineage(),
        )
    with pytest.raises((ValueError, ValidationError)):
        CopilotAnswer(
            specialist="OPERACIONAL",
            answer="x",
            impact=Impact(amount=None, currency="BRL", status=ClaimStatus.FACT),
            units=[5555],
            evidence=_evidence(),
            lineage=[{}],
        )
    with pytest.raises((ValueError, ValidationError)):
        EvidenceItem.model_validate(
            {
                "id": "x",
                "fonte": "SDS",
                "resumo": "ok",
                "claimStatus": ClaimStatus.FACT,
                "empresaCodigo": 5555,
            }
        )
    with pytest.raises((ValueError, ValidationError)):
        EvidenceItem.model_validate(
            {
                "id": "x",
                "fonte": "SDS",
                "resumo": "ok",
                "claimStatus": ClaimStatus.FACT,
                "periodo": _period(),
                "empresaCodigo": 5333,
            }
        )
    with pytest.raises((ValueError, ValidationError)):
        gate.build_answer(
            specialist="OPERACIONAL",
            question="Volume",
            fact="x",
            impact=Impact(amount=None, currency="BRL", status=ClaimStatus.FACT),
            evidence=_evidence(status=ClaimStatus.AUTO_CLASSIFIED),
            lineage=_lineage(),
            units=[5555],
        )
    ok = gate.build_answer(
        specialist="OPERACIONAL",
        question="Volume SDS",
        fact="Volume consolidado SDS.",
        period_end=date(2026, 8, 28),
        impact=Impact(amount=None, currency="BRL", status=ClaimStatus.FACT),
        evidence=_evidence(),
        lineage=_lineage(),
        units=[5555],
    )
    assert ok.impact.status == ClaimStatus.FACT
    assert isinstance(ok.evidence[0], EvidenceItem)
    assert isinstance(ok.lineage[0], LineageItem)
    assert ok.confidence.level == ConfidenceLevel.ALTA


def test_webposto_writes_stays_zero() -> None:
    answer = _gate().build_answer(
        specialist="PRESIDENTE",
        question="Resumo",
        fact="SDS disponível.",
        impact=Impact(amount=None, currency="BRL", status=ClaimStatus.FACT),
        evidence=_evidence(),
        lineage=_lineage(),
        units=list(LICENSED_SDS_CODES),
    )
    assert answer.webposto_writes == 0
    assert answer.to_public_payload()["webpostoWrites"] == 0


def test_payload_and_logs_do_not_expose_secrets() -> None:
    dirty = _lineage()
    dirty[0]["fonte"] = "https://api.example/x?token=abc"
    dirty[0]["referencia"] = "token=super-secret"
    answer = _gate().build_answer(
        specialist="PRESIDENTE",
        question="Resumo",
        fact="ok",
        impact=Impact(amount=None, currency="BRL", status=ClaimStatus.FACT),
        evidence=_evidence(),
        lineage=dirty,
        units=[5555],
    )
    blob = str(sanitize_value(answer.to_public_payload()))
    assert "super-secret" not in blob
    assert "token=abc" not in blob
    assert "[redacted]" in blob or "[url-redacted]" in blob
    assert "5333" not in blob


def test_confidence_bounds_and_coherence() -> None:
    with pytest.raises(ValidationError):
        Confidence(score=-0.1, level=ConfidenceLevel.BAIXA)
    with pytest.raises(ValidationError):
        Confidence(score=1.1, level=ConfidenceLevel.ALTA)
    with pytest.raises(ValidationError):
        Confidence(score=0.5, level="ALTISSIMA")
    with pytest.raises(ValidationError):
        Confidence.model_validate({"score": 0.5, "level": "MEDIA", "extraFoo": True})
    blocked = CopilotAnswer(
        specialist="PRESIDENTE",
        answer="bloqueado",
        impact=Impact(amount=None, currency="BRL", status=ClaimStatus.BLOCKED),
        blocked={"code": "X", "message": "x"},
        confidence=Confidence(score=0.99, level=ConfidenceLevel.ALTA),
    )
    assert blocked.confidence.level != ConfidenceLevel.ALTA
    unavailable = CopilotAnswer(
        specialist="PRESIDENTE",
        answer="indisponivel",
        impact=Impact(amount=None, currency="BRL", status=ClaimStatus.UNAVAILABLE),
        units=[5555],
        confidence=Confidence(score=0.99, level=ConfidenceLevel.ALTA),
    )
    assert unavailable.confidence.level != ConfidenceLevel.ALTA
    fact = _gate().build_answer(
        specialist="OPERACIONAL",
        question="Volume",
        fact="ok",
        impact=Impact(amount=None, currency="BRL", status=ClaimStatus.FACT),
        evidence=_evidence(),
        lineage=_lineage(),
        units=[5555],
    )
    assert fact.confidence.level == ConfidenceLevel.ALTA
    assert 0.0 <= fact.confidence.score <= 1.0


def test_unexpected_public_extra_is_rejected() -> None:
    with pytest.raises(ValidationError):
        CopilotAnswer(
            specialist="PRESIDENTE",
            answer="x",
            impact=Impact(amount=None, currency="BRL", status=ClaimStatus.UNAVAILABLE),
            units=[5555],
            campoInesperado=True,
        )


def test_fact_rejects_mismatched_unit_evidence_and_lineage() -> None:
    with pytest.raises(ValidationError):
        CopilotAnswer(
            specialist="OPERACIONAL",
            answer="x",
            impact=Impact(amount=None, currency="BRL", status=ClaimStatus.FACT),
            units=[5555],
            evidence=_evidence(unit=11495),
            lineage=_lineage(unit=5555),
        )
    with pytest.raises(ValidationError):
        CopilotAnswer(
            specialist="OPERACIONAL",
            answer="x",
            impact=Impact(amount=None, currency="BRL", status=ClaimStatus.FACT),
            units=[5555],
            evidence=_evidence(unit=5555),
            lineage=_lineage(unit=11495),
        )


def test_fact_accepts_explicit_consolidated_scope() -> None:
    answer = CopilotAnswer(
        specialist="PRESIDENTE",
        answer="rede",
        impact=Impact(amount=None, currency="BRL", status=ClaimStatus.FACT),
        units=list(LICENSED_SDS_CODES),
        consolidatedScope=True,
        evidence=_evidence(consolidated=True),
        lineage=_lineage(consolidated=True),
    )
    assert answer.impact.status == ClaimStatus.FACT
    assert set(answer.units) == set(LICENSED_SDS_CODES)


def test_fact_accepts_three_units_with_coherent_evidence() -> None:
    answer = CopilotAnswer(
        specialist="PRESIDENTE",
        answer="rede",
        impact=Impact(amount=None, currency="BRL", status=ClaimStatus.FACT),
        units=list(LICENSED_SDS_CODES),
        evidence=_evidence(unit=5555) + _evidence(unit=11495) + _evidence(unit=74014),
        lineage=_lineage(unit=5555) + _lineage(unit=11495) + _lineage(unit=74014),
    )
    assert answer.impact.status == ClaimStatus.FACT
    assert answer.units == list(LICENSED_SDS_CODES)


def test_snapshot_cannot_sustain_fact() -> None:
    with pytest.raises(ValidationError):
        CopilotAnswer(
            specialist="OPERACIONAL",
            answer="x",
            impact=Impact(amount=None, currency="BRL", status=ClaimStatus.FACT),
            units=[5555],
            evidence=_evidence(),
            lineage=_lineage(nature=SourceNature.SNAPSHOT),
        )
    checkpoint = CopilotAnswer(
        specialist="OPERACIONAL",
        answer="ok",
        impact=Impact(amount=None, currency="BRL", status=ClaimStatus.FACT),
        units=[5555],
        evidence=_evidence(),
        lineage=_lineage(nature=SourceNature.CHECKPOINT),
    )
    assert checkpoint.impact.status == ClaimStatus.FACT
    homologated = CopilotAnswer(
        specialist="OPERACIONAL",
        answer="ok",
        impact=Impact(amount=None, currency="BRL", status=ClaimStatus.FACT),
        units=[5555],
        evidence=_evidence(),
        lineage=_lineage(nature=SourceNature.LOCAL_HOMOLOGATED),
    )
    assert homologated.impact.status == ClaimStatus.FACT
    snapshot = CopilotAnswer(
        specialist="PRESIDENTE",
        answer="snapshot legado",
        impact=Impact(amount=None, currency="BRL", status=ClaimStatus.UNAVAILABLE),
        units=[5555],
        evidence=_evidence(status=ClaimStatus.UNAVAILABLE),
        lineage=_lineage(nature=SourceNature.SNAPSHOT),
        confidence=Confidence(score=0.99, level=ConfidenceLevel.ALTA),
    )
    assert snapshot.impact.status != ClaimStatus.FACT
    assert snapshot.confidence.level != ConfidenceLevel.ALTA


def test_period_window_order_and_invalid_dates() -> None:
    single = PeriodWindow.model_validate({"inicio": "2026-08-28", "fim": "2026-08-28"})
    assert single.start == single.end
    spanned = PeriodWindow.model_validate({"inicio": "2026-08-27", "fim": "2026-08-28"})
    assert spanned.start < spanned.end
    with pytest.raises(ValidationError):
        PeriodWindow.model_validate({"inicio": "2026-08-29", "fim": "2026-08-28"})
    with pytest.raises(ValidationError):
        PeriodWindow.model_validate({"inicio": "2026-13-01", "fim": "2026-08-28"})
    with pytest.raises(ValidationError):
        PeriodWindow.model_validate({"inicio": "nao-e-data", "fim": "2026-08-28"})
    with pytest.raises(ValidationError):
        PeriodWindow.model_validate({"inicio": "", "fim": "2026-08-28"})


def test_dre_line_without_cost_blocks_profit() -> None:
    status = dre_numeric_status(
        {
            "companyCode": 5555,
            "department": "combustiveis",
            "status": "BLOQUEADO",
            "cost": None,
            "operatingResult": None,
            "missingEvidence": ["CUSTO", "CLASSIFICACAO_DESPESAS"],
        },
        homologated=False,
    )
    assert status in {ClaimStatus.UNAVAILABLE, ClaimStatus.BLOCKED}
    assert status != ClaimStatus.FACT
