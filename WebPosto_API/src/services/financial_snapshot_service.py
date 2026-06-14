"""F08.0 — Snapshots financeiros homologados (overview, expenses, receivables, payables)."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from src.services.executive_snapshot_service import build_snapshot_key
from src.services.snapshot_store import SnapshotStore

ROOT = Path(__file__).resolve().parents[2]
FINANCIAL_DIR = ROOT / "snapshots" / "financial"
HOMOLOGATED_TTL = 30 * 24 * 3600.0

SNAPSHOT_KINDS = ("financial_overview", "financial_expenses", "financial_receivables", "financial_payables")


def _kind_filename(kind: str, key: str) -> str:
    safe = key.replace(":", "_")
    return f"{kind}_{safe}.json"


class FinancialSnapshotService:
    def __init__(self, output_dir: str | Path = FINANCIAL_DIR, ttl_seconds: float = HOMOLOGATED_TTL) -> None:
        self._dir = Path(output_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._store = SnapshotStore(self._dir, ttl_seconds)

    @staticmethod
    def build_key(data_inicial: str, data_final: str, empresa_codigo: str | int | None = None) -> str:
        return build_snapshot_key(data_inicial, data_final, empresa_codigo)

    def _path(self, kind: str, key: str) -> Path:
        return self._dir / _kind_filename(kind, key)

    def save_kind(self, kind: str, key: str, data: Any, *, source: str = "live") -> None:
        payload = {
            "kind": kind,
            "key": key,
            "lastUpdated": datetime.now().isoformat(timespec="seconds"),
            "homologated": True,
            "source": source,
            "data": data,
        }
        self._path(kind, key).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self._store.save(f"{kind}:{key}", payload)

    def load_kind(self, kind: str, key: str, *, allow_stale: bool = True) -> dict[str, Any] | None:
        store_key = f"{kind}:{key}"
        if allow_stale:
            payload, _expired = self._store.load_stale(store_key)
            if payload and payload.get("data") is not None:
                return payload
        path = self._path(kind, key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if isinstance(payload, dict) and payload.get("data") is not None:
            return payload
        return None

    def list_available(self, key: str) -> list[str]:
        return [kind for kind in SNAPSHOT_KINDS if self.load_kind(kind, key)]

    @staticmethod
    def _sum_decimal(rows: list[dict[str, Any]], field: str = "valor") -> Decimal:
        total = Decimal("0")
        for row in rows:
            try:
                total += Decimal(str(row.get(field) or 0))
            except Exception:
                continue
        return total

    def _bootstrap_from_expense_semantic(self, key: str, data_inicial: str, data_final: str) -> bool:
        semantic_dir = ROOT / "snapshots" / "expense_semantic"
        if not semantic_dir.is_dir():
            return False
        candidates = sorted(semantic_dir.glob("expenses_semantic_*.json"), reverse=True)
        rows: list[dict[str, Any]] = []
        for path in candidates:
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            payload = raw.get("payload") or raw.get("data") or {}
            batch = payload.get("rows") or payload.get("data") or []
            if isinstance(batch, list) and batch:
                rows = batch
                break
        if not rows:
            return False

        filtered = [
            r
            for r in rows
            if str(r.get("data") or "")[:10] >= data_inicial[:10]
            and str(r.get("data") or "")[:10] <= data_final[:10]
        ]
        if not filtered:
            filtered = rows[:500]

        by_empresa: dict[Any, list[dict[str, Any]]] = defaultdict(list)
        for row in filtered:
            by_empresa[row.get("empresaCodigo")].append(row)

        postos: list[dict[str, Any]] = []
        total_despesas = Decimal("0")
        for empresa_codigo, empresa_rows in by_empresa.items():
            subtotal = self._sum_decimal(empresa_rows)
            total_despesas += subtotal
            postos.append(
                {
                    "empresaCodigo": empresa_codigo,
                    "nome": f"Filial {empresa_codigo}",
                    "total_despesas": str(subtotal.quantize(Decimal("0.01"))),
                    "total_a_pagar": "0",
                    "synthetic": False,
                    "fromHomologatedSnapshot": True,
                }
            )

        overview = {
            "postos": postos,
            "consolidado": {
                "total_despesas": str(total_despesas.quantize(Decimal("0.01"))),
                "total_a_pagar": "0",
                "synthetic": False,
            },
        }
        expenses = {
            "page": 1,
            "limit": min(len(filtered), 500),
            "total": len(filtered),
            "data": filtered[:500],
            "synthetic": False,
            "fromHomologatedSnapshot": True,
        }
        self.save_kind("financial_overview", key, overview, source="expense_semantic_homologated")
        self.save_kind("financial_expenses", key, expenses, source="expense_semantic_homologated")
        self.save_kind(
            "financial_receivables",
            key,
            {"page": 1, "limit": 0, "total": 0, "data": [], "fromHomologatedSnapshot": True},
            source="expense_semantic_homologated",
        )
        self.save_kind(
            "financial_payables",
            key,
            {"page": 1, "limit": 0, "total": 0, "data": [], "fromHomologatedSnapshot": True},
            source="expense_semantic_homologated",
        )
        return True

    def ensure_homologated(self, data_inicial: str, data_final: str, empresa_codigo: str | int | None = None) -> list[str]:
        key = self.build_key(data_inicial, data_final, empresa_codigo)
        available = self.list_available(key)
        missing = [kind for kind in SNAPSHOT_KINDS if kind not in available]
        if not missing and available:
            return available
        if self._bootstrap_from_expense_semantic(key, data_inicial, data_final):
            return self.list_available(key)
        if missing and available:
            overview = self.load_kind("financial_overview", key)
            if overview and "financial_expenses" in missing:
                self.save_kind(
                    "financial_expenses",
                    key,
                    {
                        "page": 1,
                        "limit": 500,
                        "total": 0,
                        "data": [],
                        "fromHomologatedSnapshot": True,
                    },
                    source="overview_seed",
                )
            return self.list_available(key)
        return available
