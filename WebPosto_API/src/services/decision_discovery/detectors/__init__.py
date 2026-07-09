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

from src.services.decision_discovery.detectors.card_receivable_detector import CardReceivableDetector
from src.services.decision_discovery.detectors.expense_detector import ExpenseDetector
from src.services.decision_discovery.detectors.fuel_revenue_detector import FuelRevenueDetector
from src.services.decision_discovery.detectors.supplier_invoice_spike_detector import (
    SupplierInvoiceSpikeDetector,
)

__all__ = [
    "CardReceivableDetector",
    "FuelRevenueDetector",
    "ExpenseDetector",
    "SupplierInvoiceSpikeDetector",
]
