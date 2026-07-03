"""
Root Cause Engine — Models

Estruturas de dados para análise de causas raízes de decisões.

O Root Cause Engine complementa o Decision Discovery Engine,
explicando **por que** um problema aconteceu, não apenas **qual** é o problema.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class CauseType(str, Enum):
    """Tipo de causa identificada."""
    
    PRICE = "price"  # Problema relacionado a preço
    VOLUME = "volume"  # Problema relacionado a volume
    MARGIN = "margin"  # Problema relacionado a margem
    STOCK = "stock"  # Problema relacionado a estoque
    OPERATIONAL = "operational"  # Problema operacional
    EXTERNAL = "external"  # Fator externo (clima, evento, etc.)
    COMPETITION = "competition"  # Concorrência
    UNKNOWN = "unknown"  # Causa desconhecida


class CauseCertainty(str, Enum):
    """Nível de certeza sobre a causa."""
    
    CONFIRMED = "CONFIRMED"  # Causa confirmada (evidência direta)
    PROBABLE = "PROBABLE"  # Causa provável (forte evidência)
    POSSIBLE = "POSSIBLE"  # Causa possível (indício)
    UNKNOWN = "UNKNOWN"  # Insuficiente para determinar


@dataclass
class Investigation:
    """
    Resultado de uma investigação específica.
    
    Cada investigação analisa um aspecto do problema
    (produto, volume, preço, margem, etc.).
    """
    
    aspect: str  # Aspecto investigado (ex: "Produto", "Volume", "Preço")
    finding: str  # Descoberta principal
    evidence: Dict[str, Any]  # Evidências encontradas
    contribution_to_problem: float  # 0-1: Contribuição para o problema
    confidence: float  # 0-1: Confiança na investigação
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa Investigation para dict."""
        return {
            "aspect": self.aspect,
            "finding": self.finding,
            "evidence": self.evidence,
            "contribution_to_problem": round(self.contribution_to_problem, 4),
            "confidence": round(self.confidence, 4),
        }


@dataclass
class CauseProbability:
    """
    Probabilidade de uma causa específica.
    
    Representa uma hipótese de causa com sua probabilidade
    baseada em evidências.
    """
    
    cause_type: CauseType
    description: str  # Descrição da causa
    probability: float  # 0-1: Probabilidade
    certainty: CauseCertainty
    supporting_evidence: List[str]  # Evidências que suportam
    contradicting_evidence: List[str]  # Evidências que contradizem
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa CauseProbability para dict."""
        return {
            "cause_type": self.cause_type.value,
            "description": self.description,
            "probability": round(self.probability, 4),
            "certainty": self.certainty.value,
            "supporting_evidence": self.supporting_evidence,
            "contradicting_evidence": self.contradicting_evidence,
        }


@dataclass
class Recommendation:
    """
    Recomendação específica baseada na causa provável.
    
    Nunca genérica, sempre acionável.
    """
    
    action: str  # Ação específica a tomar
    estimated_time_minutes: int  # Tempo estimado em minutos
    expected_impact: str  # "High", "Medium", "Low"
    priority: int  # 1 (mais alta) a N
    why: str  # Por que esta ação é recomendada
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa Recommendation para dict."""
        return {
            "action": self.action,
            "estimated_time_minutes": self.estimated_time_minutes,
            "expected_impact": self.expected_impact,
            "priority": self.priority,
            "why": self.why,
        }


@dataclass
class RootCauseAnalysis:
    """
    Análise completa de causa raiz.
    
    Resultado da investigação automática realizada pelo Root Cause Engine.
    
    Estrutura:
    - Problema encontrado
    - Investigações realizadas
    - Causa mais provável
    - Causas alternativas descartadas
    - Recomendações específicas
    - Confidence da análise
    """
    
    # Identificação
    decision_id: str  # ID da decisão analisada
    investigator_name: str  # Nome do investigador usado
    
    # Problema
    problem_summary: str  # Resumo do problema
    financial_impact: float  # Impacto financeiro (R$)
    
    # Investigações
    investigations: List[Investigation]  # Investigações realizadas
    
    # Causa Provável
    most_probable_cause: Optional[CauseProbability]  # Causa mais provável
    alternative_causes: List[CauseProbability]  # Causas alternativas
    discarded_hypotheses: List[str]  # Hipóteses descartadas (com motivo)
    
    # Recomendações
    recommendations: List[Recommendation]  # Recomendações ordenadas por prioridade
    
    # Confidence
    overall_confidence: float  # 0-1: Confiança geral da análise
    confidence_explanation: str  # Explicação do confidence
    
    # Metadados
    analysis_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    data_sources_used: List[str] = field(default_factory=list)  # APIs/endpoints
    analysis_duration_ms: float = 0.0  # Tempo da análise
    
    # Mensagem (quando não há causa determinável)
    insufficient_data_message: Optional[str] = None
    
    def has_probable_cause(self) -> bool:
        """
        Verifica se há uma causa provável determinada.
        
        Returns:
            True se há causa provável com certainty >= POSSIBLE
        """
        if not self.most_probable_cause:
            return False
        
        return self.most_probable_cause.certainty in [
            CauseCertainty.CONFIRMED,
            CauseCertainty.PROBABLE,
            CauseCertainty.POSSIBLE,
        ]
    
    def get_explanation(self) -> str:
        """
        Gera explicação estruturada da análise.
        
        Formato:
        1. Problema encontrado
        2. Investigação realizada
        3. Causa provável
        4. Evidências
        5. Recomendações
        
        Returns:
            String formatada com a explicação completa
        """
        if not self.has_probable_cause():
            return self.insufficient_data_message or "Dados insuficientes para determinar causa provável."
        
        cause = self.most_probable_cause
        
        explanation = f"""**Problema Encontrado:**
{self.problem_summary}

**Impacto Financeiro:**
R$ {self.financial_impact:,.2f}

**Causa Mais Provável:**
{cause.description}

**Certeza:**
{cause.certainty.value} (Probabilidade: {cause.probability:.0%})

**Evidências:**
"""
        
        for evidence in cause.supporting_evidence:
            explanation += f"• {evidence}\n"
        
        if self.recommendations:
            explanation += "\n**Recomendações:**\n"
            for i, rec in enumerate(self.recommendations[:3], 1):
                explanation += f"{i}. {rec.action} ({rec.estimated_time_minutes} min) - Impacto: {rec.expected_impact}\n"
        
        explanation += f"\n**Confidence da Análise:**\n{self.overall_confidence:.0%} - {self.confidence_explanation}"
        
        return explanation
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa RootCauseAnalysis para dict."""
        return {
            "decision_id": self.decision_id,
            "investigator": self.investigator_name,
            "problem": {
                "summary": self.problem_summary,
                "financial_impact": self.financial_impact,
            },
            "investigations": [inv.to_dict() for inv in self.investigations],
            "most_probable_cause": (
                self.most_probable_cause.to_dict() if self.most_probable_cause else None
            ),
            "alternative_causes": [cause.to_dict() for cause in self.alternative_causes],
            "discarded_hypotheses": self.discarded_hypotheses,
            "recommendations": [rec.to_dict() for rec in self.recommendations],
            "confidence": {
                "overall": round(self.overall_confidence, 4),
                "explanation": self.confidence_explanation,
            },
            "metadata": {
                "timestamp": self.analysis_timestamp,
                "data_sources": self.data_sources_used,
                "duration_ms": round(self.analysis_duration_ms, 2),
            },
            "insufficient_data_message": self.insufficient_data_message,
            "has_probable_cause": self.has_probable_cause(),
            "explanation": self.get_explanation(),
        }


@dataclass
class RootCauseResult:
    """
    Resultado completo do Root Cause Engine.
    
    Inclui a análise e metadados de execução.
    """
    
    success: bool
    analysis: Optional[RootCauseAnalysis] = None
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa RootCauseResult para dict."""
        return {
            "success": self.success,
            "analysis": self.analysis.to_dict() if self.analysis else None,
            "error_message": self.error_message,
            "execution_time_ms": round(self.execution_time_ms, 2),
        }
