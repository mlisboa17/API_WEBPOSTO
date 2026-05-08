from dataclasses import dataclass

from src.shared.domain_event import DomainEvent


@dataclass
class ClienteAdicionado(DomainEvent):
    """Evento: Cliente foi adicionado ao sistema."""

    nome: str = ""
    cnpj: str = ""


@dataclass
class ClienteAtualizado(DomainEvent):
    """Evento: Dados do cliente foram atualizados."""

    nome: str = ""
    cnpj: str = ""


@dataclass
class ClienteAtivado(DomainEvent):
    """Evento: Cliente foi ativado."""

    pass


@dataclass
class ClienteDesativado(DomainEvent):
    """Evento: Cliente foi desativado."""

    pass


@dataclass
class ClienteDeletado(DomainEvent):
    """Evento: Cliente foi deletado."""

    pass
