from datetime import datetime, timezone
from io import BytesIO

import pytest
from pypdf import PdfReader

from src.services.periodic_audit_dossier_service import PeriodicAuditDossierService
from src.services.periodic_audit_run_service import (
    AuditChecklistItem,
    AuditDocumentReconciliation,
    AuditRunEvent,
    PeriodicAuditRun,
)


def approved_run() -> PeriodicAuditRun:
    now = datetime.now(timezone.utc)
    return PeriodicAuditRun(
        id="run-123", cycle_id="cycle-1", empresa_codigo="5555",
        centro_custo="PISTA", data_inicial="2026-07-01", data_final="2026-07-07",
        status="APROVADO", criado_em=now, aprovado_por="Diretor", aprovado_em=now,
        itens=[AuditChecklistItem(
            id="item-1", titulo="Conferencia documental", descricao="Validar",
            severidade="NORMAL", status="RESOLVIDO", fonte="PDF",
            evidencia="documento-123", responsavel="Auditor", resolvido_em=now,
        )],
        reconciliacoes=[AuditDocumentReconciliation(
            evidence_id="evidence-1", sha256="abc123", status="MATCH",
            comparisons=[{"metric": "withdrawals", "pdf": "10", "api": "10", "difference": "0", "status": "MATCH"}],
            reconciled_by="Auditor", reconciled_at=now, reviewed_by="Diretor",
            reviewed_at=now, review_justification="Valores conferidos.",
        )],
        eventos=[AuditRunEvent(action="OPENED", actor="SYSTEM", at=now)],
    )


def test_dossier_contains_scope_evidence_and_audit_trail():
    content = PeriodicAuditDossierService().generate(approved_run())
    reader = PdfReader(BytesIO(content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert len(reader.pages) >= 2
    assert "Dossiê Final de Auditoria" in text
    assert "run-123" in text
    assert "abc123" in text
    assert "Trilha de auditoria" in text


def test_dossier_rejects_unapproved_run():
    run = approved_run().model_copy(update={"status": "AGUARDANDO_CONFERENCIA"})
    with pytest.raises(ValueError, match="DOSSIER_REQUIRES_APPROVED_RUN"):
        PeriodicAuditDossierService().generate(run)
