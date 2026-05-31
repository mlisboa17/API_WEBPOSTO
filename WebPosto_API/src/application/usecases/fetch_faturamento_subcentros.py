"""
Faturamento em R$ dos 3 sub-centros operacionais (PISTA, LOJA, FOOD) no período.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.domain.entities.audit import (
    FaturamentoConsolidadoResponse,
    FaturamentoSubCentro,
    SubCentroCusto,
    calcular_faturamento_periodo,
)
from src.domain.gateways.audit_gateway import AuditGateway


class FetchFaturamentoSubCentrosUseCase:
    def __init__(self, gateway: AuditGateway) -> None:
        self._gateway = gateway

    async def execute(
        self,
        data_inicio: date,
        data_fim: date,
        *,
        posto_id: str = "default",
        filial: list[int] | None = None,
    ) -> FaturamentoConsolidadoResponse:
        itens: list[FaturamentoSubCentro] = []
        total = Decimal("0")

        for sc in SubCentroCusto.operacionais():
            raw = await self._gateway.fetch_transactions(
                data_inicio, data_fim, sc, posto_id=posto_id, filial=filial
            )
            fat = raw.faturamento_periodo or calcular_faturamento_periodo(sc, raw.vendas)
            litros = (
                sum((v.litros for v in raw.vendas), Decimal("0")).quantize(Decimal("0.01"))
                if sc == SubCentroCusto.PISTA
                else Decimal("0")
            )
            itens.append(
                FaturamentoSubCentro(
                    sub_centro=sc,
                    faturamento_periodo=fat,
                    galonagem_litros=litros,
                )
            )
            total += fat

        return FaturamentoConsolidadoResponse(
            data_inicio=data_inicio,
            data_fim=data_fim,
            posto_id=posto_id,
            itens=itens,
            faturamento_total_posto=total.quantize(Decimal("0.01")),
        )
