from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional

from src.shared.domain_event import DomainEvent


class TipoLancamento(str, Enum):
    """Tipos de lançamento financeiro."""

    RECEBER = "RECEBER"
    PAGAR = "PAGAR"
    TRANSFERENCIA = "TRANSFERENCIA"


@dataclass
class Financeiro:
    """Entity: Financeiro. Representa um lançamento financeiro."""

    id: str
    tipo: TipoLancamento
    valor: float
    data_vencimento: datetime
    descricao: str
    pago: bool = False
    data_pagamento: Optional[datetime] = None
    webposto_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    _events: List[DomainEvent] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self):
        """Valida dados após inicialização."""
        if self.valor <= 0:
            raise ValueError("Valor deve ser maior que zero")
        if not self.descricao:
            raise ValueError("Descrição é obrigatória")

    def adicionar_evento(self, event: DomainEvent) -> None:
        """Adiciona um evento ao agregado."""
        event.aggregate_id = self.id
        self._events.append(event)

    def limpar_eventos(self) -> List[DomainEvent]:
        """Retorna eventos e limpa a lista."""
        events = self._events.copy()
        self._events.clear()
        return events

    def obter_eventos(self) -> List[DomainEvent]:
        """Retorna eventos sem limpar."""
        return self._events.copy()

    def marcar_pago(self, data_pagamento: Optional[datetime] = None) -> None:
        """Marca lançamento como pago."""
        if self.pago:
            return
        self.pago = True
        self.data_pagamento = data_pagamento or datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def marcar_nao_pago(self) -> None:
        """Marca lançamento como não pago."""
        if not self.pago:
            return
        self.pago = False
        self.data_pagamento = None
        self.updated_at = datetime.utcnow()

    def dias_vencimento(self) -> int:
        """Retorna dias para vencimento (negativo = vencido)."""
        delta = self.data_vencimento - datetime.utcnow()
        return delta.days

    @property
    def vencido(self) -> bool:
        """Verifica se está vencido."""
        return not self.pago and self.dias_vencimento() < 0
