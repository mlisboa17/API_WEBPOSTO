"""Rota Anti-Fraude — leitura exclusiva do cache RAM (<50ms).

GET /api/v1/executive/audit/card-fraud
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Query

from src.services.fraud_detection_engine import get_fraud_detection_engine
from src.utils.filial_normalizer import resolve_empresa_codigo

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/executive/audit",
    tags=["Executive Card Fraud Audit"],
)


@router.get("/card-fraud")
async def get_card_fraud_audit(
    dataInicial: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: Optional[int] = Query(None),
    limiarRetencaoMinutos: Optional[int] = Query(
        None,
        ge=1,
        le=180,
        description="Ignorado no GET (thresholds vêm do worker/settings).",
    ),
) -> dict:
    """Auditoria anti-fraude — 100% memória RAM (PistaSyncWorker 30s)."""
    _ = limiarRetencaoMinutos
    from datetime import date

    end = dataFinal or date.today().isoformat()
    start = dataInicial or date.today().isoformat()
    empresa = resolve_empresa_codigo(empresaCodigo)

    engine = get_fraud_detection_engine()
    store = engine.get_store()

    # Warm-up em background se cache ainda vazio — nunca bloqueia o GET
    if store.result is None and not store.gerado_em:
        import asyncio

        async def _warm() -> None:
            try:
                await engine.refresh_from_pista()
            except Exception as exc:
                logger.warning("card-fraud warm-up falhou: %s", exc)

        try:
            asyncio.get_running_loop().create_task(_warm())
        except RuntimeError:
            pass

    result = engine.response_from_ram(
        empresa_codigo=empresa,
        data_inicial=start,
        data_final=end,
    )
    payload = result.model_dump()

    for o in payload.get("ocorrencias") or []:
        if not o.get("formaPagamento"):
            o["formaPagamento"] = o.get("meioPagamento") or "Cartão/TEF"
        if not o.get("dataHoraBaixa") and o.get("horaBaixa"):
            o["dataHoraBaixa"] = o["horaBaixa"]
        nivel = o.get("nivelRisco")
        if nivel == "ALTO":
            o["nivelRiscoLegado"] = "CRITICO"
        elif nivel == "DESCONTO":
            o["nivelRiscoLegado"] = "DESCONTO"
        elif nivel == "MEDIO":
            o["nivelRiscoLegado"] = "ATENCAO"
        else:
            o["nivelRiscoLegado"] = "BAIXO"
        if not o.get("dataHoraEmissaoCupom"):
            o["dataHoraEmissaoCupom"] = o.get("dataHoraBaixa") or o.get("horaBaixa") or ""

    return {
        "success": True,
        "data": payload,
        "namespace": "executive",
        "synthetic": False,
        "fromCache": True,
        "latencyMs": payload.get("latencyMs", 0),
    }
