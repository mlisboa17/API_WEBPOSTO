"""
Decision Discovery Router — VALUE-01

Expõe o Decision Discovery Engine via HTTP.

Endpoints disponíveis:
- GET /api/v1/discovery/top-decision - Melhor decisão do dia
- GET /api/v1/discovery/top-3 - Top 3 decisões
- GET /api/v1/discovery/top-5 - Top 5 decisões

Princípio 19: O LOGOS deve encontrar primeiro a decisão mais valiosa
antes de aumentar a quantidade de decisões apresentadas.
"""

from __future__ import annotations

from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta
from typing import Dict, Any

from src.services.decision_discovery import DecisionDiscoveryEngine
from src.services.decision_discovery.detectors import CardReceivableDetector, ExpenseDetector, FuelRevenueDetector
from src.services.decision_discovery.root_cause.root_cause_engine import RootCauseEngine
from src.services.decision_discovery.root_cause.investigators import (
    CardReceivableRootCause,
    ExpenseRootCause,
    FuelRevenueRootCause,
)
from src.services.decision_discovery.models import DecisionCategory

router = APIRouter(prefix="/api/v1/discovery", tags=["Decision Discovery"])


def _get_discovery_engine() -> DecisionDiscoveryEngine:
    """
    Cria e configura o Discovery Engine.
    
    Registra todos os detectores disponíveis.
    
    Returns:
        DecisionDiscoveryEngine configurado
    """
    engine = DecisionDiscoveryEngine()
    
    # Registrar detectores disponíveis
    engine.register_detector(FuelRevenueDetector())
    engine.register_detector(ExpenseDetector())
    engine.register_detector(CardReceivableDetector())
    
    # Futuros detectores serão adicionados aqui:
    # engine.register_detector(CardDetector())
    # engine.register_detector(MarginDetector())
    # engine.register_detector(ReceivableDetector())
    # etc.
    
    return engine


@router.get("/top-decision")
async def get_top_decision(
    dataInicial: str = Query(..., description="Data inicial (YYYY-MM-DD)"),
    dataFinal: str = Query(..., description="Data final (YYYY-MM-DD)"),
    empresaCodigo: str | None = Query(None, description="Código da empresa"),
) -> Dict[str, Any]:
    """
    Retorna a decisão de maior prioridade.
    
    O Discovery Engine executa todos os detectores disponíveis,
    compara os resultados e retorna automaticamente a decisão
    mais importante para o proprietário.
    
    Critérios de seleção:
    - Confidence >= 80%
    - Maior Priority Score (impacto financeiro + urgência + confiança)
    
    Se nenhuma decisão atender aos critérios, retorna mensagem
    explicativa ao invés de decisões fracas.
    
    Args:
        dataInicial: Data inicial (YYYY-MM-DD)
        dataFinal: Data final (YYYY-MM-DD)
        empresaCodigo: Código da empresa (opcional, usa default se não informado)
    
    Returns:
        Decisão de maior prioridade ou mensagem de dados insuficientes
    """
    try:
        # Usar empresa padrão se não informada
        tenant_code = empresaCodigo or "vip"
        tenant_name = "POSTO VIP"  # TODO: Buscar do banco de dados
        
        # Criar Discovery Engine
        engine = _get_discovery_engine()
        
        # Executar descoberta (top 1)
        result = await engine.discover(
            tenant_code=tenant_code,
            data_inicial=dataInicial,
            data_final=dataFinal,
            top_n=1,
            tenant_name=tenant_name
        )
        
        return {
            "success": True,
            "data": {
                "decision": result.top_decision.to_dict() if result.top_decision else None,
                "message": result.message,
                "execution_time_ms": result.execution_time_ms,
                "detectors_executed": result.detectors_executed,
            },
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao executar Decision Discovery Engine: {str(e)}"
        )


@router.get("/top-3")
async def get_top_3_decisions(
    dataInicial: str = Query(..., description="Data inicial (YYYY-MM-DD)"),
    dataFinal: str = Query(..., description="Data final (YYYY-MM-DD)"),
    empresaCodigo: str | None = Query(None, description="Código da empresa"),
) -> Dict[str, Any]:
    """
    Retorna as top 3 decisões mais importantes.
    
    Similar ao /top-decision, mas retorna até 3 decisões
    ordenadas por Priority Score.
    
    Útil para interfaces que mostram mais opções ao proprietário.
    
    Args:
        dataInicial: Data inicial (YYYY-MM-DD)
        dataFinal: Data final (YYYY-MM-DD)
        empresaCodigo: Código da empresa (opcional)
    
    Returns:
        Top 3 decisões ou mensagem de dados insuficientes
    """
    try:
        tenant_code = empresaCodigo or "vip"
        tenant_name = "POSTO VIP"
        
        engine = _get_discovery_engine()
        
        result = await engine.discover(
            tenant_code=tenant_code,
            data_inicial=dataInicial,
            data_final=dataFinal,
            top_n=3,
            tenant_name=tenant_name
        )
        
        return {
            "success": True,
            "data": {
                "decisions": [c.to_dict() for c in result.all_candidates],
                "count": len(result.all_candidates),
                "message": result.message,
                "execution_time_ms": result.execution_time_ms,
                "detectors_executed": result.detectors_executed,
            },
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao executar Decision Discovery Engine: {str(e)}"
        )


@router.get("/top-5")
async def get_top_5_decisions(
    dataInicial: str = Query(..., description="Data inicial (YYYY-MM-DD)"),
    dataFinal: str = Query(..., description="Data final (YYYY-MM-DD)"),
    empresaCodigo: str | None = Query(None, description="Código da empresa"),
) -> Dict[str, Any]:
    """
    Retorna as top 5 decisões mais importantes.
    
    Similar ao /top-decision, mas retorna até 5 decisões
    ordenadas por Priority Score.
    
    Útil para dashboards executivos completos.
    
    Args:
        dataInicial: Data inicial (YYYY-MM-DD)
        dataFinal: Data final (YYYY-MM-DD)
        empresaCodigo: Código da empresa (opcional)
    
    Returns:
        Top 5 decisões ou mensagem de dados insuficientes
    """
    try:
        tenant_code = empresaCodigo or "vip"
        tenant_name = "POSTO VIP"
        
        engine = _get_discovery_engine()
        
        result = await engine.discover(
            tenant_code=tenant_code,
            data_inicial=dataInicial,
            data_final=dataFinal,
            top_n=5,
            tenant_name=tenant_name
        )
        
        return {
            "success": True,
            "data": {
                "decisions": [c.to_dict() for c in result.all_candidates],
                "count": len(result.all_candidates),
                "message": result.message,
                "execution_time_ms": result.execution_time_ms,
                "detectors_executed": result.detectors_executed,
            },
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao executar Decision Discovery Engine: {str(e)}"
        )


@router.get("/debug/execution-log")
async def get_execution_log(
    dataInicial: str = Query(..., description="Data inicial (YYYY-MM-DD)"),
    dataFinal: str = Query(..., description="Data final (YYYY-MM-DD)"),
    empresaCodigo: str | None = Query(None, description="Código da empresa"),
) -> Dict[str, Any]:
    """
    Retorna log completo de execução do Discovery Engine.
    
    Útil para debugging e auditoria.
    
    Mostra:
    - Detectores executados
    - Candidatos gerados
    - Candidatos rejeitados (com motivo)
    - Priority Scores calculados
    - Decisão final escolhida
    
    Args:
        dataInicial: Data inicial (YYYY-MM-DD)
        dataFinal: Data final (YYYY-MM-DD)
        empresaCodigo: Código da empresa (opcional)
    
    Returns:
        Log completo de execução
    """
    try:
        tenant_code = empresaCodigo or "vip"
        tenant_name = "POSTO VIP"
        
        engine = _get_discovery_engine()
        
        result = await engine.discover(
            tenant_code=tenant_code,
            data_inicial=dataInicial,
            data_final=dataFinal,
            top_n=1,
            tenant_name=tenant_name
        )
        
        return {
            "success": True,
            "data": {
                "execution_log": engine.get_execution_log(),
                "result": result.to_dict(),
            },
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao executar Decision Discovery Engine: {str(e)}"
        )


@router.get("/today")
async def get_today_decision(
    empresaCodigo: str | None = Query(None, description="Código da empresa"),
) -> Dict[str, Any]:
    """
    Conveniência: retorna a melhor decisão de hoje (últimos 7 dias).
    
    Equivalente a chamar /top-decision com dataInicial=(hoje - 7 dias)
    e dataFinal=hoje.
    
    Args:
        empresaCodigo: Código da empresa (opcional)
    
    Returns:
        Melhor decisão de hoje
    """
    hoje = datetime.now().date()
    data_final = hoje.isoformat()
    data_inicial = (hoje - timedelta(days=7)).isoformat()
    
    return await get_top_decision(
        dataInicial=data_inicial,
        dataFinal=data_final,
        empresaCodigo=empresaCodigo
    )


@router.get("/explain/{decision_id}")
async def explain_decision(
    decision_id: str
) -> Dict[str, Any]:
    """
    Explica a causa raiz de uma decisão.
    
    VALUE-02: Root Cause Engine
    
    Investiga automaticamente:
    - Produto afetado
    - Volume/litros
    - Preço médio
    - Margem
    - Padrão temporal
    - Causa provável
    - Evidências
    - Recomendações específicas
    
    Args:
        decision_id: ID da decisão a ser explicada
    
    Returns:
        RootCauseAnalysis completo com causa provável e recomendações
    """
    try:
        # 1. Buscar decisão (simular por enquanto - futuramente buscar do cache/DB)
        # Para MVP, vamos gerar uma decisão de exemplo
        from src.services.decision_discovery.models import DecisionCandidate, MoneyFound, ConfidenceFactors, ImpactType
        
        # Decisão simulada para demonstração
        decision = DecisionCandidate(
            id=decision_id,
            detector_name="FuelRevenueDetector",
            title="Você pode estar perdendo aproximadamente R$ 12.430 por semana",
            summary="Queda de 34% nas vendas de combustíveis",
            category=DecisionCategory.REVENUE,
            impact_type=ImpactType.REVENUE,
            tenant="vip",
            tenant_name="POSTO VIP",
            period_start="2026-06-25",
            period_end="2026-07-02",
            money_found=MoneyFound(at_risk=12430.0),
            confidence=0.94,
            confidence_factors=ConfidenceFactors(
                data_quality=0.98,
                comparison_validity=0.95,
                period_adequacy=0.90
            ),
            recommended_actions=["Verificar preço", "Verificar estoque"],
            estimated_execution_time=20,
            evidence={
                "product_name": "Diesel S10",
                "product_drop_pct": 0.87,
                "current_volume": 2100,
                "previous_volume": 3200,
                "current_price": 5.89,
                "previous_price": 5.45,
                "current_margin": 0.15,
                "previous_margin": 0.14,
                "days_impacted": 7,
                "time_pattern": "Queda concentrada no período noturno (18h-22h)",
            },
            baseline_used={
                "baseline_value": 36580.0,
                "current_value": 24150.0,
            },
            source_endpoints=["/api/v1/sales/fuel-summary"],
        )
        
        # 2. Criar Root Cause Engine
        root_cause_engine = RootCauseEngine()
        root_cause_engine.register_investigator(
            DecisionCategory.REVENUE,
            FuelRevenueRootCause()
        )
        root_cause_engine.register_investigator(
            DecisionCategory.COST,
            ExpenseRootCause()
        )
        root_cause_engine.register_investigator(
            DecisionCategory.CASH,
            CardReceivableRootCause()
        )
        
        # 3. Investigar causa raiz
        result = await root_cause_engine.investigate(decision)
        
        return {
            "success": result.success,
            "data": result.to_dict(),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao explicar decisão: {str(e)}"
        )
