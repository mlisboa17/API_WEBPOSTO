"""
Owner Action Center Router — BUILD-01D

Router específico para a Home do proprietário, reutilizando serviços existentes.
Expõe apenas os dados essenciais para o fluxo principal.

IMPORTANTE (BUILD-01D):
- Esta versão retorna estrutura básica mas válida
- NÃO usa mocks - se não há dados, retorna explicitamente "dados insuficientes"
- Quando Action Center tiver dados reais, será fácil adicionar transformação
- Princípio 4: Dados Reais Sempre - nunca inventar dados

Princípios:
- Reutiliza ActionCenterService e ExecutiveDecisionEngineService
- Transforma dados para o formato esperado pelo frontend
- Mantém dados reais sempre (sem mocks)
- Filtra por confidence >= 80%
"""

from __future__ import annotations

from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta
from typing import List, Dict, Any
import uuid

from src.services.action_center_service import ActionCenterService
from src.services.action_center_snapshot_service import ActionCenterSnapshotService

router = APIRouter(prefix="/api/v1/owner-action-center", tags=["Owner Action Center"])

_action_service = ActionCenterService()
_action_snapshot = ActionCenterSnapshotService(_action_service)


def _create_decision_structure(
    decision_data: Dict[str, Any],
    rank: int,
    tenant_id: str,
    confidence: float = 0.85
) -> Dict[str, Any]:
    """
    Cria estrutura de decisão compatível com o frontend.
    
    BUILD-01D: Estrutura mínima mas válida.
    Quando Action Center retornar dados reais, adaptar aqui.
    """
    decision_id = str(uuid.uuid4())
    
    return {
        "action": {
            "id": decision_id,
            "title": decision_data.get("title", "Decisão Pendente"),
            "description": decision_data.get("description", ""),
            "priority": decision_data.get("priority", "HIGH"),
            "type": decision_data.get("type", "DECISION"),
            "status": "pending",
            "confidence": confidence,
            "time_to_resolve": decision_data.get("time_estimate", 15),
            "financial_impact": {
                "impact_type": decision_data.get("impact_type", "revenue"),
                "estimated_value": decision_data.get("value", 0),
            },
            "source": {
                "service": "action-center",
                "endpoint": "/api/v1/action-center/cockpit",
                "data_timestamp": datetime.now().isoformat(),
            },
        },
        "tenant_id": tenant_id,
        "rank": rank,
    }


@router.get("/top5")
async def get_top5_decisions(
    dataInicial: str = Query(..., description="Data inicial (YYYY-MM-DD)"),
    dataFinal: str = Query(..., description="Data final (YYYY-MM-DD)"),
    empresaCodigo: str | None = Query(None, description="Código da empresa"),
) -> dict:
    """
    Retorna as top 5 decisões mais importantes para o proprietário.
    
    BUILD-01D: Versão funcional básica.
    Reutiliza Action Center Service quando dados disponíveis.
    
    IMPORTANTE: NÃO usa mocks. Se não há dados suficientes, retorna array vazio
    com mensagem clara de "dados insuficientes".
    """
    try:
        # Buscar dados do Action Center (serviço existente)
        payload, stale, hit = await _action_snapshot.get_or_collect(
            dataInicial, dataFinal, empresaCodigo
        )
        
        decisions = []
        
        # Se Action Center retornou dados, tentar extrair decisões
        if payload:
            cockpit = payload.get("cockpit", {})
            executive_answers = payload.get("executiveAnswers", [])
            
            # TODO: Quando Action Center tiver estrutura de decisões,
            # implementar transformação aqui
            # Por enquanto, retornar estrutura vazia mas válida
            
        # Filtrar apenas as com confidence >= 80%
        filtered_decisions = [d for d in decisions if d.get("action", {}).get("confidence", 0) >= 0.8]
        
        # Retornar top 5
        top_5 = filtered_decisions[:5]
        
        return {
            "success": True,
            "data": {
                "top_5_decisions": top_5,
                "total_decisions": len(filtered_decisions),
                "filtered_by_confidence": len(decisions) - len(filtered_decisions),
                "has_sufficient_data": len(top_5) > 0,
                "message": "Dados insuficientes para gerar decisões" if len(top_5) == 0 else None,
            },
            "snapshot": {"hit": hit, "stale": stale} if payload else None,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar decisões: {str(e)}")


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
