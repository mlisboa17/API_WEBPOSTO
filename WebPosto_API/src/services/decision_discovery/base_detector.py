"""
Decision Discovery Engine — Base Detector

Interface abstrata que todos os detectores devem implementar.

Garante consistência e extensibilidade:
- Todos os detectores respondem à mesma interface
- Novos detectores podem ser adicionados sem alterar o Discovery Engine
- Estrutura padronizada de respostas (DecisionCandidate)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

from src.services.decision_discovery.models import DecisionCandidate


class BaseDetector(ABC):
    """
    Interface abstrata para detectores de oportunidades/riscos/perdas.
    
    Cada detector deve:
    1. Implementar o método `detect()`
    2. Retornar DecisionCandidate ou None
    3. Nunca gerar exceções não tratadas
    4. Registrar internamente seu processo de decisão
    
    Filosofia:
    - Detectores competem entre si
    - O Discovery Engine escolhe o melhor candidato
    - Nenhum detector sabe da existência dos outros
    """
    
    def __init__(self, detector_name: str):
        """
        Inicializa o detector.
        
        Args:
            detector_name: Nome único do detector (ex: "FuelRevenueDetector")
        """
        self.detector_name = detector_name
        self._execution_log: List[Dict[str, Any]] = []
    
    @abstractmethod
    async def detect(
        self,
        tenant_code: str,
        data_inicial: str,
        data_final: str,
        **kwargs: Any
    ) -> Optional[DecisionCandidate]:
        """
        Método principal de detecção.
        
        Deve:
        1. Buscar dados relevantes
        2. Analisar padrões/anomalias
        3. Calcular confidence
        4. Calcular Money Found
        5. Retornar DecisionCandidate ou None
        
        Args:
            tenant_code: Código do tenant (empresa)
            data_inicial: Data inicial (YYYY-MM-DD)
            data_final: Data final (YYYY-MM-DD)
            **kwargs: Argumentos adicionais específicos do detector
        
        Returns:
            DecisionCandidate se encontrar oportunidade relevante, None caso contrário
        
        Raises:
            Nunca. Erros devem ser capturados e logados internamente.
        """
        pass
    
    def log(self, event: str, details: Dict[str, Any]) -> None:
        """
        Registra evento interno do detector.
        
        Args:
            event: Nome do evento (ex: "data_fetched", "candidate_created", "candidate_rejected")
            details: Detalhes do evento
        """
        self._execution_log.append({
            "detector": self.detector_name,
            "event": event,
            "details": details,
        })
    
    def get_execution_log(self) -> List[Dict[str, Any]]:
        """
        Retorna log de execução do detector.
        
        Útil para debugging e auditoria.
        """
        return self._execution_log.copy()
    
    def clear_log(self) -> None:
        """Limpa o log de execução."""
        self._execution_log.clear()
    
    def normalize_financial_impact(self, amount: float, max_reference: float = 50000.0) -> float:
        """
        Normaliza impacto financeiro para escala 0-1.
        
        Facilita comparação entre diferentes tipos de decisões.
        
        Args:
            amount: Valor absoluto (R$)
            max_reference: Valor de referência para normalização (padrão: R$ 50.000)
        
        Returns:
            Valor normalizado entre 0 e 1
        """
        if max_reference <= 0:
            return 0.0
        
        normalized = min(abs(amount) / max_reference, 1.0)
        return round(normalized, 4)
    
    def calculate_baseline_deviation(
        self,
        current_value: float,
        baseline_value: float
    ) -> float:
        """
        Calcula desvio do baseline normalizado (0-1).
        
        Args:
            current_value: Valor atual
            baseline_value: Valor baseline (referência)
        
        Returns:
            Desvio normalizado entre 0 e 1
        """
        if baseline_value == 0:
            return 0.0
        
        deviation_pct = abs((current_value - baseline_value) / baseline_value)
        
        # Normaliza: desvio de 50%+ = 1.0
        normalized = min(deviation_pct / 0.5, 1.0)
        
        return round(normalized, 4)
    
    def calculate_urgency(
        self,
        days_impacted: int,
        max_days: int = 7
    ) -> float:
        """
        Calcula urgência baseado em dias impactados.
        
        Quanto mais dias consecutivos impactados, maior a urgência.
        
        Args:
            days_impacted: Número de dias consecutivos com problema
            max_days: Número máximo de dias para normalização (padrão: 7)
        
        Returns:
            Urgência normalizada entre 0 e 1
        """
        if max_days <= 0:
            return 0.0
        
        urgency = min(days_impacted / max_days, 1.0)
        return round(urgency, 4)
    
    def calculate_actionability(
        self,
        estimated_time_minutes: int,
        max_time_minutes: int = 60
    ) -> float:
        """
        Calcula actionability (facilidade de execução).
        
        Quanto menos tempo estimado, maior a actionability.
        
        Args:
            estimated_time_minutes: Tempo estimado para executar (minutos)
            max_time_minutes: Tempo máximo de referência (padrão: 60 min)
        
        Returns:
            Actionability normalizada entre 0 e 1 (1 = muito fácil, 0 = muito difícil)
        """
        if max_time_minutes <= 0:
            return 0.0
        
        # Inverte: menos tempo = maior actionability
        actionability = max(0.0, 1.0 - (estimated_time_minutes / max_time_minutes))
        return round(actionability, 4)
