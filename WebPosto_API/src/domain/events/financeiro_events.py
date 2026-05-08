from dataclasses import dataclass
from datetime import datetime

from src.shared.domain_event import DomainEvent


@dataclass
class LancamentoFinanceiroRegistrado(DomainEvent):
    """Evento: Lançamento financeiro foi registrado."""

    tipo: str = ""
    valor: float = 0.0
    descricao: str = ""


@dataclass
class LancamentoFinanceiroPago(DomainEvent):
    """Evento: Lançamento financeiro foi pago."""

    valor: float = 0.0
    data_pagamento: datetime = None


@dataclass
class LancamentoFinanceiroAtualizado(DomainEvent):
    """Evento: Lançamento financeiro foi atualizado."""

    tipo: str = ""
    valor: float = 0.0
    descricao: str = ""
