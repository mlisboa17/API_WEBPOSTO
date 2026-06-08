from __future__ import annotations

from decimal import Decimal

from src.models.error_model import WebPostoError
from src.models.response_model import WebPostoResponse
from src.services.caixa_service import CaixaService


class FechamentoService:
    def __init__(self, caixa_service: CaixaService) -> None:
        self.caixa_service = caixa_service

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

    async def get_fechamento(self, posto_id: str, data_inicial: str, data_final: str) -> WebPostoResponse:
        caixa = await self.caixa_service.get_caixa(data_inicial, data_final)
        if not caixa.success:
            return caixa

        apresentado = await self.caixa_service.get_caixa_apresentado(data_inicial, data_final)
        if not apresentado.success:
            return apresentado

        caixa_rows = self._rows(caixa.data)
        apresentado_rows = self._rows(apresentado.data)

        total_caixa = Decimal("0")
        total_apresentado = Decimal("0")
        for row in caixa_rows:
            v = row.get("valor") or row.get("valorTotal")
            if v is not None:
                total_caixa += Decimal(str(v))
        for row in apresentado_rows:
            v = row.get("valor") or row.get("valorTotal")
            if v is not None:
                total_apresentado += Decimal(str(v))

        return WebPostoResponse.ok(
            {
                "posto_id": posto_id,
                "periodo": {"dataInicial": data_inicial, "dataFinal": data_final},
                "count": len(caixa_rows) + len(apresentado_rows),
                "items": {
                    "caixa": caixa_rows,
                    "caixa_apresentado": apresentado_rows,
                },
                "summary": {
                    "total_caixa": str(total_caixa),
                    "total_caixa_apresentado": str(total_apresentado),
                    "synthetic": False,
                },
            }
        )
