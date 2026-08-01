"""Sprint 60 — Painel de Aferição de Dados Reais."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query

from src.interfaces.http.authz import require_roles
from src.services.data_audit_service import DataAuditService

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
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
) -> dict:
    """Homologação diária: faturamento, volume, abastecimentos, tanques e DRE de despesas."""
    try:
        result = await _service.build(dataInicial, dataFinal, empresaCodigo)
        return {
            "success": True,
            "data": result.model_dump(),
            "namespace": "executive",
        }
    except Exception as exc:
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
