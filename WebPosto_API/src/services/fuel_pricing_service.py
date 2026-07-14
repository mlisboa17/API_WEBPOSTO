"""Paridade de preços de compra (abastecimento) vs venda (combustível)."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from src.domain.adelaide.abastecimento_filters import valor_financeiro_abastecimento
from src.gateway.webposto_client import WebPostoClient
from src.services.analytics_multiselect import build_overview_filters
from src.services.analytics_service import AnalyticsService
from src.services.multiselect_utils import parse_empresa_codigos
from src.services.network_financial_overview_service import NetworkFinancialOverviewService

DEFAULT_MARGIN_TARGET_PCT = 10.0


class FuelPricingService:
    """Cruza litros vendidos com preço médio de compra e venda por combustível."""

    def __init__(self, client: WebPostoClient) -> None:
        self._client = client
        self._overview = NetworkFinancialOverviewService(client)
        self._analytics = AnalyticsService(self._overview)

    @staticmethod
    def _dec(value: Any) -> Decimal:
        try:
            return Decimal(str(value or 0))
        except Exception:
            return Decimal("0")

    @staticmethod
    def _q2(value: Decimal) -> float:
        return round(float(value.quantize(Decimal("0.01"))), 2)

    async def build_paridade(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None,
    ) -> dict[str, Any]:
        codes = parse_empresa_codigos(empresa_codigo)
        filters = build_overview_filters(data_inicial, data_final, empresa_codigo)

        fuel_resp = await self._analytics.get_fuel_summary(filters)
        fuel_rows = fuel_resp.data if fuel_resp.success and isinstance(fuel_resp.data, list) else []

        purchase_rows: list[dict] = []
        empresa_filter = codes if codes else None
        for code in empresa_filter or [None]:
            params: dict[str, Any] = {
                "dataInicial": data_inicial,
                "dataFinal": data_final,
            }
            if code is not None:
                params["empresaCodigo"] = code
            abast = await self._client.call_endpoint("abastecimento", params=params)
            if not abast.success:
                continue
            raw = abast.data
            rows = raw if isinstance(raw, list) else (raw or {}).get("resultados") or (raw or {}).get("data") or []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                if empresa_filter and str(row.get("empresaCodigo") or "") not in {str(c) for c in empresa_filter}:
                    continue
                purchase_rows.append(row)

        sales_acc: dict[str, dict[str, Decimal]] = defaultdict(
            lambda: {"litros": Decimal("0"), "valor": Decimal("0")}
        )
        for row in fuel_rows:
            name = str(row.get("combustivel") or "").strip()
            if not name:
                continue
            sales_acc[name]["litros"] += self._dec(row.get("litros"))
            sales_acc[name]["valor"] += self._dec(row.get("valor"))

        purchase_acc: dict[str, dict[str, Decimal]] = defaultdict(
            lambda: {"litros": Decimal("0"), "valor": Decimal("0")}
        )
        for row in purchase_rows:
            name = str(
                row.get("descricaoProduto") or row.get("produto") or row.get("combustivel") or ""
            ).strip()
            if not name:
                continue
            litros = self._dec(row.get("quantidade") or row.get("litros"))
            valor = valor_financeiro_abastecimento(row)
            if litros <= 0 and valor > 0:
                unit = self._dec(row.get("valorUnitario"))
                if unit > 0:
                    litros = valor / unit
            purchase_acc[name]["litros"] += litros
            purchase_acc[name]["valor"] += self._dec(valor)

        paridade: list[dict[str, Any]] = []
        all_fuels = set(sales_acc) | set(purchase_acc)
        total_litros = sum((sales_acc[f]["litros"] for f in all_fuels), Decimal("0"))

        for fuel in sorted(all_fuels, key=lambda f: float(sales_acc[f]["litros"]), reverse=True):
            sale = sales_acc[fuel]
            purchase = purchase_acc[fuel]
            litros = sale["litros"]
            preco_venda = (sale["valor"] / litros) if litros > 0 else Decimal("0")
            purchase_litros = purchase["litros"] if purchase["litros"] > 0 else litros
            preco_compra = (
                (purchase["valor"] / purchase_litros) if purchase_litros > 0 else Decimal("0")
            )
            margem_real = (
                ((preco_venda - preco_compra) / preco_venda * 100) if preco_venda > 0 else Decimal("0")
            )
            delta = margem_real - Decimal(str(DEFAULT_MARGIN_TARGET_PCT))
            paridade.append(
                {
                    "combustivel": fuel,
                    "litros": self._q2(litros),
                    "precoMedioCompra": self._q2(preco_compra),
                    "precoMedioVenda": self._q2(preco_venda),
                    "margemRealizadaPct": self._q2(margem_real),
                    "margemMetaPct": DEFAULT_MARGIN_TARGET_PCT,
                    "deltaMargemPct": self._q2(delta),
                    "participacao": self._q2((litros / total_litros * 100) if total_litros > 0 else Decimal("0")),
                }
            )

        return {
            "paridadePrecos": paridade,
            "precificacao": {
                "litrosTotal": self._q2(total_litros),
                "combustiveisAnalisados": len(paridade),
                "margemMediaRealizadaPct": self._q2(
                    sum(self._dec(p["margemRealizadaPct"]) * self._dec(p["litros"]) for p in paridade)
                    / total_litros
                    if total_litros > 0
                    else Decimal("0")
                ),
                "margemMetaPct": DEFAULT_MARGIN_TARGET_PCT,
            },
            "lineage": {
                "venda": "/api/v1/sales/fuel-summary",
                "compra": "/INTEGRACAO/ABASTECIMENTO",
            },
        }

    async def enrich_executive_payload(
        self,
        payload: dict[str, Any],
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None,
    ) -> dict[str, Any]:
        pricing = await self.build_paridade(data_inicial, data_final, empresa_codigo)
        merged = {**payload, **pricing}
        combustiveis = list(merged.get("combustiveis") or [])
        paridade_map = {p["combustivel"]: p for p in pricing.get("paridadePrecos") or []}
        for item in combustiveis:
            key = str(item.get("combustivel") or "")
            if key in paridade_map:
                item.update(
                    {
                        "precoMedioCompra": paridade_map[key]["precoMedioCompra"],
                        "precoMedioVenda": paridade_map[key]["precoMedioVenda"],
                        "margemRealizadaPct": paridade_map[key]["margemRealizadaPct"],
                    }
                )
        merged["combustiveis"] = combustiveis
        kpis = dict(merged.get("kpis") or {})
        kpis.update(pricing.get("precificacao") or {})
        merged["kpis"] = kpis
        return merged
