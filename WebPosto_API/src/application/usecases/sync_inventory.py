"""Caso de uso: sincronizar estoque/tanques."""

from __future__ import annotations

from typing import List

from src.domain.entities.sales import TankVolume
from src.domain.gateways.posto_gateway import PostoGateway


class SyncInventoryUseCase:
    def __init__(self, gateway: PostoGateway) -> None:
        self._gateway = gateway

    async def execute(self) -> List[TankVolume]:
        return await self._gateway.get_volume_tanques()
