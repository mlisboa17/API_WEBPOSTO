"""
Detectores de Oportunidades/Riscos/Perdas

Cada detector é responsável por identificar um tipo específico
de decisão de alto valor para proprietários.

Detectores disponíveis:
- FuelRevenueDetector: Detecta quedas de receita em combustíveis

Futuros detectores:
- ExpenseDetector: Detecta despesas anormais
- CardDetector: Detecta problemas com recebimentos de cartão
- MarginDetector: Detecta compressão de margem
- ReceivableDetector: Detecta valores a receber em atraso
- InventoryDetector: Detecta problemas de estoque
- OperationalDetector: Detecta problemas operacionais
- EmployeeDetector: Detecta questões com funcionários
"""

from src.services.decision_discovery.detectors.fuel_revenue_detector import FuelRevenueDetector
from src.services.decision_discovery.detectors.expense_detector import ExpenseDetector

__all__ = [
    "FuelRevenueDetector",
    "ExpenseDetector",
]
