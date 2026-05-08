from typing import Optional

from src.domain.entities.caixa import Caixa
from src.shared.repository import Repository


class CaixaRepository(Repository[Caixa]):
    """Interface para repositório de Movimentações de Caixa."""

    async def find_by_webposto_id(self, webposto_id: str) -> Optional[Caixa]:
        """Encontra movimentação por ID do webPosto."""
        pass

    async def find_by_referencia(self, referencia: str) -> Optional[Caixa]:
        """Encontra movimentação por referência."""
        pass

    async def find_saldo_atual(self) -> float:
        """Retorna o saldo atual da caixa."""
        pass
