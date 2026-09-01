"""Sprint 60 — Painel de Aferição de Dados Reais."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query

from src.interfaces.http.authz import require_roles
from src.services.data_audit_service import DataAuditService
from src.utils.filial_normalizer import resolve_empresa_codigo
from src.services.webposto.offline_mode import (
    WebPostoOfflineBlocked,
    annotate_offline_success,
    classify_local_source,
    offline_unavailable_response,
    webposto_offline_mode,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/executive",
    tags=["Executive Data Audit S60"],
)

_service = DataAuditService()


@router.get("/data-audit")
async def get_data_audit(
    dataInicial: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: Optional[int] = Query(None),
    regime: Optional[str] = Query(
        "competencia",
        description="competencia (data da nota) | caixa (data do pagamento/boleto)",
    ),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
) -> dict:
    """Homologação diária: faturamento, volume, abastecimentos, tanques e DRE de despesas."""
    try:
        empresa = resolve_empresa_codigo(empresaCodigo)
        result = await _service.build(dataInicial, dataFinal, empresa, regime=regime)
        dumped = result.model_dump()
        body = {
            "success": True,
            "data": dumped,
            "namespace": "executive",
        }
        if webposto_offline_mode():
            fonte = str((dumped or {}).get("fonte") or "cache_local")
            return annotate_offline_success(body, source=classify_local_source(fonte))
        return body
    except WebPostoOfflineBlocked:
        return offline_unavailable_response(route="/api/v1/executive/data-audit")
    except Exception as exc:
        if webposto_offline_mode():
            return offline_unavailable_response(route="/api/v1/executive/data-audit")
        logger.exception("data-audit falhou: %s", exc)
        return {
            "success": True,
            "data": {
                "periodo": {"inicio": dataInicial or "", "fim": dataFinal or ""},
                "filiais": [],
                "consolidado": {},
                "success": False,
                "mensagem": str(exc),
            },
            "fallback": True,
            "namespace": "executive",
        }


@router.get("/expenses/details")
async def get_expense_details(
    dataInicial: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataReferencia: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: Optional[int] = Query(None),
    categoriaPlanoContas: str = Query(
        ...,
        description="CPV | PESSOAL | ADMINISTRATIVA | OUTRAS (ou label amigável)",
    ),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
) -> dict:
    """Drill-down: lançamentos individuais de uma categoria do Plano de Contas."""
    start = dataInicial or dataReferencia
    end = dataFinal or dataReferencia or dataInicial
    try:
        result = await _service.get_expense_details(
            start, end, empresaCodigo, categoriaPlanoContas
        )
        return {
            "success": bool(result.success),
            "data": result.model_dump(),
            "namespace": "executive",
        }
    except Exception as exc:
        if webposto_offline_mode():
            return offline_unavailable_response(route="/api/v1/executive/expenses/details")
        logger.exception("expenses/details falhou: %s", exc)
        return {
            "success": False,
            "data": {
                "empresaCodigo": empresaCodigo,
                "categoria": categoriaPlanoContas,
                "subtotal": 0,
                "quantidade": 0,
                "itens": [],
                "success": False,
                "mensagem": str(exc),
            },
            "fallback": True,
            "namespace": "executive",
        }
