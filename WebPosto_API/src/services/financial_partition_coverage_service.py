"""Coleta financeira por empresa/dia/cursor com prova explícita de cobertura."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from src.core.management_scope import LICENSED_COMPANY_CODES
from src.models.error_model import WebPostoError
from src.models.response_model import WebPostoResponse
from src.services.webposto_cursor_paginator import WebPostoCursorPaginator


class FinancialPartitionCoverageService:
    def __init__(self, client: Any, *, max_pages: int = 1000) -> None:
        self._paginator = WebPostoCursorPaginator(client, max_pages=max_pages, batch_size=200)

    @staticmethod
    def _days(start: str, end: str) -> list[str]:
        first = date.fromisoformat(start)
        last = date.fromisoformat(end)
        if first > last:
            raise ValueError("dataInicial deve ser menor ou igual a dataFinal")
        days: list[str] = []
        current = first
        while current <= last:
            days.append(current.isoformat())
            current += timedelta(days=1)
        return days

    async def collect_account_movements(
        self,
        data_inicial: str,
        data_final: str,
        company_codes: tuple[int, ...] | None = None,
    ) -> WebPostoResponse:
        requested = company_codes or tuple(sorted(LICENSED_COMPANY_CODES))
        if not requested or any(code not in LICENSED_COMPANY_CODES for code in requested):
            return WebPostoResponse.fail(WebPostoError(
                endpoint="MOVIMENTO_CONTA",
                status=400,
                type="COMPANY_OUT_OF_SCOPE",
                message="A coleta aceita somente as tres empresas licenciadas",
            ))

        all_rows: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        partitions: list[dict[str, Any]] = []
        for day in self._days(data_inicial, data_final):
            for company_code in requested:
                response = await self._paginator.collect(
                    "movimento_conta",
                    "movimento_conta",
                    {"dataInicial": day, "dataFinal": day, "empresaCodigo": company_code},
                    cursor_field="movimentoContaCodigo",
                )
                if not response.success:
                    return response
                payload = response.data or {}
                rows = payload.get("resultados") or []
                foreign = sorted({
                    int(row.get("empresaCodigo"))
                    for row in rows
                    if row.get("empresaCodigo") is not None
                    and int(row.get("empresaCodigo")) != company_code
                })
                if foreign:
                    return WebPostoResponse.fail(WebPostoError(
                        endpoint="MOVIMENTO_CONTA",
                        status=502,
                        type="TENANT_SCOPE_VIOLATION",
                        message=f"Particao {company_code}/{day} retornou empresas fora do escopo",
                    ))
                added = 0
                for row in rows:
                    row_id = str(row.get("movimentoContaCodigo") or "")
                    if not row_id or row_id in seen_ids:
                        continue
                    seen_ids.add(row_id)
                    all_rows.append(row)
                    added += 1
                partitions.append({
                    "companyCode": company_code,
                    "date": day,
                    "records": added,
                    "pagination": payload.get("pagination") or {},
                    "complete": bool((payload.get("pagination") or {}).get("complete")),
                })

        complete = all(item["complete"] for item in partitions)
        return WebPostoResponse.ok({
            "resultados": all_rows,
            "coverage": {
                "complete": complete,
                "strategy": "COMPANY_DAY_CURSOR",
                "partitions": partitions,
                "licensedCompanies": list(requested),
                "records": len(all_rows),
            },
            "synthetic": False,
        })
