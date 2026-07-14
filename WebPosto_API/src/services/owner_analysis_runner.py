"""Execução síncrona do Discovery Engine para Owner Action Center."""

from __future__ import annotations

import uuid
from typing import Any, List, Literal

from src.services.decision_discovery import DecisionDiscoveryEngine
from src.services.decision_discovery.detectors import (
    CardReceivableDetector,
    ExpenseDetector,
    FuelRevenueDetector,
    MarginDetector,
    SupplierInvoiceSpikeDetector,
)
from src.services.decision_discovery.models import DecisionCandidate, TenantAnalysisRecord
from src.services.owner_analysis_models import TenantProgressCallback
from src.services.tenant_discovery_service import TenantDiscoveryService, TenantDiscoveryResult
from src.utils.utc_datetime import utc_now, utc_now_iso

AnalysisStatus = Literal[
    "PRIORITY_FOUND",
    "ANALYSIS_COMPLETE_NO_PRIORITY",
    "INSUFFICIENT_DATA",
    "PARTIAL_ANALYSIS",
    "ANALYSIS_ERROR",
]

MonitoringState = Literal[
    "DECISION",
    "OBSERVATION",
    "NORMAL",
    "INSUFFICIENT_DATA",
    "ANALYSIS_FAILED",
]

def _get_discovery_engine() -> DecisionDiscoveryEngine:
    engine = DecisionDiscoveryEngine()
    engine.register_detector(FuelRevenueDetector())
    engine.register_detector(ExpenseDetector())
    engine.register_detector(CardReceivableDetector())
    engine.register_detector(MarginDetector())
    engine.register_detector(SupplierInvoiceSpikeDetector())
    return engine


def _detectors_count(detectors_executed: Any) -> int:
    if isinstance(detectors_executed, list):
        return len(detectors_executed)
    if isinstance(detectors_executed, int):
        return detectors_executed
    return 0


def build_observations(
    rejected: List[dict[str, Any]],
    tenant_code: str,
    tenant_name: str,
    analyzed_at: str,
) -> List[dict[str, Any]]:
    observations: List[dict[str, Any]] = []
    for item in rejected:
        candidate = item.get("candidate") or {}
        evidence = candidate.get("evidence") or {}
        baseline = candidate.get("baseline") or {}
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
            "period": candidate.get("period") or {},
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
    observations.sort(key=lambda obs: float(obs.get("financial_impact") or 0), reverse=True)
    return observations[:3]


def _tenant_record_to_dict(record: TenantAnalysisRecord) -> dict[str, Any]:
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
        "period_analyzed": {"start": record.period_start, "end": record.period_end},
        "error": record.error,
    }


def _analysis_limitations(result: Any, observations: List[dict[str, Any]] | None = None) -> List[str]:
    limitations = []
    if _detectors_count(result.detectors_executed) == 1:
        limitations.append("Apenas uma área financeira foi verificada nesta análise.")
    elif _detectors_count(result.detectors_executed) == 4:
        limitations.append(
            "Combustível, despesas, NF de fornecedor e recebíveis verificados; cartão TEF sem NSU no ERP."
        )
    elif _detectors_count(result.detectors_executed) == 3:
        limitations.append("Combustível, despesas e recebíveis verificados; cartão TEF sem NSU no ERP.")
    if not result.all_candidates and not (observations or []):
        limitations.append("Nenhum candidato atingiu os critérios de prioridade")
    return limitations


def _multi_tenant_limitations(
    tenant_records: List[TenantAnalysisRecord],
    base_limitations: List[str],
) -> List[str]:
    limitations = list(base_limitations)
    analyzed = [r for r in tenant_records if r.status == "ANALYZED"]
    failed = [r for r in tenant_records if r.status == "FAILED"]
    if failed:
        for record in failed:
            limitations.append(f"{record.tenant_name or record.tenant_id} não pôde ser analisado")
    if analyzed and failed:
        limitations.insert(0, f"{len(analyzed)} posto(s) analisado(s), {len(failed)} posto(s) com falha")
    return limitations


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


async def run_owner_analysis(
    data_inicial: str,
    data_final: str,
    *,
    analysis_id: str | None = None,
    empresa_codigo: str | None = None,
    force_tenant_discovery: bool = False,
    on_tenant_progress: TenantProgressCallback | None = None,
) -> dict[str, Any]:
    analysis_id = analysis_id or str(uuid.uuid4())
    analysis_start = utc_now()

    discovery_service = TenantDiscoveryService()
    empresa_filter: int | None = None
    if empresa_codigo and str(empresa_codigo).strip().isdigit():
        empresa_filter = int(str(empresa_codigo).strip())

    discovery: TenantDiscoveryResult = await discovery_service.discover_tenants(
        empresa_codigo_filter=empresa_filter,
        force_refresh=force_tenant_discovery,
    )
    tenants = discovery.tenants_discovered
    if not tenants:
        raise ValueError(
            "Nenhum tenant descoberto. "
            + ("; ".join(discovery.limitations) if discovery.limitations else "")
        )

    engine = _get_discovery_engine()
    tenants_total = len(tenants)

    async def _progress(record: TenantAnalysisRecord, completed: int, total: int) -> None:
        if on_tenant_progress:
            await on_tenant_progress(record, completed, total)

    result = await engine.discover_all_tenants(
        tenants=tenants,
        data_inicial=data_inicial,
        data_final=data_final,
        top_n=5,
        analysis_id=analysis_id,
        on_tenant_progress=_progress,
    )

    analysis_end = utc_now()
    execution_time_ms = int((analysis_end - analysis_start).total_seconds() * 1000)
    tenant_records = result.tenant_records
    analyzed_records = [r for r in tenant_records if r.status == "ANALYZED"]

    decisions = []
    stored_candidates = []
    for idx, candidate in enumerate(result.all_candidates):
        candidate_dict = candidate.to_dict()
        stored_candidates.append(candidate_dict)
        decisions.append({
            "decision_id": candidate.id,
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
                    "impact_type": (
                        candidate.impact_type.value
                        if hasattr(candidate.impact_type, "value")
                        else str(candidate.impact_type)
                    ),
                    "estimated_value": (
                        candidate.money_found.at_risk
                        + candidate.money_found.recoverable
                        + candidate.money_found.additional
                    ),
                },
                "source": {
                    "service": "discovery-engine",
                    "endpoint": "/api/v1/discovery/top-5",
                    "data_timestamp": utc_now_iso(),
                },
            },
            "candidate": candidate_dict,
            "tenant_id": candidate.tenant,
            "tenant_name": candidate.tenant_name,
            "rank": idx + 1,
        })

    observations: List[dict[str, Any]] = []
    for record in analyzed_records:
        tenant_rejected = [
            item for item in result.rejected_candidates
            if str((item.get("candidate") or {}).get("tenant") or "") == record.tenant_id
        ]
        observations.extend(
            build_observations(
                tenant_rejected,
                tenant_code=record.tenant_id,
                tenant_name=record.tenant_name,
                analyzed_at=utc_now_iso(),
            )
        )
    observations.sort(key=lambda obs: float(obs.get("financial_impact") or 0), reverse=True)
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

    monitoring_state = _resolve_monitoring_state(len(decisions), len(observations), analysis_status)
    detectors_executed = result.detectors_executed
    base_limitations = _analysis_limitations(result, observations)
    limitations = _multi_tenant_limitations(tenant_records, base_limitations)
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
        "period_analyzed": {"start": data_inicial, "end": data_final},
        "detectors_available": len(detectors_executed),
        "detectors_executed": detectors_executed,
        "detectors_successful": detectors_executed,
        "detectors_failed": 0,
        "data_sources_consulted": [
            "/api/v1/sales/fuel-summary",
            "/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
            "/INTEGRACAO/TITULO_PAGAR",
            "/INTEGRACAO/TITULO_RECEBER",
            "/INTEGRACAO/VENDA_FORMA_PAGAMENTO",
            "/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE (REF NF)",
        ],
        "endpoints_consulted": [
            "/api/v1/sales/fuel-summary",
            "/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
            "/INTEGRACAO/TITULO_PAGAR",
            "/INTEGRACAO/TITULO_RECEBER",
            "/INTEGRACAO/VENDA_FORMA_PAGAMENTO",
            "/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE (REF NF)",
        ],
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
            "stored_candidates": stored_candidates,
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
        "_meta": {
            "duration_ms": execution_time_ms,
            "period_start": data_inicial,
            "period_end": data_final,
            "tenants_total": tenants_total,
            "tenants_analyzed": analyzed_count,
            "tenants_failed": failed_count,
        },
    }
