from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.models.response_model import WebPostoResponse
from src.services.abastecimento_service import AbastecimentoService
from src.services.caixa_service import CaixaService
from src.services.financeiro_service import FinanceiroService
from src.services.vendas_combustivel_service import VendasCombustivelService


class OperacaoInteligenteService:
    def __init__(
        self,
        abastecimento_service: AbastecimentoService,
        caixa_service: CaixaService,
        financeiro_service: FinanceiroService,
        vendas_combustivel_service: VendasCombustivelService,
    ) -> None:
        self.abastecimento_service = abastecimento_service
        self.caixa_service = caixa_service
        self.financeiro_service = financeiro_service
        self.vendas_combustivel_service = vendas_combustivel_service

    @staticmethod
    def _rows(payload: object) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            if isinstance(payload.get("resultados"), list):
                return payload["resultados"]
            if isinstance(payload.get("data"), list):
                return payload["data"]
            if isinstance(payload.get("items"), list):
                return payload["items"]
        return []

    @staticmethod
    def _sum_values(rows: list[dict[str, Any]], keys: list[str]) -> str:
        total = Decimal("0")
        for row in rows:
            for key in keys:
                value = row.get(key)
                if value is not None:
                    total += Decimal(str(value))
                    break
        return str(total)

    async def get_visao_unificada(self, posto_id: str, data_inicial: str, data_final: str) -> WebPostoResponse:
        abastecimento = await self.abastecimento_service.get_periodo(data_inicial, data_final)
        if not abastecimento.success:
            return abastecimento

        caixa = await self.caixa_service.get_caixa(data_inicial, data_final)
        if not caixa.success:
            return caixa

        caixa_apresentado = await self.caixa_service.get_caixa_apresentado(data_inicial, data_final)
        if not caixa_apresentado.success:
            return caixa_apresentado

        financeiro = await self.financeiro_service.get_periodo(data_inicial, data_final)
        if not financeiro.success:
            return financeiro

        vendas = await self.vendas_combustivel_service.get_periodo(data_inicial, data_final)
        if not vendas.success:
            return vendas

        rows_abastecimento = self._rows(abastecimento.data)
        rows_caixa = self._rows(caixa.data)
        rows_caixa_apresentado = self._rows(caixa_apresentado.data)
        rows_financeiro = self._rows(financeiro.data)
        rows_vendas = self._rows(vendas.data)

        return WebPostoResponse.ok(
            {
                "posto_id": posto_id,
                "periodo": {"dataInicial": data_inicial, "dataFinal": data_final},
                "operacao": {
                    "abastecimento": rows_abastecimento,
                    "analise_vendas_combustivel": rows_vendas,
                },
                "financeiro": {
                    "titulo_pagar": rows_financeiro,
                    "caixa": rows_caixa,
                    "caixa_apresentado": rows_caixa_apresentado,
                },
                "correlacao": {
                    "abastecimento_count": len(rows_abastecimento),
                    "vendas_combustivel_count": len(rows_vendas),
                    "caixa_count": len(rows_caixa),
                    "caixa_apresentado_count": len(rows_caixa_apresentado),
                    "titulo_pagar_count": len(rows_financeiro),
                    "total_caixa": self._sum_values(rows_caixa, ["valor", "valorTotal", "apurado"]),
                    "total_caixa_apresentado": self._sum_values(rows_caixa_apresentado, ["valor", "valorTotal", "apurado"]),
                    "total_titulo_pagar": self._sum_values(rows_financeiro, ["valor", "valorTotal", "valorDespesa"]),
                    "synthetic": False,
                },
            }
        )
