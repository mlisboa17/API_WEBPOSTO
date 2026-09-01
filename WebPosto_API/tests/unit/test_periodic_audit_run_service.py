import asyncio

import pytest

from src.models.response_model import WebPostoResponse
from src.services.periodic_audit_run_service import PeriodicAuditRunService


class FakeIntelligence:
    async def build(self, start, end, company, center):
        return WebPostoResponse.ok({
            "scope": {"centerCoverage": {
                "despesas": {"status": "COMPROVADA"},
                "caixas": {"status": "COMPROVADA"},
                "banco": {"status": "COMPROVADA"},
            }},
            "employeeAccountability": {},
            "sangriaIntelligence": {"answers": {}, "fluxo": {}},
            "valeForensics": {"valorTotal": 0},
        })


def test_run_is_idempotent_and_has_complete_audit_trail(tmp_path):
    service = PeriodicAuditRunService(tmp_path / "runs.json", FakeIntelligence())
    first = asyncio.run(service.open_run("cycle-1", "5555", "PISTA", "2026-07-01", "2026-07-07"))
    second = asyncio.run(service.open_run("cycle-1", "5555", "PISTA", "2026-07-01", "2026-07-07"))
    assert first.id == second.id
    assert first.eventos[0].action == "OPENED"

    resolved = service.resolve(first.id, first.itens[0].id, "Auditor", "documento-123")
    approved = service.approve(first.id, "Diretor")
    assert resolved.eventos[-1].action == "ITEM_RESOLVED"
    assert approved.status == "APROVADO"
    assert [event.action for event in approved.eventos] == ["OPENED", "ITEM_RESOLVED", "APPROVED"]


def test_run_rejects_invalid_period(tmp_path):
    service = PeriodicAuditRunService(tmp_path / "runs.json", FakeIntelligence())
    with pytest.raises(ValueError, match="INVALID_PERIOD"):
        asyncio.run(service.open_run("cycle-1", "5555", "PISTA", "2026-07-08", "2026-07-01"))


def test_pdf_reconciliation_is_audited_and_blocks_approval_until_reviewed(tmp_path):
    service = PeriodicAuditRunService(tmp_path / "runs.json", FakeIntelligence())
    run = asyncio.run(service.open_run("cycle-1", "5555", "PISTA", "2026-07-01", "2026-07-07"))
    service.resolve(run.id, run.itens[0].id, "Auditor", "documento-123")
    recorded = service.record_reconciliation(
        run.id,
        "evidence-1",
        "abc123",
        {"status": "DIVERGENT", "comparisons": [{"metric": "withdrawals"}]},
        "Auditor",
    )
    assert recorded.eventos[-1].action == "PDF_RECONCILED"
    with pytest.raises(ValueError, match="sem revisão humana"):
        service.approve(run.id, "Diretor")

    reviewed = service.review_reconciliation(
        run.id, "evidence-1", "Diretor", "Diferença justificada por corte de horário."
    )
    approved = service.approve(run.id, "Diretor")
    assert reviewed.reconciliacoes[0].reviewed_by == "Diretor"
    assert reviewed.eventos[-1].action == "PDF_RECONCILIATION_REVIEWED"
    assert approved.status == "APROVADO"
