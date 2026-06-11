"""F04.0 — Dimensão nominal de funcionários (/INTEGRACAO/FUNCIONARIO)."""
from __future__ import annotations

from typing import Any

from src.gateway.webposto_client import WebPostoClient
from src.services.cash_operations_service import CashOperationsService, _round2


class EmployeeDimensionService:
    def __init__(self, client: WebPostoClient | None = None) -> None:
        self._cash = CashOperationsService(client)

    async def fetch_catalog(
        self,
        data_inicial: str,
        data_final: str,
        max_pages: int = 10,
    ) -> list[dict[str, Any]]:
        rows, _ = await self._cash._fetch_paged("funcionario", data_inicial, data_final, max_pages)
        return rows

    @staticmethod
    def to_dimension(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        seen: set[int] = set()
        for row in rows:
            try:
                code = int(row.get("funcionarioCodigo"))
            except (TypeError, ValueError):
                continue
            if code in seen:
                continue
            seen.add(code)
            out.append(
                {
                    "employeeId": code,
                    "employeeCode": code,
                    "employeeName": row.get("nome"),
                    "employeeCpf": row.get("cpf"),
                    "employeeReference": row.get("funcionarioReferencia"),
                    "employeeStatus": "ATIVO" if row.get("ativo") in (True, 1, "1", "S", "s") else "INATIVO",
                    "empresaCodigo": row.get("empresaCodigo"),
                    "funcaoCodigo": row.get("funcaoCodigo"),
                }
            )
        return out

    @staticmethod
    def index_by_code(dim: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
        idx: dict[int, dict[str, Any]] = {}
        for row in dim:
            code = row.get("employeeCode")
            if code is not None:
                idx[int(code)] = row
        return idx

    async def build(
        self,
        data_inicial: str,
        data_final: str,
    ) -> dict[str, Any]:
        rows = await self.fetch_catalog(data_inicial, data_final)
        dim = self.to_dimension(rows)
        active = [d for d in dim if d.get("employeeStatus") == "ATIVO"]
        with_name = [d for d in dim if d.get("employeeName")]
        with_cpf = [d for d in dim if d.get("employeeCpf")]
        return {
            "total": len(dim),
            "ativos": len(active),
            "comNome": len(with_name),
            "comCpf": len(with_cpf),
            "nominalizacaoPct": _round2(100 * len(with_name) / len(dim)) if dim else 0.0,
            "employees": dim,
            "index": EmployeeDimensionService.index_by_code(dim),
        }
