"""Rota de Auditoria Anti-Fraude de Pista (Cartao/TEF) — engine dinâmica.

GET /api/v1/executive/audit/card-fraud
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Query

from src.services.fraud_detection_engine import get_fraud_detection_engine

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
        description="Override opcional do limiar de atenção (min). Null = usa settings salvos.",
    ),
) -> dict:
    """Auditoria avançada com thresholds dinâmicos (settings) + cache RAM."""
    from datetime import date, timedelta

    end = dataFinal or date.today().isoformat()
    start = dataInicial or date.today().isoformat()

    try:
        result = await get_fraud_detection_engine().auditar(
            data_inicial=start,
            data_final=end,
            empresa_codigo=empresaCodigo,
            limiar_override=limiarRetencaoMinutos,
        )
        payload = result.model_dump()
        # Alias dataHoraBaixa no legado (campo principal já existe)
        for o in payload.get("ocorrencias") or []:
            if not o.get("dataHoraBaixa") and o.get("horaBaixa"):
                o["dataHoraBaixa"] = o["horaBaixa"]
            # nivelRisco legado CRITICO/ATENCAO
            nivel = o.get("nivelRisco")
            if nivel == "ALTO":
                o["nivelRiscoLegado"] = "CRITICO"
            elif nivel == "MEDIO":
                o["nivelRiscoLegado"] = "ATENCAO"
            else:
                o["nivelRiscoLegado"] = "BAIXO"
        return {
            "success": True,
            "data": payload,
            "namespace": "executive",
            "synthetic": False,
        }
    except Exception as exc:
        logger.exception("audit/card-fraud falhou: %s", exc)
        return {
            "success": True,
            "data": {
                "success": False,
                "synthetic": False,
                "fonte": "FraudDetectionEngine",
                "endpoint": "/api/v1/abastecimentos/baixados",
                "periodo": {"inicio": start, "fim": end},
                "empresaCodigo": empresaCodigo,
                "resumo": {},
                "resumoExecutivo": {},
                "ocorrencias": [],
                "bannerAlerta": None,
                "observacoes": [str(exc)],
            },
            "synthetic": False,
            "namespace": "executive",
        }
