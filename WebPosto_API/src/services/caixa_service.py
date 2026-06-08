from __future__ import annotations

from src.gateway.webposto_client import WebPostoClient
from src.models.response_model import WebPostoResponse


class CaixaService:
    def __init__(self, client: WebPostoClient) -> None:
        self.client = client

    async def get_caixa(self, data_inicial: str, data_final: str) -> WebPostoResponse:
        return await self.client.call_endpoint(
            "caixa",
            params={"dataInicial": data_inicial, "dataFinal": data_final},
        )

    async def get_caixa_apresentado(self, data_inicial: str, data_final: str) -> WebPostoResponse:
        return await self.client.call_endpoint(
            "caixa_apresentado",
            params={"dataInicial": data_inicial, "dataFinal": data_final},
        )
