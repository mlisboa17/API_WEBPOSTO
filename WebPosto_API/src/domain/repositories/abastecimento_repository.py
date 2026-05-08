from datetime import datetime
from typing import List, Optional

from src.domain.entities.abastecimento import Abastecimento
from src.shared.repository import Repository


class AbastecimentoRepository(Repository[Abastecimento]):
    """Interface para repositório de Abastecimentos."""

    async def find_by_cliente_id(
        self, cliente_id: str, skip: int = 0, limit: int = 100
    ) -> List[Abastecimento]:
        """Encontra abastecimentos de um cliente."""
        pass

    async def find_by_webposto_id(self, webposto_id: str) -> Optional[Abastecimento]:
        """Encontra abastecimento por ID do webPosto."""
        pass

    async def find_by_date_range(
        self, data_inicio: datetime, data_fim: datetime
    ) -> List[Abastecimento]:
        """Encontra abastecimentos em um período."""
        pass
