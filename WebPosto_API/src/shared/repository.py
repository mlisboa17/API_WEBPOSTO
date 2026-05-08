from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar

T = TypeVar("T")


class Repository(ABC, Generic[T]):
    """Interface genérica para repositórios. Segue o padrão Port (Hexagonal Architecture)."""

    @abstractmethod
    async def save(self, entity: T) -> T:
        """Salva uma entidade (create ou update)."""
        pass

    @abstractmethod
    async def find_by_id(self, entity_id: str) -> Optional[T]:
        """Encontra uma entidade por ID."""
        pass

    @abstractmethod
    async def find_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Lista todas as entidades com paginação."""
        pass

    @abstractmethod
    async def update(self, entity_id: str, entity: T) -> Optional[T]:
        """Atualiza uma entidade."""
        pass

    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Deleta uma entidade. Retorna True se deletada, False se não encontrada."""
        pass
