"""Rush Intelligence V3 — Mapa de Calor Operacional.

GET  /api/v1/executive/pista-rush-heatmap
POST /api/v1/executive/pista-interventions
GET  /api/v1/executive/pista-interventions
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from fastapi import APIRouter, Body, Query
from pydantic import BaseModel, Field

from src.services.rush_heatmap_engine import (
    build_rush_heatmap,
    list_interventions,
    register_intervention,
)
from src.utils.filial_normalizer import resolve_empresa_codigo

LOGGER = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/executive",
    tags=["Executive Rush Heatmap"],
)

_ISO_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2})?)?$"
)


def _compose_iso(
    data: str | None,
    hora: str | None,
    *,
    end_of_day: bool = False,
) -> str | None:
    """Combina data + hora ou aceita ISO datetime-local."""
    if not data:
        return None
    text = data.strip()
    if "T" in text or " " in text:
        # já veio com hora (datetime-local / ISO)
        if len(text) == 16:  # YYYY-MM-DDTHH:mm
            return f"{text}:00"
        return text.replace(" ", "T", 1)
    if not _ISO_RE.match(text) and not re.match(r"^\d{4}-\d{2}-\d{2}$", text):
        return text
    h = (hora or "").strip()
    if h:
        if len(h) == 5:
            h = f"{h}:00"
        return f"{text}T{h}"
    return f"{text}T{'23:59:59' if end_of_day else '00:00:00'}"


class InterventionBody(BaseModel):
    empresa_codigo: Optional[int] = None
    unidade_id: Optional[int] = None
    tipo: str = "MANUAL"
    suspeita_type: Optional[str] = None
    subject_id: Optional[str] = None
    acao: str = ""
    operador: str = "diretor"
    metrics_baseline: dict[str, Any] = Field(default_factory=dict)


@router.get("/pista-rush-heatmap")
async def get_pista_rush_heatmap(
    empresaCodigo: Optional[int] = Query(None),
    filial_id: Optional[int] = Query(None),
    dataInicial: Optional[str] = Query(
        None, description="YYYY-MM-DD ou ISO 2026-08-01T17:00"
    ),
    dataFinal: Optional[str] = Query(None),
    horaInicial: Optional[str] = Query(None, description="HH:mm"),
    horaFinal: Optional[str] = Query(None, description="HH:mm"),
    inicio: Optional[str] = Query(None, description="Alias ISO início"),
    fim: Optional[str] = Query(None, description="Alias ISO fim"),
) -> dict:
    empresa = resolve_empresa_codigo(
        filial_id if filial_id is not None else empresaCodigo
    )
    periodo_inicio = inicio or _compose_iso(dataInicial, horaInicial, end_of_day=False)
    periodo_fim = fim or _compose_iso(dataFinal, horaFinal, end_of_day=True)
    try:
        data = build_rush_heatmap(
            empresa_codigo=empresa,
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
        )
        return {
            "success": True,
            "data": data,
            "namespace": "executive",
            "fromCache": True,
            "latencyMs": data.get("latency_ms"),
        }
    except Exception as exc:
        LOGGER.exception("pista-rush-heatmap falhou: %s", exc)
        return {
            "success": False,
            "data": {
                "success": False,
                "posts": [],
                "intelligence_cards": [],
                "mensagem": str(exc),
            },
            "namespace": "executive",
        }


@router.post("/pista-interventions")
async def post_pista_intervention(body: InterventionBody = Body(...)) -> dict:
    record = register_intervention(body.model_dump())
    return {"success": True, "data": record, "namespace": "executive"}


@router.get("/pista-interventions")
async def get_pista_interventions(
    empresaCodigo: Optional[int] = Query(None),
) -> dict:
    emp = resolve_empresa_codigo(empresaCodigo)
    return {
        "success": True,
        "data": {"items": list_interventions(emp)},
        "namespace": "executive",
    }
