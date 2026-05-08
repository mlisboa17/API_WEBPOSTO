from dataclasses import dataclass
from datetime import datetime

from src.shared.domain_event import DomainEvent


@dataclass
class AbastecimentoRegistrado(DomainEvent):
    """Evento: Abastecimento foi registrado."""

    cliente_id: str = ""
    valor: float = 0.0
    litros: float = 0.0
    data: datetime = None


@dataclass
class AbastecimentoAtualizado(DomainEvent):
    """Evento: Abastecimento foi atualizado."""

    cliente_id: str = ""
    valor: float = 0.0
    litros: float = 0.0


@dataclass
class AbastecimentoDeletado(DomainEvent):
    """Evento: Abastecimento foi deletado."""

    cliente_id: str = ""
