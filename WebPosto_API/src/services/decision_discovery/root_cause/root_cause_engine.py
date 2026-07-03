"""
Root Cause Engine — Orquestrador Principal

Gerencia a investigação de causas raízes de decisões.

Recebe uma decisão do Discovery Engine e delega a investigação
para o investigador apropriado.
"""

from __future__ import annotations

import time
from typing import Dict, Optional

from src.services.decision_discovery.models import DecisionCandidate, DecisionCategory
from src.services.decision_discovery.root_cause.models import RootCauseResult
from src.services.decision_discovery.root_cause.base_investigator import BaseRootCauseInvestigator


class RootCauseEngine:
    """
    Motor de investigação de causas raízes.
    
    Responsabilidades:
    1. Receber decisão do Discovery Engine
    2. Selecionar investigador apropriado
    3. Executar investigação
    4. Retornar análise estruturada
    
    Filosofia:
    - Complementar, nunca duplicar o Discovery Engine
    - Investigar usando apenas dados reais
    - Documentar hipóteses descartadas
    - Retornar recomendações específicas
    """
    
    def __init__(self):
        """Inicializa o Root Cause Engine."""
        self._investigators: Dict[str, BaseRootCauseInvestigator] = {}
    
    def register_investigator(
        self,
        decision_category: DecisionCategory,
        investigator: BaseRootCauseInvestigator
    ) -> None:
        """
        Registra um investigador para uma categoria de decisão.
        
        Args:
            decision_category: Categoria de decisão
            investigator: Investigador a ser registrado
        """
        self._investigators[decision_category.value] = investigator
    
    async def investigate(
        self,
        decision: DecisionCandidate
    ) -> RootCauseResult:
        """
        Investiga causa raiz de uma decisão.
        
        Args:
            decision: Decisão a ser investigada
        
        Returns:
            RootCauseResult com análise completa
        """
        start_time = time.time()
        
        try:
            # Selecionar investigador apropriado
            investigator = self._investigators.get(decision.category.value)
            
            if not investigator:
                return RootCauseResult(
                    success=False,
                    error_message=f"Nenhum investigador registrado para categoria: {decision.category.value}",
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            # Executar investigação
            analysis = await investigator.investigate(decision)
            
            execution_time_ms = (time.time() - start_time) * 1000
            analysis.analysis_duration_ms = execution_time_ms
            
            return RootCauseResult(
                success=True,
                analysis=analysis,
                execution_time_ms=execution_time_ms
            )
            
        except Exception as e:
            return RootCauseResult(
                success=False,
                error_message=f"Erro na investigação: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )
