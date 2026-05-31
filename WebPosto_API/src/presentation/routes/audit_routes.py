"""
Rotas de auditoria de caixa — HTTP 202 + BackgroundTasks.
"""

from __future__ import annotations

import os
import re
from datetime import date
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.domain.entities.audit import FaturamentoConsolidadoResponse, SubCentroCusto
from src.domain.exceptions.audit_fetch import AuditFetchError
from src.application.usecases.fetch_faturamento_subcentros import FetchFaturamentoSubCentrosUseCase
from src.infrastructure.background.audit_state import AuditJobStatus, load_job_state
from src.infrastructure.background.audit_tasks import create_audit_job, run_audit_job, _make_gateway

router = APIRouter(prefix="/v1/audit", tags=["audit"])


def _parse_filial_csv(filial: Optional[str]) -> list[int] | None:
    if not filial or not str(filial).strip():
        return None
    out: list[int] = []
    for part in str(filial).split(","):
        p = part.strip()
        if p.isdigit():
            out.append(int(p))
    return out or None


def _audit_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, AuditFetchError):
        detail = exc.args[0] if exc.args else "Dados indisponíveis"
        if exc.erros:
            detail = f"{detail} — {'; '.join(exc.erros)}"
        return HTTPException(status_code=502, detail=detail)
    return HTTPException(status_code=502, detail=str(exc)[:500])


class AuditProcessResponse(BaseModel):
    job_id: str
    status: str = "accepted"
    poll_url: str
    message: str = "Processamento de auditoria enfileirado"


@router.post("/process", status_code=202)
async def process_audit(
    background_tasks: BackgroundTasks,
    data_inicio: date = Query(..., description="YYYY-MM-DD"),
    data_fim: date = Query(..., description="YYYY-MM-DD"),
    sub_centro: SubCentroCusto = Query(SubCentroCusto.PISTA),
    posto_id: Optional[str] = Query(None, description="ID do posto (default: empresa da chave)"),
    filial: Optional[str] = Query(None, description="Códigos de filial separados por vírgula"),
):
    """
    Inicia reconciliação CaixaApurado × CaixaApresentado por sub-centro.
    Resposta imediata 202; resultado em GET /v1/audit/jobs/{job_id}.
    """
    if data_fim < data_inicio:
        raise HTTPException(400, "data_fim deve ser >= data_inicio")

    chave = (os.getenv("WEBPOSTO_API_KEY") or os.getenv("WEBPOSTO_CHAVE") or "").strip()
    if not chave or chave in ("sua_chave_api_rest_aqui", "SEU_TOKEN_AQUI"):
        raise HTTPException(401, "WEBPOSTO_API_KEY ausente no .env")

    pid = (posto_id or "default").strip()
    job_id = await create_audit_job(
        data_inicio,
        data_fim,
        sub_centro.value,
        posto_id=pid,
        filial=_parse_filial_csv(filial),
    )
    background_tasks.add_task(run_audit_job, job_id)

    return JSONResponse(
        status_code=202,
        content=AuditProcessResponse(
            job_id=job_id,
            poll_url=f"/v1/audit/jobs/{job_id}",
        ).model_dump(),
    )


@router.get("/faturamento", response_model=FaturamentoConsolidadoResponse)
async def get_faturamento_subcentros(
    data_inicio: date = Query(..., description="YYYY-MM-DD"),
    data_fim: date = Query(..., description="YYYY-MM-DD"),
    posto_id: Optional[str] = Query(None),
    filial: Optional[str] = Query(None, description="Códigos de filial separados por vírgula"),
):
    """
    Faturamento do período em R$ para PISTA, LOJA e FOOD (3 sub-centros operacionais).
    O posto pode ter 4 centros no ERP; o 4º não entra nesta consolidação.
    """
    if data_fim < data_inicio:
        raise HTTPException(400, "data_fim deve ser >= data_inicio")
    chave = (os.getenv("WEBPOSTO_API_KEY") or os.getenv("WEBPOSTO_CHAVE") or "").strip()
    if not chave:
        raise HTTPException(401, "WEBPOSTO_API_KEY ausente no .env")

    try:
        uc = FetchFaturamentoSubCentrosUseCase(_make_gateway())
        return await uc.execute(
            data_inicio,
            data_fim,
            posto_id=(posto_id or "default").strip(),
            filial=_parse_filial_csv(filial),
        )
    except AuditFetchError as exc:
        raise _audit_http_error(exc) from exc
    except Exception as exc:
        raise _audit_http_error(exc) from exc


@router.get("/jobs/{job_id}")
async def get_audit_job(job_id: str):
    state = await load_job_state(job_id)
    if not state:
        raise HTTPException(404, "Job de auditoria não encontrado")
    out = {
        "job_id": state.job_id,
        "status": state.status.value,
        "params": state.params,
    }
    if state.status == AuditJobStatus.DONE and state.result:
        out["result"] = state.result
    if state.error:
        out["error"] = state.error
    return out
