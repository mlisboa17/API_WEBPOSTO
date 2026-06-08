from __future__ import annotations

from decimal import Decimal

from src.gateway.webposto_client import WebPostoClient
from src.models.error_model import WebPostoError
from src.models.response_model import WebPostoResponse


class ExpensesService:
    def __init__(self, client: WebPostoClient) -> None:
        self.client = client

    @staticmethod
    def _rows(payload: object) -> list[dict]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            if isinstance(payload.get("resultados"), list):
                return payload["resultados"]
            if isinstance(payload.get("data"), list):
                return payload["data"]
        return []

    @staticmethod
    def _validate_real_item(row: dict) -> dict | None:
        descricao = row.get("descricao") or row.get("historico") or row.get("produto") or row.get("codigoProduto")
        valor = row.get("valor") or row.get("valorTotal") or row.get("valorDespesa")
        data = row.get("data") or row.get("dataFiscal") or row.get("dataHoraAbastecimento")
        if not (descricao and valor and data):
            return None
        return {
            "descricao": str(descricao),
            "valor": str(Decimal(str(valor))),
            "data": str(data),
            "synthetic": False,
        }

    async def get_periodo(self, data_inicial: str, data_final: str) -> WebPostoResponse:
        primary = await self.client.call_endpoint(
            "financeiro", params={"dataInicial": data_inicial, "dataFinal": data_final}
        )
        if primary.success:
            rows = [x for x in (self._validate_real_item(r) for r in self._rows(primary.data)) if x]
            return WebPostoResponse.ok(rows)

        if primary.error and primary.error.status == 401:
            fallback = await self.client.call_endpoint(
                "abastecimento", params={"dataInicial": data_inicial, "dataFinal": data_final}
            )
            if not fallback.success:
                return fallback
            rows = [x for x in (self._validate_real_item(r) for r in self._rows(fallback.data)) if x]
            return WebPostoResponse.ok(rows)

        return WebPostoResponse.fail(
            primary.error or WebPostoError(endpoint="/INTEGRACAO/TITULO_PAGAR", status=500, type="UNKNOWN_ERROR", message="Falha no servico de expenses")
        )
