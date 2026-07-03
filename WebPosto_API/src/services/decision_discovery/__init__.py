"""
Decision Discovery Engine — VALUE-01

Motor de descoberta automática de decisões de alto valor para proprietários.

Arquitetura escalável que permite múltiplos detectores competindo para
identificar a melhor oportunidade/risco/perda do dia.

Princípio 19: O LOGOS deve encontrar primeiro a decisão mais valiosa
antes de aumentar a quantidade de decisões apresentadas.
"""

from src.services.decision_discovery.models import (
    DecisionCandidate,
    MoneyFound,
    PriorityScore,
    ConfidenceFactors,
)
from src.services.decision_discovery.base_detector import BaseDetector
from src.services.decision_discovery.priority_calculator import PriorityScoreCalculator
from src.services.decision_discovery.discovery_engine import DecisionDiscoveryEngine

__all__ = [
    "DecisionCandidate",
    "MoneyFound",
    "PriorityScore",
    "ConfidenceFactors",
    "BaseDetector",
    "PriorityScoreCalculator",
    "DecisionDiscoveryEngine",
]
