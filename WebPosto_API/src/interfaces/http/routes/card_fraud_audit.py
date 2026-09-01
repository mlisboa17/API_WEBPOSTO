"""Rota Anti-Fraude — audita baixados reais do período (WebPosto) + filtros em memória.

GET /api/v1/executive/audit/card-fraud
D0 pode usar cache RAM do PistaSyncWorker; histórico/multi-dia chama FraudDetectionEngine.auditar_periodo.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from fastapi import APIRouter, Query

from src.services.fraud_detection_engine import (
    filter_ocorrencias_ram,
    get_fraud_detection_engine,
    list_frentistas_disponiveis,
)
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
    filial_id: Optional[int] = Query(
        None, description="Alias de filial (aplica filial_normalizer)."
    ),
    frentista_id: Optional[int] = Query(None),
    frentista_nome: Optional[str] = Query(None),
    tipo_infracao: Optional[str] = Query(
        None,
        description="RETENCAO_CARTAO | EXCESSO_DESCONTO | AGRUPAMENTO_BICOS | ABUSO_CPF",
    ),
    tempo_retencao_min: Optional[int] = Query(None, ge=0, le=1440),
    forma_pagamento: Optional[str] = Query(
        None, description="CARTAO | PIX | DINHEIRO | FROTA"
    ),
    busca_texto: Optional[str] = Query(
        None, description="Busca por nome, cupom/venda, bico, CPF, NSU"
    ),
    limiarRetencaoMinutos: Optional[int] = Query(
        None,
        ge=1,
        le=180,
        description="Ignorado no GET (thresholds vêm do worker/settings).",
    ),
) -> dict:
    """Auditoria anti-fraude sobre baixados do período + filtros RAM opcionais."""
    _ = limiarRetencaoMinutos
    from datetime import date

    t_filter0 = time.perf_counter()
    end = dataFinal or date.today().isoformat()
    start = dataInicial or date.today().isoformat()
    # filial_id tem prioridade se informado; senão empresaCodigo
    empresa = resolve_empresa_codigo(
        filial_id if filial_id is not None else empresaCodigo
    )

    engine = get_fraud_detection_engine()

    # Período histórico / multi-dia → audita baixados reais WebPosto (não só RAM D0)
    try:
        result = await engine.auditar_periodo(
            data_inicial=start,
            data_final=end,
            empresa_codigo=empresa,
        )
    except Exception as exc:
        logger.exception("card-fraud auditar_periodo falhou: %s", exc)
        result = engine.response_from_ram(
            empresa_codigo=empresa,
            data_inicial=start,
            data_final=end,
        )

    total_antes = len(result.ocorrencias)
    frentistas = list_frentistas_disponiveis(result.ocorrencias)

    filtered = filter_ocorrencias_ram(
        result.ocorrencias,
        frentista_id=frentista_id,
        frentista_nome=frentista_nome,
        tipo_infracao=tipo_infracao,
        tempo_retencao_min=tempo_retencao_min,
        forma_pagamento=forma_pagamento,
        busca_texto=busca_texto,
    )
    filter_ms = round((time.perf_counter() - t_filter0) * 1000.0, 3)

    # Recalcula resumo só do recorte filtrado (KPIs da lista atual)
    if len(filtered) != total_antes:
        resumo = engine._build_resumo(filtered)
        result.ocorrencias = filtered
        result.resumo = resumo
        result.resumoExecutivo = resumo
    else:
        result.ocorrencias = filtered

    payload = result.model_dump()
    payload["totalOcorrencias"] = total_antes
    payload["totalFiltrado"] = len(filtered)
    payload["filterLatencyMs"] = filter_ms
    payload["frentistasDisponiveis"] = frentistas
    payload["filtrosAplicados"] = {
        "frentista_id": frentista_id,
        "frentista_nome": frentista_nome,
        "tipo_infracao": tipo_infracao,
        "tempo_retencao_min": tempo_retencao_min,
        "forma_pagamento": forma_pagamento,
        "busca_texto": busca_texto,
        "filial_id": filial_id,
        "empresaCodigo": empresa,
    }

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
        # Aliases snake_case do contrato de auditoria (Cartão Curinga)
        o["cartao_repetido"] = bool(o.get("cartaoRepetido"))
        o["quantidade_uso_cartao"] = int(o.get("quantidadeUsoCartao") or 0)
        o["quantidade_abastecimentos_cartao"] = int(
            o.get("quantidadeAbastecimentosCartao") or 0
        )

    if filter_ms >= 20:
        logger.warning(
            "card-fraud filterLatencyMs=%.1f (>=20ms) total=%s filtrado=%s",
            filter_ms,
            total_antes,
            len(filtered),
        )

    return {
        "success": True,
        "data": payload,
        "namespace": "executive",
        "synthetic": False,
        "fromCache": True,
        "latencyMs": payload.get("latencyMs", 0),
        "filterLatencyMs": filter_ms,
    }


@router.get("/pista-live")
async def get_pista_live_status(
    empresaCodigo: Optional[int] = Query(None),
    filial_id: Optional[int] = Query(
        None, description="Alias de filial (aplica filial_normalizer)."
    ),
) -> dict:
    """Painel Tático — status de bicos/ilhas (cache RAM, <50ms)."""
    from src.services.pista_live_status_service import build_pista_live_status

    empresa = resolve_empresa_codigo(
        filial_id if filial_id is not None else empresaCodigo
    )
    payload = build_pista_live_status(empresa_codigo=empresa)
    return {
        "success": True,
        "data": payload,
        "namespace": "executive",
        "fromCache": True,
    }
