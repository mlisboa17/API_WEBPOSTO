"""F08.4 — Evidências auditáveis a partir de snapshots financeiros homologados."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from src.services.financial_snapshot_service import FinancialSnapshotService

ROOT = Path(__file__).resolve().parents[2]
FINANCIAL_DIR = ROOT / "snapshots" / "financial"

HORIZONS = ("7d", "30d", "90d", "12m")
HORIZON_DAYS = {"7d": 7, "30d": 30, "90d": 90, "12m": 365}
TREND_THRESHOLD_PCT = 5.0

_FILENAME_RE = re.compile(
    r"^financial_(overview|expenses|receivables|payables)_(?P<start>\d{4}-\d{2}-\d{2})_(?P<end>\d{4}-\d{2}-\d{2})_(?P<empresa>.+)\.json$"
)


def _dec(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")


def _parse_iso(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def classify_trend(delta_pct: float | None) -> str:
    if delta_pct is None:
        return "INDETERMINADO"
    if delta_pct > TREND_THRESHOLD_PCT:
        return "CRESCIMENTO"
    if delta_pct < -TREND_THRESHOLD_PCT:
        return "QUEDA"
    return "ESTABILIDADE"


def delta_pct(current: Decimal, previous: Decimal) -> float | None:
    if previous == 0:
        if current == 0:
            return 0.0
        return None
    return float((current - previous) / previous * 100)


def build_lineage(kind: str, payload: dict[str, Any] | None, *, metric: str) -> dict[str, Any]:
    if not payload:
        return {"present": False, "kind": kind, "metric": metric, "lineage": False}
    return {
        "present": True,
        "kind": kind,
        "key": payload.get("key"),
        "source": payload.get("source"),
        "lastUpdated": payload.get("lastUpdated"),
        "homologated": payload.get("homologated"),
        "metric": metric,
        "lineage": True,
    }


@dataclass(frozen=True)
class PeriodEvidence:
    data_inicial: str
    data_final: str
    empresa_codigo: str | None
    key: str
    overview: dict[str, Any] | None
    expenses: dict[str, Any] | None
    receivables: dict[str, Any] | None
    payables: dict[str, Any] | None


@dataclass(frozen=True)
class PeriodMetrics:
    despesas: Decimal
    pagamentos: Decimal
    recebimentos: Decimal
    receitas: Decimal
    fluxo: Decimal
    receivable_rows: int
    payable_rows: int
    overdue_receivables: Decimal
    overdue_payables: Decimal
    expense_concentration_top_share: float
    receivable_top_share: float


class FinancialIntelligenceEvidence:
    def __init__(self, snapshots: FinancialSnapshotService | None = None) -> None:
        self._snapshots = snapshots or FinancialSnapshotService()

    def build_key(self, data_inicial: str, data_final: str, empresa_codigo: str | int | None) -> str:
        return self._snapshots.build_key(data_inicial, data_final, empresa_codigo)

    def load_period(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> PeriodEvidence:
        key = self.build_key(data_inicial, data_final, empresa_codigo)
        self._snapshots.ensure_homologated(data_inicial, data_final, empresa_codigo)
        return PeriodEvidence(
            data_inicial=data_inicial,
            data_final=data_final,
            empresa_codigo=str(empresa_codigo) if empresa_codigo not in (None, "", "all") else None,
            key=key,
            overview=self._snapshots.load_kind("financial_overview", key),
            expenses=self._snapshots.load_kind("financial_expenses", key),
            receivables=self._snapshots.load_kind("financial_receivables", key),
            payables=self._snapshots.load_kind("financial_payables", key),
        )

    def discover_periods(self, empresa_codigo: str | int | None = None) -> list[dict[str, Any]]:
        empresa_suffix = "all" if empresa_codigo in (None, "", "all") else str(empresa_codigo)
        found: dict[tuple[str, str, str], dict[str, Any]] = {}
        if not FINANCIAL_DIR.is_dir():
            return []
        for path in FINANCIAL_DIR.glob("financial_overview_*.json"):
            match = _FILENAME_RE.match(path.name)
            if not match or match.group("empresa") != empresa_suffix:
                continue
            start, end = match.group("start"), match.group("end")
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            found[(start, end, empresa_suffix)] = {
                "dataInicial": start,
                "dataFinal": end,
                "empresaCodigo": None if empresa_suffix == "all" else empresa_suffix,
                "key": payload.get("key") or self.build_key(start, end, empresa_codigo),
                "lastUpdated": payload.get("lastUpdated"),
                "source": payload.get("source"),
            }
        rows = list(found.values())
        rows.sort(key=lambda r: (r["dataFinal"], r["dataInicial"]), reverse=True)
        return rows

    def compute_metrics(self, evidence: PeriodEvidence) -> PeriodMetrics:
        overview_data = (evidence.overview or {}).get("data") or {}
        consolidado = overview_data.get("consolidado") or {}
        despesas = _dec(consolidado.get("total_despesas"))

        pay_rows = ((evidence.payables or {}).get("data") or {}).get("data") or []
        rec_rows = ((evidence.receivables or {}).get("data") or {}).get("data") or []
        pagamentos = _dec(consolidado.get("total_a_pagar"))
        if pay_rows:
            pagamentos = sum((_dec(r.get("valor")) for r in pay_rows), Decimal("0"))

        recebimentos = sum((_dec(r.get("valor")) for r in rec_rows), Decimal("0"))
        receitas = recebimentos
        fluxo = recebimentos - despesas

        today = date.today()
        overdue_receivables = Decimal("0")
        overdue_payables = Decimal("0")
        rec_by_empresa: dict[str, Decimal] = {}
        exp_by_cat: dict[str, Decimal] = {}

        for row in rec_rows:
            val = _dec(row.get("valor"))
            emp = str(row.get("empresaCodigo") or row.get("filial") or "—")
            rec_by_empresa[emp] = rec_by_empresa.get(emp, Decimal("0")) + val
            due = _parse_iso(row.get("vencimento"))
            situacao = str(row.get("situacao") or row.get("status") or "").lower()
            if due and due < today and situacao not in {"pago", "quitado", "baixado"}:
                overdue_receivables += val
            elif situacao in {"inadimplente", "atrasado", "vencido"}:
                overdue_receivables += val

        for row in pay_rows:
            val = _dec(row.get("valor"))
            due = _parse_iso(row.get("vencimento"))
            status = str(row.get("status") or row.get("situacao") or "").lower()
            if due and due < today and status not in {"pago", "quitado", "baixado"}:
                overdue_payables += val

        expense_rows = ((evidence.expenses or {}).get("data") or {}).get("data") or []
        for row in expense_rows:
            cat = str(row.get("categoriaLogosV3") or row.get("planoConta") or "OUTROS")[:80]
            exp_by_cat[cat] = exp_by_cat.get(cat, Decimal("0")) + _dec(row.get("valor"))

        total_exp = sum(exp_by_cat.values(), Decimal("0")) or despesas
        top_exp = max(exp_by_cat.values(), default=Decimal("0"))
        expense_concentration = float(top_exp / total_exp * 100) if total_exp else 0.0

        total_rec = recebimentos or Decimal("1")
        top_rec = max(rec_by_empresa.values(), default=Decimal("0"))
        receivable_top_share = float(top_rec / total_rec * 100) if recebimentos else 0.0

        return PeriodMetrics(
            despesas=despesas,
            pagamentos=pagamentos,
            recebimentos=recebimentos,
            receitas=receitas,
            fluxo=fluxo,
            receivable_rows=len(rec_rows),
            payable_rows=len(pay_rows),
            overdue_receivables=overdue_receivables,
            overdue_payables=overdue_payables,
            expense_concentration_top_share=round(expense_concentration, 2),
            receivable_top_share=round(receivable_top_share, 2),
        )

    def compare_periods(
        self,
        current: PeriodEvidence,
        previous: PeriodEvidence | None,
    ) -> dict[str, Any]:
        cur = self.compute_metrics(current)
        if not previous:
            return {"current": cur, "previous": None, "deltas": {}}
        prev = self.compute_metrics(previous)
        return {
            "current": cur,
            "previous": prev,
            "deltas": {
                "despesas": delta_pct(cur.despesas, prev.despesas),
                "pagamentos": delta_pct(cur.pagamentos, prev.pagamentos),
                "recebimentos": delta_pct(cur.recebimentos, prev.recebimentos),
                "receitas": delta_pct(cur.receitas, prev.receitas),
                "fluxo": delta_pct(cur.fluxo, prev.fluxo),
            },
            "previousPeriod": {
                "dataInicial": previous.data_inicial,
                "dataFinal": previous.data_final,
                "key": previous.key,
            },
        }

    def pick_baseline_period(
        self,
        periods: list[dict[str, Any]],
        current: PeriodEvidence,
        horizon: str,
    ) -> dict[str, Any] | None:
        target_days = HORIZON_DAYS[horizon]
        cur_end = _parse_iso(current.data_final)
        if not cur_end:
            return None
        for row in periods:
            if row["dataFinal"] == current.data_final and row["dataInicial"] == current.data_inicial:
                continue
            end = _parse_iso(row["dataFinal"])
            if not end or end >= cur_end:
                continue
            gap = (cur_end - end).days
            if gap <= target_days:
                return row
        return periods[1] if len(periods) > 1 else None


_evidence: FinancialIntelligenceEvidence | None = None


def get_financial_intelligence_evidence() -> FinancialIntelligenceEvidence:
    global _evidence
    if _evidence is None:
        _evidence = FinancialIntelligenceEvidence()
    return _evidence


def classify_executive_score(score: float) -> str:
    if score >= 90:
        return "EXCELENTE"
    if score >= 75:
        return "BOM"
    if score >= 50:
        return "ATENÇÃO"
    return "CRÍTICO"
