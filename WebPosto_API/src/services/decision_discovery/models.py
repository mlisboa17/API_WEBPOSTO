"""
Decision Discovery Engine — Models

Estruturas de dados padrão para decisões descobertas automaticamente.

Todos os detectores devem retornar DecisionCandidate seguindo exatamente
esta estrutura para garantir consistência e escalabilidade.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class MoneyType(str, Enum):
    """Tipo de impacto financeiro identificado."""
    
    AT_RISK = "at_risk"  # Dinheiro que pode ser perdido
    RECOVERABLE = "recoverable"  # Dinheiro que pode ser recuperado
    ADDITIONAL = "additional"  # Dinheiro adicional possível (crescimento)


class MoneyConfidence(str, Enum):
    """Nível de confiança no valor financeiro."""
    
    ESTIMATED = "ESTIMATED"  # Valor estimado baseado em projeções
    CONFIRMED = "CONFIRMED"  # Valor confirmado por dados reais


class DecisionCategory(str, Enum):
    """Categoria da decisão."""
    
    REVENUE = "REVENUE"  # Receita
    COST = "COST"  # Custo/Despesa
    MARGIN = "MARGIN"  # Margem
    CASH = "CASH"  # Caixa
    OPERATIONAL = "OPERATIONAL"  # Operacional
    COMPLIANCE = "COMPLIANCE"  # Conformidade
    RISK = "RISK"  # Risco


class ImpactType(str, Enum):
    """Tipo de impacto financeiro."""
    
    REVENUE = "revenue"
    COST = "cost"
    MARGIN = "margin"
    CASH = "cash"
    RISK = "risk"


@dataclass
class MoneyFound:
    """
    Estrutura para Money Found.
    
    Princípio 16: Nunca misturar estimativas com fatos.
    Princípio 17: Todo valor deve indicar claramente se é estimado ou confirmado.
    """
    
    at_risk: float = 0.0
    at_risk_type: MoneyConfidence = MoneyConfidence.ESTIMATED
    
    recoverable: float = 0.0
    recoverable_type: MoneyConfidence = MoneyConfidence.ESTIMATED
    
    additional: float = 0.0
    additional_type: MoneyConfidence = MoneyConfidence.ESTIMATED
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa MoneyFound para dict."""
        return {
            "at_risk": {
                "value": self.at_risk,
                "type": self.at_risk_type.value,
            },
            "recoverable": {
                "value": self.recoverable,
                "type": self.recoverable_type.value,
            },
            "additional": {
                "value": self.additional,
                "type": self.additional_type.value,
            },
        }
    
    def total_impact(self) -> float:
        """Calcula impacto financeiro total."""
        return self.at_risk + self.recoverable + self.additional


@dataclass
class ConfidenceFactors:
    """
    Fatores que compõem o Confidence Score.
    
    Todos os fatores devem estar entre 0.0 e 1.0.
    """
    
    data_quality: float  # Qualidade dos dados utilizados
    comparison_validity: float  # Validade da comparação (baseline)
    period_adequacy: float  # Adequação do período analisado
    calculation_reliability: float = 1.0  # Confiabilidade do cálculo
    
    def overall_confidence(self) -> float:
        """
        Calcula Confidence Score geral (média ponderada).
        
        Pesos:
        - data_quality: 40%
        - comparison_validity: 30%
        - period_adequacy: 20%
        - calculation_reliability: 10%
        """
        return (
            self.data_quality * 0.40 +
            self.comparison_validity * 0.30 +
            self.period_adequacy * 0.20 +
            self.calculation_reliability * 0.10
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa ConfidenceFactors para dict."""
        return {
            "data_quality": round(self.data_quality, 4),
            "comparison_validity": round(self.comparison_validity, 4),
            "period_adequacy": round(self.period_adequacy, 4),
            "calculation_reliability": round(self.calculation_reliability, 4),
            "overall_confidence": round(self.overall_confidence(), 4),
        }


@dataclass
class PriorityScore:
    """
    Score de priorização da decisão.
    
    Calcula automaticamente a prioridade baseado em múltiplos fatores.
    Centraliza pesos e fórmulas para evitar lógica espalhada.
    """
    
    financial_impact: float  # 0-1: Impacto financeiro normalizado
    baseline_deviation: float  # 0-1: Desvio do baseline normalizado
    confidence: float  # 0-1: Confidence score
    urgency: float  # 0-1: Urgência (tempo sensível)
    actionability: float  # 0-1: Facilidade de execução
    
    # Pesos (centralizados, somam 1.0)
    WEIGHT_FINANCIAL = 0.40
    WEIGHT_DEVIATION = 0.20
    WEIGHT_CONFIDENCE = 0.20
    WEIGHT_URGENCY = 0.10
    WEIGHT_ACTIONABILITY = 0.10
    
    def calculate(self) -> float:
        """
        Calcula o Priority Score final (0-100).
        
        Fórmula centralizada para garantir consistência entre detectores.
        """
        score = (
            self.financial_impact * self.WEIGHT_FINANCIAL +
            self.baseline_deviation * self.WEIGHT_DEVIATION +
            self.confidence * self.WEIGHT_CONFIDENCE +
            self.urgency * self.WEIGHT_URGENCY +
            self.actionability * self.WEIGHT_ACTIONABILITY
        )
        return round(score * 100, 2)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa PriorityScore para dict."""
        return {
            "financial_impact": round(self.financial_impact, 4),
            "baseline_deviation": round(self.baseline_deviation, 4),
            "confidence": round(self.confidence, 4),
            "urgency": round(self.urgency, 4),
            "actionability": round(self.actionability, 4),
            "priority_score": self.calculate(),
            "weights": {
                "financial": self.WEIGHT_FINANCIAL,
                "deviation": self.WEIGHT_DEVIATION,
                "confidence": self.WEIGHT_CONFIDENCE,
                "urgency": self.WEIGHT_URGENCY,
                "actionability": self.WEIGHT_ACTIONABILITY,
            },
        }


@dataclass
class DecisionCandidate:
    """
    Estrutura padrão para decisões descobertas.
    
    TODOS os detectores devem retornar exatamente esta estrutura.
    Nenhum detector pode adicionar campos customizados.
    
    A decisão deve SEMPRE começar pelo dinheiro (Money Found),
    nunca pelo problema técnico.
    
    Princípio 4: Dados Reais Sempre.
    Princípio 15: O Proprietário Decide.
    Princípio 18: Momento Zero (clareza em 10 segundos).
    Princípio 19: Priorize a Decisão Mais Valiosa.
    """
    
    # Identificação
    id: str
    detector_name: str  # Nome do detector que gerou a decisão
    
    # Título e Descrição (começam pelo dinheiro)
    title: str  # Ex: "Você pode estar perdendo R$ 12.430 por semana"
    summary: str  # Resumo claro e acionável
    
    # Categorização
    category: DecisionCategory
    impact_type: ImpactType
    
    # Contexto
    tenant: str  # Código do tenant (empresa/posto)
    tenant_name: Optional[str] = None
    period_start: str = ""  # ISO date
    period_end: str = ""  # ISO date
    
    # Money Found (OBRIGATÓRIO)
    money_found: MoneyFound = field(default_factory=MoneyFound)
    
    # Confidence (OBRIGATÓRIO, >= 0.80 para exibir)
    confidence: float = 0.0  # 0-1
    confidence_factors: Optional[ConfidenceFactors] = None
    
    # Priority Score (calculado automaticamente)
    priority_score: Optional[PriorityScore] = None
    priority_value: float = 0.0  # 0-100 (calculado)
    
    # Ação Recomendada
    recommended_actions: List[str] = field(default_factory=list)
    estimated_execution_time: int = 0  # minutos
    
    # Evidências e Rastreabilidade
    evidence: Dict[str, Any] = field(default_factory=dict)
    baseline_used: Dict[str, Any] = field(default_factory=dict)
    source_endpoints: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    alternatives_considered: int = 0  # Quantas alternativas foram descartadas
    selection_reason: str = ""  # Por que esta foi escolhida
    
    # Thresholds de decisão prioritária (BUILD-03A)
    MIN_DECISION_CONFIDENCE = 0.80
    MIN_DECISION_IMPACT_BRL = 5000.0

    def is_valid(self) -> bool:
        """
        Valida se a decisão atende aos critérios mínimos de PRIORIDADE.
        
        Critérios:
        - Confidence >= 80%
        - Impacto financeiro >= R$ 5.000
        - Título claro
        - Ações recomendadas
        """
        return (
            self.confidence >= self.MIN_DECISION_CONFIDENCE and
            self.money_found.total_impact() >= self.MIN_DECISION_IMPACT_BRL and
            len(self.title) > 0 and
            len(self.recommended_actions) > 0
        )
    
    def calculate_priority(self, priority_calculator) -> None:
        """
        Calcula e atribui o Priority Score usando o calculator centralizado.
        
        Args:
            priority_calculator: Instância de PriorityScoreCalculator
        """
        self.priority_score, self.priority_value = priority_calculator.calculate(self)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serializa DecisionCandidate para dict (compatível com frontend).
        """
        return {
            "id": self.id,
            "detector": self.detector_name,
            "title": self.title,
            "summary": self.summary,
            "category": self.category.value,
            "impact_type": self.impact_type.value,
            "tenant": self.tenant,
            "tenant_name": self.tenant_name,
            "period": {
                "start": self.period_start,
                "end": self.period_end,
            },
            "money_found": self.money_found.to_dict(),
            "confidence": round(self.confidence, 4),
            "confidence_factors": (
                self.confidence_factors.to_dict() if self.confidence_factors else None
            ),
            "priority_score": (
                self.priority_score.to_dict() if self.priority_score else None
            ),
            "priority_value": self.priority_value,
            "recommended_actions": self.recommended_actions,
            "estimated_execution_time": self.estimated_execution_time,
            "evidence": self.evidence,
            "baseline": self.baseline_used,
            "source_endpoints": self.source_endpoints,
            "created_at": self.created_at,
            "alternatives_considered": self.alternatives_considered,
            "selection_reason": self.selection_reason,
        }


@dataclass
class TenantAnalysisRecord:
    """Registro de execução por tenant (BUILD-03B)."""

    tenant_id: str
    tenant_name: str
    empresa_codigo: str
    credential_alias: str
    status: str
    detectors_executed: List[str] = field(default_factory=list)
    candidates_found: int = 0
    decisions_found: int = 0
    observations_found: int = 0
    requests_count: int = 0
    execution_time_ms: int = 0
    period_start: str = ""
    period_end: str = ""
    error: Optional[str] = None


@dataclass
class DiscoveryResult:
    """
    Resultado completo da execução do Discovery Engine.
    
    Contém não apenas a decisão escolhida, mas também
    o log de todas as candidatas avaliadas.
    """
    
    top_decision: Optional[DecisionCandidate] = None
    all_candidates: List[DecisionCandidate] = field(default_factory=list)
    rejected_candidates: List[Dict[str, Any]] = field(default_factory=list)
    execution_time_ms: float = 0.0
    detectors_executed: List[str] = field(default_factory=list)
    message: str = ""  # Mensagem caso não haja decisão
    tenant_records: List[TenantAnalysisRecord] = field(default_factory=list)
    tenant_ids: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa DiscoveryResult para dict."""
        return {
            "top_decision": self.top_decision.to_dict() if self.top_decision else None,
            "candidates_count": len(self.all_candidates),
            "rejected_count": len(self.rejected_candidates),
            "execution_time_ms": round(self.execution_time_ms, 2),
            "detectors_executed": self.detectors_executed,
            "message": self.message or "Decision discovered successfully" if self.top_decision else "No decision with sufficient confidence and impact found",
        }
