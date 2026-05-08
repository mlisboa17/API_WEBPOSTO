from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.shared.domain_event import DomainEvent


@dataclass
class Abastecimento:
    """Entity: Abastecimento. Representa um registro de abastecimento."""

    id: str
    cliente_id: str
    data: datetime
    valor: float
    litros: float
    produto_id: Optional[str] = None
    webposto_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    _events: list[DomainEvent] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self):
        """Valida dados após inicialização."""
        if self.valor <= 0:
            raise ValueError("Valor deve ser maior que zero")
        if self.litros <= 0:
            raise ValueError("Litros deve ser maior que zero")
        if not self.cliente_id:
            raise ValueError("Cliente ID é obrigatório")

    def adicionar_evento(self, event: DomainEvent) -> None:
        """Adiciona um evento ao agregado."""
        event.aggregate_id = self.id
        self._events.append(event)

    def limpar_eventos(self) -> list[DomainEvent]:
        """Retorna eventos e limpa a lista."""
        events = self._events.copy()
        self._events.clear()
        return events

    def obter_eventos(self) -> list[DomainEvent]:
        """Retorna eventos sem limpar."""
        return self._events.copy()

    def preco_litro(self) -> float:
        """Calcula preço por litro."""
        return round(self.valor / self.litros, 2)
