"""
Root Cause Engine — Base Root Cause Investigator

Interface abstrata para investigadores de causa raiz.

Garante que todos os investigadores seguem o mesmo padrão
e retornam análises estruturadas consistentes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any, List

from src.services.decision_discovery.models import DecisionCandidate
from src.services.decision_discovery.root_cause.models import RootCauseAnalysis


class BaseRootCauseInvestigator(ABC):
    """
    Interface abstrata para investigadores de causa raiz.
    
    Cada investigador é especializado em analisar um tipo
    específico de decisão (ex: queda de receita em combustível).
    
    Filosofia:
    - Nunca assumir hipóteses
    - Investigar usando apenas dados reais
    - Documentar hipóteses descartadas
    - Calcular confidence da análise
    - Retornar recomendações específicas (nunca genéricas)
    """
    
    def __init__(self, investigator_name: str):
        """
        Inicializa o investigador.
        
        Args:
            investigator_name: Nome único do investigador
        """
        self.investigator_name = investigator_name
        self._execution_log: List[Dict[str, Any]] = []
    
    @abstractmethod
    async def investigate(
        self,
        decision: DecisionCandidate,
        **kwargs: Any
    ) -> RootCauseAnalysis:
        """
        Investiga a causa raiz de uma decisão.
        
        Deve:
        1. Realizar múltiplas investigações (produto, volume, preço, etc.)
        2. Coletar evidências
        3. Determinar causa mais provável
        4. Descartar hipóteses não suportadas
        5. Gerar recomendações específicas
        6. Calcular confidence da análise
        7. Retornar RootCauseAnalysis completo
        
        Args:
            decision: Decisão a ser investigada (do Discovery Engine)
            **kwargs: Argumentos adicionais
        
        Returns:
            RootCauseAnalysis com investigação completa
        
        Raises:
            Nunca. Erros devem ser capturados e retornados
            com insufficient_data_message.
        """
        pass
    
    def log(self, event: str, details: Dict[str, Any]) -> None:
        """
        Registra evento interno do investigador.
        
        Args:
            event: Nome do evento
            details: Detalhes do evento
        """
        self._execution_log.append({
            "investigator": self.investigator_name,
            "event": event,
            "details": details,
        })
    
    def get_execution_log(self) -> List[Dict[str, Any]]:
        """
        Retorna log de execução do investigador.
        
        Útil para debugging e auditoria.
        """
        return self._execution_log.copy()
    
    def clear_log(self) -> None:
        """Limpa o log de execução."""
        self._execution_log.clear()
    
    # Métodos auxiliares para investigações comuns
    
    def calculate_contribution(
        self,
        current_value: float,
        baseline_value: float,
        total_drop: float
    ) -> float:
        """
        Calcula contribuição de um fator para o problema.
        
        Args:
            current_value: Valor atual
            baseline_value: Valor baseline
            total_drop: Queda total
        
        Returns:
            Contribuição normalizada (0-1)
        """
        if total_drop == 0:
            return 0.0
        
        factor_drop = baseline_value - current_value
        contribution = abs(factor_drop / total_drop)
        
        return min(contribution, 1.0)
    
    def assess_price_impact(
        self,
        current_price: float,
        baseline_price: float,
        volume_change_pct: float
    ) -> str:
        """
        Avalia impacto do preço baseado em correlação com volume.
        
        Args:
            current_price: Preço atual
            baseline_price: Preço baseline
            volume_change_pct: Variação de volume (%)
        
        Returns:
            Descrição do impacto (Alto, Médio, Baixo, Nenhum)
        """
        price_change_pct = ((current_price - baseline_price) / baseline_price) if baseline_price > 0 else 0
        
        # Se preço subiu e volume caiu proporcionalmente → Alto impacto
        if price_change_pct > 0.05 and volume_change_pct < -0.10:
            return "Alto"
        
        # Se preço subiu e volume caiu levemente → Médio impacto
        elif price_change_pct > 0.02 and volume_change_pct < -0.05:
            return "Médio"
        
        # Se preço subiu mas volume estável → Baixo impacto
        elif price_change_pct > 0 and volume_change_pct > -0.05:
            return "Baixo"
        
        # Outros casos
        else:
            return "Nenhum"
    
    def identify_time_pattern(
        self,
        hourly_data: Dict[str, float]
    ) -> str:
        """
        Identifica padrão temporal na queda.
        
        Args:
            hourly_data: Dados por faixa horária {hora: valor}
        
        Returns:
            Descrição do padrão identificado
        """
        if not hourly_data:
            return "Sem dados horários disponíveis"
        
        # Encontrar horários com maior queda
        sorted_hours = sorted(hourly_data.items(), key=lambda x: x[1])
        
        worst_hours = [h for h, v in sorted_hours[:3]]
        
        if all(int(h.split('-')[0]) >= 18 for h in worst_hours):
            return "Queda concentrada no período noturno (18h-22h)"
        elif all(int(h.split('-')[0]) < 12 for h in worst_hours):
            return "Queda concentrada no período matutino (6h-12h)"
        elif all(12 <= int(h.split('-')[0]) < 18 for h in worst_hours):
            return "Queda concentrada no período vespertino (12h-18h)"
        else:
            return "Queda distribuída ao longo do dia"
    
    def format_evidence_list(
        self,
        evidence_dict: Dict[str, Any]
    ) -> List[str]:
        """
        Formata evidências para lista legível.
        
        Args:
            evidence_dict: Dicionário de evidências
        
        Returns:
            Lista de strings formatadas
        """
        evidence_list = []
        
        for key, value in evidence_dict.items():
            if isinstance(value, float):
                if "pct" in key or "percent" in key:
                    evidence_list.append(f"{key.replace('_', ' ').title()}: {value:.1%}")
                else:
                    evidence_list.append(f"{key.replace('_', ' ').title()}: {value:.2f}")
            elif isinstance(value, int):
                evidence_list.append(f"{key.replace('_', ' ').title()}: {value}")
            else:
                evidence_list.append(f"{key.replace('_', ' ').title()}: {value}")
        
        return evidence_list
