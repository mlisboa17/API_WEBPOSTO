"""Leitura contingencial de despesas reais já coletadas em snapshots locais."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from src.core.management_scope import LICENSED_COMPANY_CODES

ROOT = Path(__file__).resolve().parents[2] / "snapshots"


def _rows_from_file(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if path.parent.name == "finance_center":
        return list((((payload.get("center") or {}).get("expenses") or {}).get("data") or []))
    return list(((payload.get("data") or {}).get("data") or []))


def load_expense_snapshots(start: str, end: str, company: int | None = None) -> dict[str, Any]:
    start_date, end_date = date.fromisoformat(start), date.fromisoformat(end)
    candidates = sorted(
        [*ROOT.glob("finance_center/*.json"), *ROOT.glob("financial/financial_expenses*.json")],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    seen: set[tuple[str, ...]] = set()
    rows: list[dict[str, Any]] = []
    dates: list[str] = []
    for path in candidates:
        for row in _rows_from_file(path):
            row_date = str(row.get("data") or row.get("dataMovimento") or "")[:10]
            try:
                parsed_date = date.fromisoformat(row_date)
                company_code = int(row.get("empresaCodigo"))
            except (TypeError, ValueError):
                continue
            if not start_date <= parsed_date <= end_date or company_code not in LICENSED_COMPANY_CODES:
                continue
            if company is not None and company_code != company:
                continue
            marker = (
                str(company_code), row_date, str(row.get("valor") or row.get("valorTotal") or ""),
                str(row.get("planoContaCodigo") or ""), str(row.get("planoConta") or row.get("descricao") or ""),
            )
            if marker in seen:
                continue
            seen.add(marker)
            rows.append(row)
            dates.append(row_date)
    rows.sort(key=lambda row: (str(row.get("data") or ""), str(row.get("empresaCodigo") or "")), reverse=True)
    return {
        "rows": rows,
        "coverage": {"requestedStart": start, "requestedEnd": end, "availableStart": min(dates) if dates else None, "availableEnd": max(dates) if dates else None},
        "source": "LOCAL_REAL_SNAPSHOTS",
    }
