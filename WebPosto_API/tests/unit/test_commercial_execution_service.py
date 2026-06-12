"""Testes F07.7 — Commercial Execution & Outcome Tracking."""
from __future__ import annotations

import pytest

from src.services.commercial_execution_service import CommercialExecutionService, LIFECYCLE_STATES


def _sample_actions(n: int = 5) -> list[dict]:
    actions = []
    for i in range(n):
        actions.append(
            {
                "id": f"ACT-{i}",
                "tipo": "PROTEGER_MARGEM",
                "titulo": f"Ação {i}",
                "prioridade": "ALTA" if i % 2 == 0 else "MEDIA",
                "status": "RECOMENDADA",
                "empresaCodigo": 11495,
                "produtoCodigo": 1000 + i,
                "impactoEstimadoReceita": 50 + i,
                "impactoEstimadoMargem": 15 + i,
                "responsavel": {"ownerId": 1, "ownerName": "Gestor PV", "ownerRole": "GERENTE"},
                "evidencia": {"empresaCodigo": 11495},
                "lineage": [{"origem": "F07.6"}],
            }
        )
    return actions


def test_assignment_engine_lifecycle_states():
    svc = CommercialExecutionService()
    assignment = svc._assignment_engine(_sample_actions(12), "2026-06-07", None)
    actions = assignment["actions"]
    assert len(actions) == 12
    statuses = {a["lifecycleStatus"] for a in actions}
    assert statuses.issubset(set(LIFECYCLE_STATES))
    assert all(a.get("responsavelNome") for a in actions)
    assert all(a.get("empresaCodigo") for a in actions)


def test_evidence_required_for_validated():
    svc = CommercialExecutionService()
    assignment = svc._assignment_engine(_sample_actions(14), "2026-06-07", None)
    actions = assignment["actions"]
    actions, evidences = svc._evidence_engine(actions, "2026-06-07")
    validadas = [a for a in actions if a["lifecycleStatus"] == "VALIDADA"]
    assert validadas
    assert all(a.get("hasExecutionEvidence") for a in validadas)
    assert len(evidences) >= len(validadas)
    for ev in evidences:
        assert ev.get("executionEvidence") is True
        assert ev.get("executionUser")
        assert ev.get("lineage")


def test_outcome_and_roi_real():
    svc = CommercialExecutionService()
    assignment = svc._assignment_engine(_sample_actions(14), "2026-06-07", None)
    actions = assignment["actions"]
    actions, _ = svc._evidence_engine(actions, "2026-06-07")
    actions = svc._apply_outcome_to_actions(actions)
    revenue = svc._revenue_lift_tracking(actions)
    margin = svc._margin_improvement_tracking(actions)
    outcome = svc._outcome_measurement(actions, {"receitaProdutosVendidos": 1104.01, "margemBrutaTotal": 350.94})
    qa = svc._qa_gate(actions, None)
    assert revenue["receitaRealizada"] > 0
    assert margin["margemRealizada"] > 0
    assert outcome["depois"]["receitaProdutosVendidos"] >= outcome["antes"]["receitaProdutosVendidos"]
    assert qa["zeroValidadaSemEvidencia"] is True
    assert qa["zeroAcaoSemResponsavel"] is True


@pytest.mark.asyncio
async def test_build_from_homologated_audit():
    svc = CommercialExecutionService()
    resp = await svc.build("2026-06-01", "2026-06-07", None)
    if not resp.success:
        pytest.skip(f"Snapshot F07.6 indisponível: {resp.error}")
    data = resp.data
    assert data.get("sprint") == "F07.7"
    assert data.get("fonte", {}).get("webPostoLive") is False
    assert data.get("commercialAssignmentEngine")
    assert data.get("revenueLiftTracking")
    assert data.get("executiveAnswers", {}).get("1_totalAcoes", 0) > 0
