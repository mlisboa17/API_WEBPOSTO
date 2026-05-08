from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from src.shared.domain_event import DomainEvent


@dataclass
class Cliente:
    """Entity: Cliente. Representa um cliente do posto de combustíveis."""

    id: str
    nome: str
    cnpj: str
    ativo: bool = True
    webposto_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    _events: List[DomainEvent] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self):
        """Valida dados após inicialização."""
        if not self.nome or not self.nome.strip():
            raise ValueError("Nome do cliente não pode ser vazio")
        if not self.cnpj or len(self.cnpj) < 10:
            raise ValueError("CNPJ inválido")

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

    def ativar(self) -> None:
        """Ativa o cliente."""
        if self.ativo:
            return
        self.ativo = True
        self.updated_at = datetime.utcnow()

    def desativar(self) -> None:
        """Desativa o cliente."""
        if not self.ativo:
            return
        self.ativo = False
        self.updated_at = datetime.utcnow()

    def atualizar_dados(
        self, nome: Optional[str] = None, cnpj: Optional[str] = None
    ) -> None:
        """Atualiza dados do cliente."""
        if nome is not None:
            if not nome.strip():
                raise ValueError("Nome não pode ser vazio")
            self.nome = nome
        if cnpj is not None:
            if len(cnpj) < 10:
                raise ValueError("CNPJ inválido")
            self.cnpj = cnpj
        self.updated_at = datetime.utcnow()
