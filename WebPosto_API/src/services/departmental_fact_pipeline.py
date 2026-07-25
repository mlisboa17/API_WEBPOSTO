"""Pipeline diária e isolada para materialização dos fatos departamentais."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from src.core.management_scope import LICENSED_COMPANIES, is_licensed_company
from src.domain.departmental_facts import DepartmentalFactBatch, DepartmentalFactKind
from src.services.departmental_fact_builder import DepartmentalFactBuilder
from src.services.webposto_cursor_paginator import WebPostoCursorPaginator


class DepartmentalFactPipeline:
    def __init__(
        self,
        client: Any,
        paginator: WebPostoCursorPaginator | None = None,
        *,
        max_quarantine_ratio: Decimal = Decimal("0.02"),
    ) -> None:
        self._client = client
        self._paginator = paginator or WebPostoCursorPaginator(client)
        self._max_quarantine_ratio = max_quarantine_ratio

    @staticmethod
    def _rows(payload: Any) -> list[dict[str, Any]]:
        return WebPostoCursorPaginator._rows(payload)

    @staticmethod
    def _logical_token(company_code: int) -> str:
        return next(
            item.nome for item in LICENSED_COMPANIES if item.empresa_codigo == company_code
        )

    async def _collect_paginated(
        self,
        endpoint: str,
        params: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None, str | None]:
        response = await self._paginator.collect(endpoint, endpoint, params)
        if not response.success:
            error_type = response.error.type if response.error else "UNKNOWN_ERROR"
            return [], None, f"{endpoint}:{error_type}"
        pagination = (response.data or {}).get("pagination") or {}
        if pagination.get("complete") is not True:
            return [], pagination, f"{endpoint}:INCOMPLETE_PAGINATION"
        return list((response.data or {}).get("resultados") or []), pagination, None

    async def build_day(self, company_code: int, day: str) -> dict[str, Any]:
        if not is_licensed_company(company_code):
            return {
                "publishable": False,
                "companyCode": company_code,
                "day": day,
                "blockingReasons": ["UNLICENSED_COMPANY"],
                "batches": {},
            }

        params = {"empresaCodigo": company_code, "dataInicial": day, "dataFinal": day}
        (
            (product_rows, product_page, product_error),
            (sale_rows, sale_page, sale_error),
            (stock_rows, stock_page, stock_error),
        ) = await asyncio.gather(
            self._collect_paginated("produto", {"empresaCodigo": company_code}),
            self._collect_paginated("venda_item", params),
            self._collect_paginated("produto_estoque", params),
        )
        blocking = [
            error for error in (product_error, sale_error, stock_error) if error is not None
        ]
        if blocking:
            return {
                "publishable": False,
                "companyCode": company_code,
                "day": day,
                "blockingReasons": blocking,
                "pagination": {
                    "produto": product_page,
                    "venda_item": sale_page,
                    "produto_estoque": stock_page,
                },
                "batches": {},
            }

        expense_response, cash_response = await asyncio.gather(
            self._client.call_endpoint("despesas_financeiro_rede", params=params),
            self._client.call_endpoint("caixa", params=params),
        )
        if not expense_response.success:
            blocking.append("despesas_financeiro_rede:UPSTREAM_ERROR")
        if not cash_response.success:
            blocking.append("caixa:UPSTREAM_ERROR")
        if blocking:
            return {
                "publishable": False,
                "companyCode": company_code,
                "day": day,
                "blockingReasons": blocking,
                "batches": {},
            }

        product_groups = {
            int(row["produtoCodigo"]): int(row["grupoCodigo"])
            for row in product_rows
            if str(row.get("produtoCodigo") or "").isdigit()
            and str(row.get("grupoCodigo") or "").isdigit()
        }
        collected_at = datetime.now(timezone.utc)
        common = {
            "logical_token": self._logical_token(company_code),
            "product_groups": product_groups,
            "period_start": day,
            "period_end": day,
            "collected_at": collected_at,
        }
        batches: dict[str, DepartmentalFactBatch] = {
            "sales": DepartmentalFactBuilder.build(
                DepartmentalFactKind.SALE,
                sale_rows,
                endpoint="/INTEGRACAO/VENDA_ITEM",
                **common,
            ),
            "costs": DepartmentalFactBuilder.build(
                DepartmentalFactKind.COST,
                sale_rows,
                endpoint="/INTEGRACAO/VENDA_ITEM",
                **common,
            ),
            "expenses": DepartmentalFactBuilder.build(
                DepartmentalFactKind.EXPENSE,
                self._rows(expense_response.data),
                endpoint="/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
                **common,
            ),
            "stock": DepartmentalFactBuilder.build(
                DepartmentalFactKind.STOCK,
                stock_rows,
                endpoint="/INTEGRACAO/PRODUTO_ESTOQUE",
                **common,
            ),
            "cash": DepartmentalFactBuilder.build(
                DepartmentalFactKind.CASH,
                self._rows(cash_response.data),
                endpoint="/INTEGRACAO/CAIXA",
                **common,
            ),
        }
        reconciliation_ok = all(
            batch.reconciliation_difference == Decimal("0") for batch in batches.values()
        )
        identity_ok = all(batch.identity_conflicts == 0 for batch in batches.values())
        blocking_reasons: list[str] = []
        if not reconciliation_ok:
            blocking_reasons.append("RECONCILIATION_DIFFERENCE")
        if not identity_ok:
            blocking_reasons.append("IDENTITY_CONFLICT")
        classification_coverage: dict[str, dict[str, Any]] = {}
        for name, batch in batches.items():
            total = len(batch.facts) + len(batch.quarantine)
            ratio = Decimal(len(batch.quarantine)) / Decimal(total) if total else Decimal("0")
            classification_coverage[name] = {
                "classified": len(batch.facts),
                "quarantined": len(batch.quarantine),
                "quarantineRatio": ratio,
            }
            if total and ratio > self._max_quarantine_ratio:
                blocking_reasons.append(f"QUARANTINE_ABOVE_TOLERANCE:{name}")
        return {
            "materialized": True,
            "publishable": not blocking_reasons,
            "companyCode": company_code,
            "day": day,
            "blockingReasons": blocking_reasons,
            "pagination": {
                "produto": product_page,
                "venda_item": sale_page,
                "produto_estoque": stock_page,
            },
            "catalogCoverage": {
                "products": len(product_rows),
                "productsWithGroup": len(product_groups),
            },
            "classificationCoverage": classification_coverage,
            "batches": batches,
        }
