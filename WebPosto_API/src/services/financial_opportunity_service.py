"""F08.4 IA-3 — Financial Opportunity Engine."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from src.services.financial_intelligence_evidence import build_lineage, get_financial_intelligence_evidence
from src.services.financial_snapshot_config import get_financial_snapshot_config


def _dec(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")


class FinancialOpportunityService:
    def __init__(self) -> None:
        self._evidence = get_financial_intelligence_evidence()

    def _resolve_period(
        self,
        data_inicial: str | None,
        data_final: str | None,
    ) -> tuple[str, str]:
        cfg = get_financial_snapshot_config()
        return data_inicial or cfg.default_period()[0], data_final or cfg.default_period()[1]

    def identify(
        self,
        data_inicial: str | None = None,
        data_final: str | None = None,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        start, end = self._resolve_period(data_inicial, data_final)
        current = self._evidence.load_period(start, end, empresa_codigo)
        metrics = self._evidence.compute_metrics(current)
        opportunities: list[dict[str, Any]] = []

        expense_data = (current.expenses or {}).get("data") or {}
        by_nature = expense_data.get("resumoPorNatureza") or {}
        for code, block in by_nature.items():
            val = _dec(block.get("valor"))
            pct = float(block.get("pct") or 0)
            if val <= 0 or pct < 15:
                continue
            impacto = float((val * Decimal("0.05")).quantize(Decimal("0.01")))
            opportunities.append(
                {
                    "code": "EXPENSE_REDUCTION",
                    "title": f"Redução potencial — {block.get('label') or code}",
                    "impacto_estimado": impacto,
                    "evidencia": {
                        "categoria": code,
                        "valorAtual": float(val),
                        "participacaoPct": pct,
                        "premissa": "5% sobre categoria identificada no snapshot",
                    },
                    "origem": "financial_expenses",
                    "lineage": build_lineage("financial_expenses", current.expenses, metric=code),
                }
            )

        if metrics.overdue_receivables > 0:
            opportunities.append(
                {
                    "code": "RECEIVABLE_COLLECTION",
                    "title": "Melhora de recebimento — inadimplência identificada",
                    "impacto_estimado": float(metrics.overdue_receivables),
                    "evidencia": {"overdueReceivables": float(metrics.overdue_receivables)},
                    "origem": "financial_receivables",
                    "lineage": build_lineage("financial_receivables", current.receivables, metric="overdue"),
                }
            )

        if metrics.recebimentos > metrics.pagamentos and metrics.fluxo > 0:
            liquidity_gain = metrics.recebimentos - metrics.pagamentos
            opportunities.append(
                {
                    "code": "LIQUIDITY_BUFFER",
                    "title": "Aumento de liquidez operacional",
                    "impacto_estimado": float(liquidity_gain),
                    "evidencia": {
                        "recebimentos": float(metrics.recebimentos),
                        "pagamentos": float(metrics.pagamentos),
                    },
                    "origem": "financial_overview",
                    "lineage": build_lineage("financial_overview", current.overview, metric="liquidity"),
                }
            )

        expense_rows = expense_data.get("data") or []
        by_cat: dict[str, Decimal] = {}
        for row in expense_rows:
            cat = str(row.get("categoriaLogosV3") or row.get("planoConta") or "OUTROS")[:80]
            by_cat[cat] = by_cat.get(cat, Decimal("0")) + _dec(row.get("valor"))
        if by_cat:
            best = max(by_cat.items(), key=lambda x: x[1])
            if metrics.recebimentos > 0:
                ratio = float(best[1] / metrics.recebimentos * 100)
                if ratio < 80:
                    opportunities.append(
                        {
                            "code": "CATEGORY_EFFICIENCY",
                            "title": f"Categoria com melhor retorno relativo — {best[0][:40]}",
                            "impacto_estimado": float(best[1]),
                            "evidencia": {
                                "categoria": best[0],
                                "valor": float(best[1]),
                                "receitasRatioPct": round(ratio, 2),
                            },
                            "origem": "financial_expenses",
                            "lineage": build_lineage("financial_expenses", current.expenses, metric="category_efficiency"),
                        }
                    )

        opportunities.sort(key=lambda o: o.get("impacto_estimado") or 0, reverse=True)

        return {
            "generatedAt": datetime.now().isoformat(timespec="seconds"),
            "period": {"dataInicial": start, "dataFinal": end},
            "empresaCodigo": empresa_codigo,
            "opportunities": opportunities[:8],
            "opportunityCount": len(opportunities),
            "snapshotFirst": True,
        }


_opportunity: FinancialOpportunityService | None = None


def get_financial_opportunity_service() -> FinancialOpportunityService:
    global _opportunity
    if _opportunity is None:
        _opportunity = FinancialOpportunityService()
    return _opportunity
