from __future__ import annotations

import os
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from src.interfaces.http.authz import require_roles
from pydantic import BaseModel, Field

from src.services.periodic_audit_cycle_store import PeriodicAuditCycleStore
from src.services.periodic_audit_run_service import PeriodicAuditRunService
from src.services.periodic_audit_scheduler_service import PeriodicAuditSchedulerService
from src.services.periodic_audit_pdf_store import PeriodicAuditPdfStore
from src.services.periodic_audit_pdf_reconciliation_service import PeriodicAuditPdfReconciliationService
from src.services.prestacao_contas_intelligence_service import PrestacaoContasIntelligenceService
from src.services.periodic_audit_dossier_service import PeriodicAuditDossierService
from src.services.periodic_audit_dossier_archive_service import PeriodicAuditDossierArchiveService
from src.services.periodic_audit_dossier_backup_service import PeriodicAuditDossierBackupService


router = APIRouter(prefix="/api/v1/auditorias-periodicas", tags=["Auditorias periódicas"])
_store = PeriodicAuditCycleStore()
_runs = PeriodicAuditRunService()
_scheduler = PeriodicAuditSchedulerService(_store, _runs)
_pdfs = PeriodicAuditPdfStore()
_pdf_reconciliation = PeriodicAuditPdfReconciliationService()
_prestacao = PrestacaoContasIntelligenceService()
_dossiers = PeriodicAuditDossierService()
_dossier_archive = PeriodicAuditDossierArchiveService(generator=_dossiers)
_dossier_backup = PeriodicAuditDossierBackupService(
    backup_root=os.getenv(
        "PERIODIC_AUDIT_DOSSIER_BACKUP_DIR",
        ".runtime/periodic_audits/dossier_backups",
    ),
    retention_days=int(os.getenv("PERIODIC_AUDIT_DOSSIER_RETENTION_DAYS", "2555")),
)


class CreatePeriodicAuditBody(BaseModel):
    empresaCodigo: str = Field(min_length=1)
    centroCusto: Literal["PISTA", "CONVENIENCIA", "LOJA"]
    periodicidadeDias: int = Field(ge=1, le=90)
    responsavel: str = Field(min_length=2)
    dataCorte: date


class SetPeriodicAuditStatusBody(BaseModel):
    ativo: bool


class OpenAuditRunBody(BaseModel):
    dataInicial: str
    dataFinal: str


class ResolveAuditItemBody(BaseModel):
    evidencia: str = Field(min_length=3)


class ApproveAuditRunBody(BaseModel):
    confirmacao: bool = True


class ReviewPdfReconciliationBody(BaseModel):
    justificativa: str = Field(min_length=3)


def _serialize(item) -> dict:
    payload = item.model_dump(mode="json", by_alias=True)
    payload["proximaAuditoria"] = item.proxima_auditoria().isoformat()
    payload["statusAgenda"] = item.status()
    return payload


@router.get("/ciclos")
async def list_periodic_audit_cycles() -> dict:
    return {"success": True, "data": [_serialize(item) for item in _store.list_all()], "error": None}


@router.post("/ciclos")
async def create_periodic_audit_cycle(
    body: CreatePeriodicAuditBody,
    current_user: dict = Depends(require_roles("director", "audit", "admin", "owner")),
) -> dict:
    try:
        item = _store.create(
            body.empresaCodigo, body.centroCusto, body.periodicidadeDias,
            body.responsavel, body.dataCorte,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"success": True, "data": _serialize(item), "error": None}


@router.patch("/ciclos/{cycle_id}")
async def set_periodic_audit_cycle_status(
    cycle_id: str,
    body: SetPeriodicAuditStatusBody,
    current_user: dict = Depends(require_roles("director", "audit", "admin", "owner")),
) -> dict:
    item = _store.set_active(cycle_id, body.ativo)
    if not item:
        raise HTTPException(status_code=404, detail="Ciclo de auditoria não encontrado")
    return {"success": True, "data": _serialize(item), "error": None}


@router.post("/ciclos/{cycle_id}/abrir")
async def open_periodic_audit_run(
    cycle_id: str,
    body: OpenAuditRunBody,
    current_user: dict = Depends(require_roles("director", "audit", "admin", "owner")),
) -> dict:
    cycle = next((item for item in _store.list_all() if item.id == cycle_id), None)
    if not cycle:
        raise HTTPException(status_code=404, detail="Rotina de auditoria não encontrada")
    if not cycle.ativo:
        raise HTTPException(status_code=409, detail="Rotina de auditoria está pausada")
    try:
        run = await _runs.open_run(cycle.id, cycle.empresa_codigo, cycle.centro_custo, body.dataInicial, body.dataFinal)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"success": True, "data": run.model_dump(mode="json"), "error": None}


@router.get("/execucoes/{run_id}")
async def get_periodic_audit_run(run_id: str) -> dict:
    run = _runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Ciclo de auditoria não encontrado")
    return {"success": True, "data": run.model_dump(mode="json"), "error": None}


@router.get("/execucoes")
async def list_periodic_audit_runs() -> dict:
    return {
        "success": True,
        "data": [run.model_dump(mode="json") for run in _runs.list_all()],
        "error": None,
    }


@router.post("/execucoes/{run_id}/pdf")
async def upload_periodic_audit_pdf(
    run_id: str,
    request: Request,
    current_user: dict = Depends(require_roles("director", "audit", "admin", "owner")),
) -> dict:
    if not _runs.get(run_id):
        raise HTTPException(status_code=404, detail="Ciclo de auditoria não encontrado")
    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    if content_type != "application/pdf":
        raise HTTPException(status_code=415, detail="Envie um arquivo application/pdf")
    content = await request.body()
    actor = str(current_user.get("sub") or "authenticated-user")
    try:
        record = _pdfs.save(
            run_id,
            content,
            request.headers.get("x-filename", "prestacao-contas.pdf"),
            actor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"success": True, "data": record, "error": None}


@router.get("/execucoes/{run_id}/pdf")
async def list_periodic_audit_pdfs(run_id: str) -> dict:
    if not _runs.get(run_id):
        raise HTTPException(status_code=404, detail="Ciclo de auditoria não encontrado")
    return {"success": True, "data": _pdfs.list(run_id), "error": None}


@router.post("/execucoes/{run_id}/pdf/{evidence_id}/reconciliar")
async def reconcile_periodic_audit_pdf(
    run_id: str,
    evidence_id: str,
    current_user: dict = Depends(require_roles("director", "audit", "admin", "owner")),
) -> dict:
    run = _runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Ciclo de auditoria não encontrado")
    content = _pdfs.read(run_id, evidence_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Evidência PDF não encontrada")
    try:
        extracted = _pdf_reconciliation.extract(content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    response = await _prestacao.build(
        run.data_inicial,
        run.data_final,
        run.empresa_codigo,
        run.centro_custo,
    )
    if not response.success or not response.data:
        raise HTTPException(status_code=502, detail=response.error or "Falha na API WebPosto")
    result = _pdf_reconciliation.reconcile(extracted, response.data)
    metadata = next(
        (item for item in _pdfs.list(run_id) if item.get("id") == evidence_id),
        None,
    )
    actor = str(current_user.get("sub") or "authenticated-user")
    updated = _runs.record_reconciliation(
        run_id,
        evidence_id,
        str((metadata or {}).get("sha256") or ""),
        result,
        actor,
    )
    return {
        "success": True,
        "data": {
            "extracted": extracted,
            "reconciliation": result,
            "run": updated.model_dump(mode="json") if updated else None,
        },
        "error": None,
    }


@router.post("/execucoes/{run_id}/pdf/{evidence_id}/revisar")
async def review_periodic_audit_pdf_reconciliation(
    run_id: str,
    evidence_id: str,
    body: ReviewPdfReconciliationBody,
    current_user: dict = Depends(require_roles("director", "audit", "admin", "owner")),
) -> dict:
    actor = str(current_user.get("sub") or "authenticated-user")
    try:
        run = _runs.review_reconciliation(
            run_id, evidence_id, actor, body.justificativa
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not run:
        raise HTTPException(status_code=404, detail="Conciliação PDF não encontrada")
    return {"success": True, "data": run.model_dump(mode="json"), "error": None}


@router.post("/execucoes/{run_id}/itens/{item_id}/resolver")
async def resolve_periodic_audit_item(
    run_id: str,
    item_id: str,
    body: ResolveAuditItemBody,
    current_user: dict = Depends(require_roles("director", "audit", "admin", "owner")),
) -> dict:
    actor = str(current_user.get("sub") or "authenticated-user")
    run = _runs.resolve(run_id, item_id, actor, body.evidencia)
    if not run:
        raise HTTPException(status_code=404, detail="Ciclo ou item de checklist não encontrado")
    return {"success": True, "data": run.model_dump(mode="json"), "error": None}


@router.post("/execucoes/{run_id}/aprovar")
async def approve_periodic_audit_run(
    run_id: str,
    body: ApproveAuditRunBody,
    current_user: dict = Depends(require_roles("director", "audit", "admin", "owner")),
) -> dict:
    actor = str(current_user.get("sub") or "authenticated-user")
    try:
        run = _runs.approve(run_id, actor)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not run:
        raise HTTPException(status_code=404, detail="Ciclo de auditoria não encontrado")
    return {"success": True, "data": run.model_dump(mode="json"), "error": None}


@router.get("/execucoes/{run_id}/dossie.pdf")
async def download_periodic_audit_dossier(
    run_id: str,
    current_user: dict = Depends(require_roles("director", "audit", "admin", "owner")),
) -> Response:
    run = _runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Ciclo de auditoria não encontrado")
    try:
        content, manifest = _dossier_archive.get_or_create(run)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="dossie-auditoria-{run_id}.pdf"',
            "Cache-Control": "private, no-store",
            "X-Dossier-SHA256": manifest["sha256"],
        },
    )


@router.get("/execucoes/{run_id}/dossie-integridade")
async def verify_periodic_audit_dossier(
    run_id: str,
    current_user: dict = Depends(require_roles("director", "audit", "admin", "owner")),
) -> dict:
    if not _runs.get(run_id):
        raise HTTPException(status_code=404, detail="Ciclo de auditoria não encontrado")
    result = _dossier_archive.verify(run_id)
    status = 200 if result["integrity"] != "FAILED" else 409
    if status == 409:
        raise HTTPException(status_code=status, detail=result)
    return {"success": True, "data": result, "error": None}


@router.post("/execucoes/{run_id}/dossie-backup")
async def backup_periodic_audit_dossier(
    run_id: str,
    current_user: dict = Depends(require_roles("audit", "admin", "owner")),
) -> dict:
    run = _runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Ciclo de auditoria não encontrado")
    actor = str(current_user.get("sub") or "authenticated-user")
    try:
        _dossier_archive.get_or_create(run)
        result = _dossier_backup.backup(run_id, actor)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"success": True, "data": result, "error": None}


@router.get("/execucoes/{run_id}/dossie-backup-integridade")
async def verify_periodic_audit_dossier_backup(
    run_id: str,
    current_user: dict = Depends(require_roles("audit", "admin", "owner")),
) -> dict:
    if not _runs.get(run_id):
        raise HTTPException(status_code=404, detail="Ciclo de auditoria não encontrado")
    result = _dossier_backup.verify_backup(run_id)
    if result["integrity"] == "FAILED":
        raise HTTPException(status_code=409, detail=result)
    return {"success": True, "data": result, "error": None}


@router.post("/execucoes/{run_id}/dossie-restaurar")
async def restore_periodic_audit_dossier(
    run_id: str,
    current_user: dict = Depends(require_roles("admin", "owner")),
) -> dict:
    if not _runs.get(run_id):
        raise HTTPException(status_code=404, detail="Ciclo de auditoria não encontrado")
    actor = str(current_user.get("sub") or "authenticated-user")
    try:
        result = _dossier_backup.restore(run_id, actor)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"success": True, "data": result, "error": None}


@router.post("/executar-vencidos")
async def run_due_periodic_audits(
    data: str | None = None,
    current_user: dict = Depends(require_roles("operations", "director", "audit", "admin", "owner")),
) -> dict:
    try:
        result = await _scheduler.run_due(data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Data inválida") from exc
    return {"success": True, "data": result, "error": None}
