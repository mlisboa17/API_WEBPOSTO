from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


@dataclass(frozen=True)
class SnapshotPeriod:
    data_inicial: str
    data_final: str
    empresa_codigo: int | None = None

    @property
    def file_stem(self) -> str:
        ini = self.data_inicial.replace("-", "")
        fim = self.data_final.replace("-", "")
        if ini == fim:
            return f"snapshot_{ini}"
        return f"snapshot_{ini}_{fim}"


class FinancialSnapshotService:
    def __init__(self, base_url: str = "http://127.0.0.1:8041", timeout: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, path: str, params: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
        try:
            response = requests.get(f"{self.base_url}{path}", params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json(), None
        except Exception as exc:  # noqa: BLE001
            return None, str(exc)

    def _fetch_paginated(
        self,
        path: str,
        params: dict[str, Any],
        data_key: str = "data",
        limit: int = 500,
        max_pages: int = 50,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        errors: list[str] = []
        rows: list[dict[str, Any]] = []
        page = 1

        while page <= max_pages:
            payload, err = self._request(path, {**params, "page": page, "limit": limit})
            if err:
                errors.append(err)
                break
            if not payload:
                break

            data = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(data, dict):
                break

            page_rows = data.get(data_key)
            if not isinstance(page_rows, list):
                page_rows = []

            rows.extend([row for row in page_rows if isinstance(row, dict)])

            total = int(data.get("total") or len(rows))
            if len(page_rows) == 0 or len(rows) >= total:
                break

            page += 1

        if page > max_pages:
            errors.append("pagination_limit_reached")

        return rows, errors

    def collect_snapshot(self, period: SnapshotPeriod) -> dict[str, Any]:
        base_params: dict[str, Any] = {
            "dataInicial": period.data_inicial,
            "dataFinal": period.data_final,
        }
        if period.empresa_codigo is not None:
            base_params["empresaCodigo"] = period.empresa_codigo

        despesas, err_despesas = self._fetch_paginated("/v1/financial/expenses", base_params)
        contas, err_contas = self._fetch_paginated("/v1/financial/accounts-payable", base_params)
        vendas, err_vendas = self._fetch_paginated("/v1/sales", base_params)
        estoque, err_estoque = self._fetch_paginated("/v1/stock", base_params)

        overview_payload, err_overview = self._request("/v1/financial/overview", base_params)
        companies_payload, err_companies = self._request("/v1/financial/companies", {
            "dataInicial": period.data_inicial,
            "dataFinal": period.data_final,
        })

        overview_data = (overview_payload or {}).get("data") if isinstance(overview_payload, dict) else {}
        companies_data = (companies_payload or {}).get("data") if isinstance(companies_payload, dict) else {}

        return {
            "meta": {
                "generatedAt": datetime.utcnow().isoformat() + "Z",
                "period": {
                    "dataInicial": period.data_inicial,
                    "dataFinal": period.data_final,
                    "empresaCodigo": period.empresa_codigo,
                },
                "baseUrl": self.base_url,
                "errors": {
                    "despesas": err_despesas,
                    "contas": err_contas,
                    "vendas": err_vendas,
                    "estoque": err_estoque,
                    "overview": err_overview,
                    "companies": err_companies,
                },
            },
            "despesas": despesas,
            "contas": contas,
            "vendas": vendas,
            "estoque": estoque,
            "overview": overview_data if isinstance(overview_data, dict) else {},
            "companies": (companies_data.get("data") if isinstance(companies_data, dict) else []) or [],
        }

    def save_snapshot(self, snapshot: dict[str, Any], period: SnapshotPeriod, output_dir: str | Path = "snapshots") -> Path:
        directory = Path(output_dir)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{period.file_stem}.json"
        path.write_text(__import__("json").dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    @staticmethod
    def load_snapshot(path: str | Path) -> dict[str, Any]:
        content = Path(path).read_text(encoding="utf-8")
        return __import__("json").loads(content)
