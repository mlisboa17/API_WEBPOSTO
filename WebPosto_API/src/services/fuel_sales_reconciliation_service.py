"""Reconciliação de litros, faturamento e custo do departamento Combustíveis."""

from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from src.core.management_scope import LICENSED_COMPANIES, is_licensed_company
from src.models.error_model import WebPostoError
from src.models.response_model import WebPostoResponse
from src.services.fuel_sales_contract_service import FuelSalesContractService
from src.services.produto_catalog import ProdutoCatalogService
from src.services.webposto_cursor_paginator import WebPostoCursorPaginator


class FuelSalesReconciliationService:
    def __init__(
        self,
        client: Any,
        *,
        catalog: ProdutoCatalogService | None = None,
        paginator: WebPostoCursorPaginator | None = None,
    ) -> None:
        self._client = client
        self._catalog = catalog or ProdutoCatalogService(client)
        self._paginator = paginator or WebPostoCursorPaginator(client)

    @staticmethod
    def _q(value: Decimal, places: str) -> str:
        return str(value.quantize(Decimal(places), rounding=ROUND_HALF_UP))

    @staticmethod
    def _selected_companies(empresa_codigo: int | str | None) -> list[tuple[int, str]] | None:
        if empresa_codigo not in (None, ""):
            if not is_licensed_company(empresa_codigo):
                return None
            selected = int(empresa_codigo)
            return [
                (company.empresa_codigo, company.nome)
                for company in LICENSED_COMPANIES
                if company.empresa_codigo == selected
            ]
        return [(company.empresa_codigo, company.nome) for company in LICENSED_COMPANIES]

    async def build(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: int | str | None = None,
    ) -> WebPostoResponse:
        companies = self._selected_companies(empresa_codigo)
        if companies is None:
            return WebPostoResponse.fail(
                WebPostoError(
                    endpoint="fuel-sales-reconciliation",
                    status=403,
                    type="UNLICENSED_COMPANY",
                    message="Empresa fora do escopo das três licenças WebPosto",
                )
            )

        catalog_response = await self._catalog.get_catalog([code for code, _ in companies])
        if not catalog_response.success:
            return catalog_response
        catalog_products = (catalog_response.data or {}).get("products") or []
        group_by_product = {
            int(product["produtoCodigo"]): int(product["grupoCodigo"])
            for product in catalog_products
            if product.get("produtoCodigo") is not None and product.get("grupoCodigo") is not None
        }
        name_by_product = {
            int(product["produtoCodigo"]): str(product.get("nomeProduto") or f"Produto {product['produtoCodigo']}")
            for product in catalog_products
            if product.get("produtoCodigo") is not None
        }
        lmc_by_product = {
            int(product["produtoCodigo"]): int(product["produtoLmcCodigo"])
            for product in catalog_products
            if product.get("produtoCodigo") is not None and product.get("produtoLmcCodigo") is not None
        }
        name_by_lmc = {
            int(product["produtoLmcCodigo"]): str(product["nomeProduto"])
            for product in catalog_products
            if product.get("produtoLmcCodigo") is not None
            and product.get("nomeProduto")
            and not str(product["nomeProduto"]).startswith("Produto ")
        }

        company_results: list[dict[str, Any]] = []
        for code, name in companies:
            page_response = await self._paginator.collect(
                "venda_item_rede",
                "venda_item",
                {
                    "dataInicial": data_inicial,
                    "dataFinal": data_final,
                    "empresaCodigo": code,
                },
            )
            if not page_response.success:
                return page_response

            payload = page_response.data or {}
            raw_rows = payload.get("resultados") or []
            normalized = FuelSalesContractService.normalize_batch(
                raw_rows,
                group_by_product=group_by_product,
            )

            by_product: dict[int, dict[str, Decimal]] = defaultdict(
                lambda: {
                    "litros": Decimal("0"),
                    "faturamento": Decimal("0"),
                    "custo": Decimal("0"),
                    "desconto": Decimal("0"),
                    "acrescimo": Decimal("0"),
                }
            )
            lmc_seen: dict[int, int] = {}
            for fact in normalized["accepted"]:
                acc = by_product[fact.produto_codigo]
                acc["litros"] += fact.litros
                acc["faturamento"] += fact.faturamento
                acc["custo"] += fact.custo_total
                acc["desconto"] += fact.desconto_total
                acc["acrescimo"] += fact.acrescimo_total
                if fact.produto_lmc_codigo is not None and fact.produto_codigo not in lmc_seen:
                    lmc_seen[fact.produto_codigo] = fact.produto_lmc_codigo

            product_rows: list[dict[str, Any]] = []
            for product_code, values in sorted(
                by_product.items(), key=lambda item: item[1]["faturamento"], reverse=True
            ):
                liters = values["litros"]
                revenue = values["faturamento"]
                cost = values["custo"]
                margin = revenue - cost
                combustivel_name = name_by_product.get(product_code, "")
                if not combustivel_name or combustivel_name.startswith("Produto "):
                    lmc_code = lmc_by_product.get(product_code, lmc_seen.get(product_code))
                    combustivel_name = name_by_lmc.get(lmc_code, combustivel_name) if lmc_code is not None else combustivel_name
                if not combustivel_name:
                    combustivel_name = f"Produto {product_code}"
                product_rows.append(
                    {
                        "produtoCodigo": product_code,
                        "combustivel": combustivel_name,
                        "litros": self._q(liters, "0.001"),
                        "faturamento": self._q(revenue, "0.01"),
                        "custoRegistrado": self._q(cost, "0.01"),
                        "margemRegistrada": self._q(margin, "0.01"),
                        "precoMedioVenda": self._q(revenue / liters if liters > 0 else Decimal("0"), "0.0001"),
                        "custoMedioRegistrado": self._q(cost / liters if liters > 0 else Decimal("0"), "0.0001"),
                    }
                )

            total_items = normalized["total"]
            accepted_count = len(normalized["accepted"])
            quarantine_reasons = Counter(item["reason"] for item in normalized["quarantine"])
            company_results.append(
                {
                    "empresaCodigo": code,
                    "empresaNome": name,
                    "departamento": "combustiveis",
                    "produtos": product_rows,
                    "cobertura": {
                        "itensColetados": total_items,
                        "itensCombustivel": accepted_count,
                        "itensQuarentena": len(normalized["quarantine"]),
                        "coberturaPct": round((accepted_count / total_items * 100) if total_items else 0, 2),
                        "duplicidadesRemovidas": normalized["duplicates"],
                        "motivosQuarentena": dict(quarantine_reasons),
                    },
                    "pagination": payload.get("pagination") or {},
                }
            )

        return WebPostoResponse.ok(
            {
                "departamento": "combustiveis",
                "dataInicial": data_inicial,
                "dataFinal": data_final,
                "empresas": company_results,
                "consolidacaoGenerica": False,
            }
        )
