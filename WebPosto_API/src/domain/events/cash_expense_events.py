from dataclasses import dataclass
from datetime import datetime

from src.shared.domain_event import DomainEvent


@dataclass
class CashExpenseDetected(DomainEvent):
    """Evento de domínio emitido quando uma despesa de caixa é detectada."""

    expense_id: str = ""
    cash_movement_id: str = ""
    category: str = "other"
    amount: float = 0.0
    description: str = ""
    detected_at: datetime = None
