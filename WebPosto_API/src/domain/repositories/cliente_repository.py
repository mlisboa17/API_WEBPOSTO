from typing import List, Optional

from src.domain.entities.cliente import Cliente
from src.shared.repository import Repository


class ClienteRepository(Repository[Cliente]):
    """Interface para repositório de Clientes. Padrão Port (Hexagonal Architecture)."""

    async def find_by_cnpj(self, cnpj: str) -> Optional[Cliente]:
        """Encontra cliente por CNPJ."""
        pass

    async def find_by_webposto_id(self, webposto_id: str) -> Optional[Cliente]:
        """Encontra cliente por ID do webPosto."""
        pass

    async def find_all_ativos(self, skip: int = 0, limit: int = 100) -> List[Cliente]:
        """Lista apenas clientes ativos."""
        pass
