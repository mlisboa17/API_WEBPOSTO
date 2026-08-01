"""Endpoints de parâmetros dinâmicos da auditoria anti-fraude."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from src.services.fraud_audit_settings_service import (
    AuditFraudSettingsUpdate,
    get_settings,
    save_settings,
)

router = APIRouter(
    prefix="/api/v1/executive/audit",
    tags=["Executive Audit Settings"],
)


@router.get("/settings")
async def get_audit_settings(
    empresaId: int = Query(0, description="0 = rede / padrão"),
) -> dict[str, Any]:
    dto = await get_settings(empresa_id=empresaId)
    return {
        "success": True,
        "synthetic": False,
        "data": dto.model_dump(),
    }


@router.put("/settings")
async def put_audit_settings(body: AuditFraudSettingsUpdate) -> dict[str, Any]:
    dto = await save_settings(body)
    return {
        "success": True,
        "synthetic": False,
        "data": dto.model_dump(),
        "message": "Parâmetros salvos — recarregue a aba Anti-Fraude para recalcular.",
    }
