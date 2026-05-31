"""Processamento assíncrono de auditoria (BackgroundTasks / worker)."""

from __future__ import annotations

import logging
import uuid
from datetime import date

from src.application.usecases.reconcile_audit import ReconcileAuditUseCase
from src.infrastructure.background.audit_state import (
    AuditJobState,
    AuditJobStatus,
    load_job_state,
    save_job_state,
)
from src.infrastructure.clients.webposto_client import WebPostoAuditClient

logger = logging.getLogger(__name__)


def _make_gateway():
    from src.webposto import WebPostoClient, WebPostoConfig
    import os

    chave = (os.getenv("WEBPOSTO_API_KEY") or os.getenv("WEBPOSTO_CHAVE") or "").strip()
    base = os.getenv("WEBPOSTO_BASE_URL", "https://web.qualityautomacao.com.br").strip()
    if "qualityautomacao" in base.lower() and base.startswith("http://"):
        base = "https://web.qualityautomacao.com.br"
    client = WebPostoClient(WebPostoConfig(chave=chave, base_url=base, max_retries=2))
    return WebPostoAuditClient(client)


async def create_audit_job(
    data_inicio: date,
    data_fim: date,
    sub_centro: str,
    *,
    posto_id: str = "default",
    filial: list[int] | None = None,
) -> str:
    job_id = str(uuid.uuid4())
    state = AuditJobState(
        job_id=job_id,
        status=AuditJobStatus.PENDING,
        params={
            "data_inicio": data_inicio.isoformat(),
            "data_fim": data_fim.isoformat(),
            "sub_centro": sub_centro,
            "posto_id": posto_id,
            "filial": filial,
        },
    )
    await save_job_state(state)
    return job_id


async def run_audit_job(job_id: str) -> None:
    state = await load_job_state(job_id)
    if not state:
        logger.error("audit job %s não encontrado", job_id)
        return

    state.status = AuditJobStatus.RUNNING
    await save_job_state(state)

    try:
        p = state.params
        uc = ReconcileAuditUseCase(_make_gateway())
        session = await uc.execute(
            date.fromisoformat(p["data_inicio"]),
            date.fromisoformat(p["data_fim"]),
            p["sub_centro"],
            posto_id=p.get("posto_id", "default"),
            job_id=job_id,
            filial=p.get("filial"),
        )
        state.status = AuditJobStatus.DONE
        state.result = session.model_dump(mode="json")
        state.error = None
    except Exception as exc:
        logger.exception("audit job %s falhou", job_id)
        state.status = AuditJobStatus.FAILED
        state.error = str(exc)[:500]

    await save_job_state(state)
