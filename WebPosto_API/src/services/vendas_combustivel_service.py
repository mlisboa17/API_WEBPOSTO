from __future__ import annotations

from decimal import Decimal

from src.gateway.webposto_client import WebPostoClient
from src.models.response_model import WebPostoResponse


class VendasCombustivelService:
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
            merged: list[dict] = []
            for periodo, value in payload.items():
                if not isinstance(value, list):
                    continue
                for bloco in value:
                    if not isinstance(bloco, dict):
                        continue
                    posto = bloco.get("posto")
                    produtos = bloco.get("produtos")
                    if isinstance(produtos, list) and produtos:
                        for produto in produtos:
                            if not isinstance(produto, dict):
                                continue
                            merged.append(
                                {
                                    "periodo": periodo,
                                    "posto": posto,
                                    **produto,
                                }
                            )
                    else:
                        merged.append({"periodo": periodo, "posto": posto, **bloco})
            if merged:
                return merged
        return []

    @staticmethod
    def _normalize_item(row: dict) -> dict | None:
        data = row.get("data") or row.get("dataMovimento") or row.get("dia") or row.get("periodo")
        produto = row.get("produto") or row.get("combustivel") or row.get("descricao") or row.get("nome")
        posto = row.get("posto")
        litros = row.get("litros") or row.get("quantidade") or row.get("volume")
        valor = row.get("valor") or row.get("valorTotal") or row.get("total")

        if valor is None and isinstance(row.get("totais"), dict):
            amount = row["totais"].get("amount")
            if isinstance(amount, dict):
                valor = amount.get("amount")

        if not (data and produto and valor is not None and posto):
            return None

        normalized = {
            "data": str(data),
            "posto": str(posto),
            "produto": str(produto),
            "valor": str(Decimal(str(valor))),
            "synthetic": False,
            "raw": row,
        }
        if litros is not None:
            normalized["litros"] = str(Decimal(str(litros)))
        return normalized

    async def get_periodo(self, data_inicial: str, data_final: str) -> WebPostoResponse:
        response = await self.client.call_endpoint(
            "analise_vendas_combustivel",
            params={"dataInicial": data_inicial, "dataFinal": data_final},
        )
        if not response.success:
            return response

        rows = [x for x in (self._normalize_item(row) for row in self._rows(response.data)) if x]
        return WebPostoResponse.ok(
            {
                "periodo": {"dataInicial": data_inicial, "dataFinal": data_final},
                "count": len(rows),
                "items": rows,
                "synthetic": False,
            }
        )
