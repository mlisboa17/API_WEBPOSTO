"""Caso de uso: vendas do dia via PostoGateway."""

from __future__ import annotations

from datetime import date
from typing import List

from src.domain.entities.sales import SalesInvoice
from src.domain.gateways.posto_gateway import PostoGateway


class FetchDailySalesUseCase:
    def __init__(self, gateway: PostoGateway) -> None:
        self._gateway = gateway

    async def execute(self, horas: int = 24) -> List[SalesInvoice]:
        vendas = await self._gateway.get_vendas_recentes(horas=horas)
        hoje = date.today()
        return [v for v in vendas if v.data_emissao.date() == hoje]
