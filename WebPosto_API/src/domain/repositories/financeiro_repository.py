from typing import List, Optional

from src.domain.entities.financeiro import Financeiro, TipoLancamento
from src.shared.repository import Repository


class FinanceiroRepository(Repository[Financeiro]):
    """Interface para repositório de Lançamentos Financeiros."""

    async def find_by_tipo(
        self, tipo: TipoLancamento, skip: int = 0, limit: int = 100
    ) -> List[Financeiro]:
        """Encontra lançamentos por tipo."""
        pass

    async def find_by_webposto_id(self, webposto_id: str) -> Optional[Financeiro]:
        """Encontra lançamento por ID do webPosto."""
        pass

    async def find_vencidos(self) -> List[Financeiro]:
        """Encontra lançamentos vencidos não pagos."""
        pass

    async def find_nao_pagos(self, skip: int = 0, limit: int = 100) -> List[Financeiro]:
        """Encontra lançamentos não pagos."""
        pass
