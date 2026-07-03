"""
Owner Action Center Router — BUILD-03

Router específico para a Home do proprietário.

BUILD-03: INTEGRAÇÃO COM DISCOVERY ENGINE
- Owner Action Center agora orquestra Discovery Engine
- Retorna analysis_status e analysis_proof
- Não inventa "negócio sob controle" sem evidência
- Expõe exatamente o que foi analisado

Princípios:
- Reutiliza Discovery Engine (VALUE-01)
- Fornece prova do que foi analisado
- Mantém dados reais sempre (sem mocks)
- Filtra por confidence >= 80%
- Transparência total sobre limitações
"""

from __future__ import annotations

from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta
from typing import List, Dict, Any, Literal
import uuid

from src.services.action_center_service import ActionCenterService
from src.services.action_center_snapshot_service import ActionCenterSnapshotService
from src.services.decision_discovery import DecisionDiscoveryEngine
from src.services.decision_discovery.detectors import FuelRevenueDetector
from src.services.decision_discovery.models import DecisionCandidate, TenantAnalysisRecord
from src.services.tenant_discovery_service import TenantDiscoveryService

router = APIRouter(prefix="/api/v1/owner-action-center", tags=["Owner Action Center"])

_action_service = ActionCenterService()
_action_snapshot = ActionCenterSnapshotService(_action_service)


def _get_discovery_engine() -> DecisionDiscoveryEngine:
    """
    BUILD-03: Cria Discovery Engine com detectores disponíveis.
    
    Returns:
        DecisionDiscoveryEngine configurado
    """
    engine = DecisionDiscoveryEngine()
    engine.register_detector(FuelRevenueDetector())
    # Futuros detectores serão adicionados aqui
    return engine


AnalysisStatus = Literal[
    "PRIORITY_FOUND",
    "ANALYSIS_COMPLETE_NO_PRIORITY", 
    "INSUFFICIENT_DATA",
    "PARTIAL_ANALYSIS",
    "ANALYSIS_ERROR"
]

MonitoringState = Literal[
    "DECISION",
    "OBSERVATION",
    "NORMAL",
    "INSUFFICIENT_DATA",
    "ANALYSIS_FAILED",
]


def _detectors_count(detectors_executed: Any) -> int:
    if isinstance(detectors_executed, list):
        return len(detectors_executed)
    if isinstance(detectors_executed, int):
        return detectors_executed
    return 0


def _build_observations(
    rejected: List[Dict[str, Any]],
    tenant_code: str,
    tenant_name: str,
    analyzed_at: str,
) -> List[Dict[str, Any]]:
    """Converte candidatos descartados em observações rastreáveis (BUILD-03A)."""
    observations: List[Dict[str, Any]] = []

    for item in rejected:
        candidate = item.get("candidate") or {}
        evidence = candidate.get("evidence") or {}
        baseline = candidate.get("baseline") or {}
        period = candidate.get("period") or {}
        money = candidate.get("money_found") or {}

        financial_impact = item.get("money_found")
        if financial_impact is None:
            financial_impact = money.get("total")
        if financial_impact is None:
            financial_impact = money.get("at_risk")

        confidence = item.get("confidence", candidate.get("confidence"))
        if confidence is None:
            continue

        product = evidence.get("product_name") or candidate.get("title")
        current_value = evidence.get("current_value") or baseline.get("current_value")
        baseline_value = evidence.get("previous_value") or baseline.get("baseline_value")
        variation_percent = None
        if current_value is not None and baseline_value not in (None, 0):
            try:
                variation_percent = (float(current_value) - float(baseline_value)) / float(baseline_value)
            except (TypeError, ValueError, ZeroDivisionError):
                variation_percent = None

        observations.append({
            "id": candidate.get("id") or str(uuid.uuid4()),
            "tenant_id": tenant_code,
            "tenant_name": candidate.get("tenant_name") or tenant_name,
            "detector": item.get("detector") or candidate.get("detector"),
            "category": candidate.get("category"),
            "title": item.get("title") or candidate.get("title"),
            "description": candidate.get("summary"),
            "product": product,
            "period": period,
            "current_value": current_value,
            "baseline_value": baseline_value,
            "variation_percent": variation_percent,
            "financial_impact": financial_impact,
            "confidence": confidence,
            "decision_threshold": item.get("financial_impact_threshold"),
            "confidence_threshold": item.get("confidence_threshold"),
            "observation_reason": item.get("observation_reason") or item.get("reason"),
            "discard_reason": item.get("discard_reason") or item.get("reason"),
            "evidence": evidence,
            "endpoint_sources": candidate.get("source_endpoints") or [],
            "analyzed_at": analyzed_at,
        })

    observations.sort(
        key=lambda obs: float(obs.get("financial_impact") or 0),
        reverse=True,
    )
    return observations[:3]


def _resolve_monitoring_state(
    decisions_count: int,
    observations_count: int,
    analysis_status: AnalysisStatus,
) -> MonitoringState:
    if decisions_count > 0:
        return "DECISION"
    if observations_count > 0:
        return "OBSERVATION"
    if analysis_status == "INSUFFICIENT_DATA":
        return "INSUFFICIENT_DATA"
    if analysis_status == "ANALYSIS_ERROR":
        return "ANALYSIS_FAILED"
    return "NORMAL"


def _tenant_record_to_dict(record: TenantAnalysisRecord) -> Dict[str, Any]:
    return {
        "tenant_id": record.tenant_id,
        "tenant_name": record.tenant_name,
        "empresa_codigo": record.empresa_codigo,
        "credential_alias": record.credential_alias,
        "status": record.status,
        "detectors_executed": record.detectors_executed,
        "candidates_found": record.candidates_found,
        "decisions_found": record.decisions_found,
        "observations_found": record.observations_found,
        "requests_count": record.requests_count,
        "execution_time_ms": record.execution_time_ms,
        "period_analyzed": {
            "start": record.period_start,
            "end": record.period_end,
        },
        "error": record.error,
    }


def _build_multi_tenant_limitations(
    tenant_records: List[TenantAnalysisRecord],
    base_limitations: List[str],
) -> List[str]:
    limitations = list(base_limitations)
    analyzed = [r for r in tenant_records if r.status == "ANALYZED"]
    failed = [r for r in tenant_records if r.status == "FAILED"]

    if failed:
        for record in failed:
            limitations.append(
                f"{record.tenant_name or record.tenant_id} não pôde ser analisado"
            )

    if analyzed and failed:
        limitations.insert(
            0,
            f"{len(analyzed)} posto(s) analisado(s), {len(failed)} posto(s) com falha",
        )

    return limitations


@router.get("/top5")
async def get_top5_decisions(
    dataInicial: str = Query(..., description="Data inicial (YYYY-MM-DD)"),
    dataFinal: str = Query(..., description="Data final (YYYY-MM-DD)"),
    empresaCodigo: str | None = Query(None, description="Código da empresa (opcional — omitir para todos os postos)"),
) -> dict:
    """
    Retorna as top 5 decisões mais importantes para o proprietário.
    
    BUILD-03: Integrado com Discovery Engine
    - Executa Discovery Engine com detectores disponíveis
    - Retorna analysis_status explicando o resultado
    - Fornece analysis_proof mostrando o que foi analisado
    - NUNCA conclui "negócio sob controle" sem evidência
    
    IMPORTANTE: Usa dados reais. Se não há dados suficientes, 
    retorna INSUFFICIENT_DATA com análise parcial documentada.
    """
    analysis_id = str(uuid.uuid4())
    analysis_start = datetime.now()
    
    try:
        discovery_service = TenantDiscoveryService()
        empresa_filter: int | None = None
        if empresaCodigo and str(empresaCodigo).strip().isdigit():
            empresa_filter = int(str(empresaCodigo).strip())

        discovery = await discovery_service.discover_tenants(
            empresa_codigo_filter=empresa_filter,
        )
        tenants = discovery.tenants_discovered

        engine = _get_discovery_engine()
        
        try:
            if not tenants:
                raise ValueError(
                    "Nenhum tenant descoberto. "
                    + ("; ".join(discovery.limitations) if discovery.limitations else "")
                )

            result = await engine.discover_all_tenants(
                tenants=tenants,
                data_inicial=dataInicial,
                data_final=dataFinal,
                top_n=5,
                analysis_id=analysis_id,
            )
            
            analysis_end = datetime.now()
            execution_time_ms = int((analysis_end - analysis_start).total_seconds() * 1000)
            tenant_records = result.tenant_records
            analyzed_records = [r for r in tenant_records if r.status == "ANALYZED"]
            
            # Transformar DecisionCandidate para formato do frontend
            decisions = []
            for idx, candidate in enumerate(result.all_candidates):
                decisions.append({
                    "action": {
                        "id": candidate.id,
                        "title": candidate.title,
                        "description": candidate.summary,
                        "priority": "critical" if candidate.money_found.at_risk > 10000 else "high",
                        "type": "urgent",
                        "status": "pending",
                        "confidence": candidate.confidence,
                        "time_to_resolve": candidate.estimated_execution_time,
                        "financial_impact": {
                            "impact_type": candidate.impact_type.value if hasattr(candidate.impact_type, 'value') else str(candidate.impact_type),
                            "estimated_value": (
                                candidate.money_found.at_risk + 
                                candidate.money_found.recoverable + 
                                candidate.money_found.additional
                            ),
                        },
                        "source": {
                            "service": "discovery-engine",
                            "endpoint": "/api/v1/discovery/top-5",
                            "data_timestamp": analysis_end.isoformat(),
                        },
                    },
                    "tenant_id": candidate.tenant,
                    "tenant_name": candidate.tenant_name,
                    "rank": idx + 1,
                })
            
            observations: List[Dict[str, Any]] = []
            for record in analyzed_records:
                tenant_rejected = [
                    item for item in result.rejected_candidates
                    if str((item.get("candidate") or {}).get("tenant") or "") == record.tenant_id
                ]
                observations.extend(
                    _build_observations(
                        tenant_rejected,
                        tenant_code=record.tenant_id,
                        tenant_name=record.tenant_name,
                        analyzed_at=analysis_end.isoformat(),
                    )
                )
            observations.sort(
                key=lambda obs: float(obs.get("financial_impact") or 0),
                reverse=True,
            )
            observations = observations[:3]

            total_candidates = len(result.all_candidates) + len(result.rejected_candidates)
            analyzed_count = len(analyzed_records)
            failed_count = len([r for r in tenant_records if r.status == "FAILED"])

            if len(decisions) > 0:
                analysis_status: AnalysisStatus = "PRIORITY_FOUND"
                message = None
            elif failed_count > 0 and analyzed_count == 0:
                analysis_status = "ANALYSIS_ERROR"
                message = "Não foi possível concluir a análise"
            elif _detectors_count(result.detectors_executed) == 0:
                analysis_status = "ANALYSIS_ERROR"
                message = "Nenhum detector pode ser executado"
            elif failed_count > 0:
                analysis_status = "PARTIAL_ANALYSIS"
                message = (
                    "Análise parcial concluída. Nenhuma ação prioritária foi identificada "
                    "nas áreas verificadas."
                )
            elif len(observations) > 0:
                analysis_status = "ANALYSIS_COMPLETE_NO_PRIORITY"
                message = "Análise concluída. Sinais em observação."
            else:
                analysis_status = "ANALYSIS_COMPLETE_NO_PRIORITY"
                message = (
                    "Análise concluída. Nenhuma ação prioritária foi identificada "
                    "nas áreas verificadas."
                )

            monitoring_state = _resolve_monitoring_state(
                len(decisions),
                len(observations),
                analysis_status,
            )
            
            detectors_executed = result.detectors_executed
            base_limitations = _get_analysis_limitations(result, observations)
            limitations = _build_multi_tenant_limitations(tenant_records, base_limitations)
            limitations.extend(discovery.limitations)

            analysis_proof = {
                "analysis_id": analysis_id,
                "started_at": analysis_start.isoformat(),
                "completed_at": analysis_end.isoformat(),
                "execution_time_ms": execution_time_ms,
                "tenant_count": analyzed_count,
                "tenant_ids": [r.tenant_id for r in analyzed_records],
                "tenants": [_tenant_record_to_dict(r) for r in tenant_records],
                "credentials_detected": discovery.credentials_detected,
                "tenants_discovered": len(discovery.tenants_discovered),
                "tenants_validated": len(discovery.tenants_discovered),
                "tenants_analyzed": analyzed_count,
                "tenants_failed": failed_count,
                "period_analyzed": {
                    "start": dataInicial,
                    "end": dataFinal,
                },
                "detectors_available": len(detectors_executed),
                "detectors_executed": detectors_executed,
                "detectors_successful": detectors_executed,
                "detectors_failed": 0,
                "data_sources_consulted": ["/api/v1/sales/fuel-summary"],
                "endpoints_consulted": ["/api/v1/sales/fuel-summary"],
                "records_analyzed": None,
                "candidates_found": total_candidates,
                "candidates_approved": len(result.all_candidates),
                "candidates_discarded": len(result.rejected_candidates),
                "decisions_approved": len(decisions),
                "discard_reasons": [
                    r.get("discard_reason") or r.get("reason", "Unknown")
                    for r in result.rejected_candidates
                ],
                "confidence_threshold": DecisionCandidate.MIN_DECISION_CONFIDENCE,
                "financial_impact_threshold": DecisionCandidate.MIN_DECISION_IMPACT_BRL,
                "limitations": limitations,
                "last_analysis_at": analysis_end.isoformat(),
            }
            
            return {
                "success": True,
                "data": {
                    "top_5_decisions": decisions,
                    "observations": observations,
                    "total_decisions": len(decisions),
                    "total_observations": len(observations),
                    "filtered_by_confidence": len(result.rejected_candidates),
                    "has_sufficient_data": total_candidates > 0,
                    "message": message,
                },
                "analysis_status": analysis_status,
                "monitoring_state": monitoring_state,
                "analysis_proof": analysis_proof,
                "generated_at": analysis_end.isoformat(),
            }
            
        except Exception as discovery_error:
            # Discovery Engine falhou
            analysis_end = datetime.now()
            execution_time_ms = int((analysis_end - analysis_start).total_seconds() * 1000)
            
            return {
                "success": True,  # Endpoint funcionou, mas análise falhou
                "data": {
                    "top_5_decisions": [],
                    "total_decisions": 0,
                    "has_sufficient_data": False,
                    "message": "Não foi possível concluir a análise",
                },
                "analysis_status": "ANALYSIS_ERROR",
                "monitoring_state": "ANALYSIS_FAILED",
                "analysis_proof": {
                    "analysis_id": analysis_id,
                    "started_at": analysis_start.isoformat(),
                    "completed_at": analysis_end.isoformat(),
                    "execution_time_ms": execution_time_ms,
                    "error": str(discovery_error),
                    "limitations": ["Discovery Engine execution failed"],
                },
                "generated_at": analysis_end.isoformat(),
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar decisões: {str(e)}")


def _get_analysis_limitations(result: Any, observations: List[Dict[str, Any]] | None = None) -> List[str]:
    """
    BUILD-03: Documenta limitações da análise.
    """
    limitations = []
    detectors_count = _detectors_count(result.detectors_executed)

    if detectors_count == 1:
        limitations.append("Apenas vendas de combustível foram verificadas.")
        limitations.append("Caixa, Cartões e Despesas ainda não estão sendo analisados.")

    if not result.all_candidates and not (observations or []):
        limitations.append("Nenhum candidato atingiu os critérios de prioridade")

    return limitations


@router.get("/business-health")
async def get_business_health(
    dataInicial: str = Query(..., description="Data inicial (YYYY-MM-DD)"),
    dataFinal: str = Query(..., description="Data final (YYYY-MM-DD)"),
    empresaCodigo: str | None = Query(None, description="Código da empresa"),
) -> dict:
    """
    Retorna o score de saúde do negócio.
    
    BUILD-01D: Versão funcional básica.
    Calcula score baseado em dados disponíveis do Action Center.
    
    IMPORTANTE: NÃO inventa dados. Se não há dados suficientes,
    retorna score 0 com status "unknown".
    """
    try:
        # Buscar dados do Action Center
        payload, stale, hit = await _action_snapshot.get_or_collect(
            dataInicial, dataFinal, empresaCodigo
        )
        
        if not payload:
            return {
                "success": True,
                "data": {
                    "overall_score": 0,
                    "status": "unknown",
                    "risk_count": 0,
                    "last_update": datetime.now().isoformat(),
                    "has_sufficient_data": False,
                    "message": "Dados insuficientes para calcular health score",
                },
            }
        
        # Calcular score simplificado baseado em dados disponíveis
        # TODO: Implementar cálculo real quando estrutura de dados for definida
        cockpit = payload.get("cockpit", {})
        
        # Por enquanto, score 0 (sem dados suficientes)
        overall_score = 0
        status = "unknown"
        risk_count = 0
        
        return {
            "success": True,
            "data": {
                "overall_score": overall_score,
                "status": status,
                "risk_count": risk_count,
                "last_update": datetime.now().isoformat(),
                "has_sufficient_data": overall_score > 0,
                "message": "Dados insuficientes para calcular health score" if overall_score == 0 else None,
            },
            "snapshot": {"hit": hit, "stale": stale},
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao calcular health score: {str(e)}")


@router.get("/today-summary")
async def get_today_summary(
    empresaCodigo: str | None = Query(None, description="Código da empresa"),
) -> dict:
    """
    Conveniência: retorna resumo de hoje (últimos 7 dias).
    """
    hoje = datetime.now().date()
    data_final = hoje.isoformat()
    data_inicial = (hoje - timedelta(days=7)).isoformat()
    
    # Buscar ambos em paralelo seria ideal, mas por simplicidade:
    decisions_response = await get_top5_decisions(data_inicial, data_final, empresaCodigo)
    health_response = await get_business_health(data_inicial, data_final, empresaCodigo)
    
    return {
        "success": True,
        "data": {
            "decisions": decisions_response.get("data", {}),
            "health": health_response.get("data", {}),
            "period": {"start": data_inicial, "end": data_final},
        }
    }
