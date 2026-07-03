"""
Decision Discovery Engine — Priority Score Calculator

Algoritmo centralizado para cálculo de Priority Score.

Garante que todas as decisões são comparadas usando exatamente
os mesmos critérios e pesos, independente do detector de origem.

Princípio: Transparência total no algoritmo de priorização.
"""

from __future__ import annotations

from typing import Tuple

from src.services.decision_discovery.models import (
    DecisionCandidate,
    PriorityScore,
)


class PriorityScoreCalculator:
    """
    Calculadora centralizada de Priority Score.
    
    Responsável por:
    1. Normalizar valores financeiros
    2. Calcular fatores de prioridade
    3. Aplicar pesos centralizados
    4. Retornar Priority Score final
    
    IMPORTANTE: Todos os pesos e fórmulas devem estar aqui.
    Nunca espalhar lógica de priorização pelo código.
    """
    
    # Referências para normalização (podem ser ajustadas conforme o negócio)
    MAX_FINANCIAL_REFERENCE = 50000.0  # R$ 50k como referência máxima
    MAX_DEVIATION_REFERENCE = 0.5  # 50% de desvio = máximo
    MAX_DAYS_REFERENCE = 7  # 7 dias consecutivos = urgência máxima
    MAX_TIME_REFERENCE = 60  # 60 minutos = actionability mínima
    
    def __init__(self):
        """Inicializa o calculator."""
        pass
    
    def calculate(self, candidate: DecisionCandidate) -> Tuple[PriorityScore, float]:
        """
        Calcula Priority Score para um DecisionCandidate.
        
        Args:
            candidate: Candidato a decisão
        
        Returns:
            Tupla (PriorityScore, float): Objeto PriorityScore e valor final (0-100)
        """
        # 1. Normalizar impacto financeiro
        total_money = candidate.money_found.total_impact()
        financial_impact = self._normalize_financial(total_money)
        
        # 2. Calcular desvio do baseline (se disponível)
        baseline_deviation = self._extract_baseline_deviation(candidate)
        
        # 3. Usar confidence direto (já está normalizado 0-1)
        confidence = candidate.confidence
        
        # 4. Calcular urgência (baseado em evidências)
        urgency = self._extract_urgency(candidate)
        
        # 5. Calcular actionability (baseado em tempo estimado)
        actionability = self._calculate_actionability(
            candidate.estimated_execution_time
        )
        
        # 6. Criar objeto PriorityScore
        priority_score = PriorityScore(
            financial_impact=financial_impact,
            baseline_deviation=baseline_deviation,
            confidence=confidence,
            urgency=urgency,
            actionability=actionability,
        )
        
        # 7. Calcular valor final
        priority_value = priority_score.calculate()
        
        return priority_score, priority_value
    
    def _normalize_financial(self, amount: float) -> float:
        """
        Normaliza impacto financeiro para escala 0-1.
        
        Args:
            amount: Valor absoluto (R$)
        
        Returns:
            Valor normalizado entre 0 e 1
        """
        if self.MAX_FINANCIAL_REFERENCE <= 0:
            return 0.0
        
        normalized = min(abs(amount) / self.MAX_FINANCIAL_REFERENCE, 1.0)
        return round(normalized, 4)
    
    def _extract_baseline_deviation(self, candidate: DecisionCandidate) -> float:
        """
        Extrai desvio do baseline das evidências do candidato.
        
        Args:
            candidate: Candidato a decisão
        
        Returns:
            Desvio normalizado entre 0 e 1
        """
        # Tentar extrair do baseline_used ou evidence
        baseline = candidate.baseline_used.get("baseline_value", 0)
        current = candidate.evidence.get("current_value", 0)
        
        if baseline == 0 or current == 0:
            # Sem baseline válido, usar desvio moderado padrão
            return 0.5
        
        deviation_pct = abs((current - baseline) / baseline)
        normalized = min(deviation_pct / self.MAX_DEVIATION_REFERENCE, 1.0)
        
        return round(normalized, 4)
    
    def _extract_urgency(self, candidate: DecisionCandidate) -> float:
        """
        Extrai urgência das evidências do candidato.
        
        Args:
            candidate: Candidato a decisão
        
        Returns:
            Urgência normalizada entre 0 e 1
        """
        # Tentar extrair dias impactados das evidências
        days_impacted = candidate.evidence.get("days_impacted", 7)
        
        urgency = min(days_impacted / self.MAX_DAYS_REFERENCE, 1.0)
        return round(urgency, 4)
    
    def _calculate_actionability(self, estimated_time_minutes: int) -> float:
        """
        Calcula actionability baseado em tempo estimado.
        
        Args:
            estimated_time_minutes: Tempo estimado para executar (minutos)
        
        Returns:
            Actionability normalizada entre 0 e 1 (1 = muito fácil, 0 = muito difícil)
        """
        if self.MAX_TIME_REFERENCE <= 0:
            return 0.0
        
        # Inverte: menos tempo = maior actionability
        actionability = max(0.0, 1.0 - (estimated_time_minutes / self.MAX_TIME_REFERENCE))
        return round(actionability, 4)
    
    def compare_candidates(
        self,
        candidate_a: DecisionCandidate,
        candidate_b: DecisionCandidate
    ) -> DecisionCandidate:
        """
        Compara dois candidatos e retorna o de maior prioridade.
        
        Args:
            candidate_a: Primeiro candidato
            candidate_b: Segundo candidato
        
        Returns:
            Candidato com maior Priority Score
        """
        # Calcular priority scores
        _, priority_a = self.calculate(candidate_a)
        _, priority_b = self.calculate(candidate_b)
        
        # Retornar o de maior prioridade
        return candidate_a if priority_a >= priority_b else candidate_b
