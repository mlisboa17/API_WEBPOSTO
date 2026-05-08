from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from src.shared.domain_event import DomainEvent


@dataclass
class Caixa:
    """Entity: Caixa. Representa movimentação de caixa."""

    id: str
    descricao: str
    saldo: float
    data_movimento: datetime
    webposto_id: Optional[str] = None
    referencia: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    _events: List[DomainEvent] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self):
        """Valida dados após inicialização."""
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

    def adicionar_valor(self, valor: float) -> None:
        """Adiciona valor ao saldo."""
        if valor <= 0:
            raise ValueError("Valor deve ser maior que zero")
        self.saldo += valor
        self.updated_at = datetime.utcnow()

    def subtrair_valor(self, valor: float) -> None:
        """Subtrai valor do saldo."""
        if valor <= 0:
            raise ValueError("Valor deve ser maior que zero")
        if self.saldo < valor:
            raise ValueError("Saldo insuficiente")
        self.saldo -= valor
        self.updated_at = datetime.utcnow()

    def resetar_saldo(self, novo_saldo: float) -> None:
        """Reseta o saldo para um novo valor."""
        if novo_saldo < 0:
            raise ValueError("Saldo não pode ser negativo")
        self.saldo = novo_saldo
        self.updated_at = datetime.utcnow()
