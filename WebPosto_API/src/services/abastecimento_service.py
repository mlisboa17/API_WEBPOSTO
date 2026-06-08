from __future__ import annotations

from src.gateway.webposto_client import WebPostoClient
from src.models.response_model import WebPostoResponse


class AbastecimentoService:
    def __init__(self, client: WebPostoClient) -> None:
        self.client = client

    async def get_periodo(self, data_inicial: str, data_final: str) -> WebPostoResponse:
        return await self.client.call_endpoint(
            "abastecimento",
            params={"dataInicial": data_inicial, "dataFinal": data_final},
        )
