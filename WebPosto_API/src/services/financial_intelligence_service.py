"""Inteligência Financeira Corporativa — F01.3."""
from __future__ import annotations

import logging
from collections import defaultdict
from decimal import Decimal
from typing import Any

from src.models.response_model import WebPostoResponse
from src.services.corporate_finance_center_service import CorporateFinanceCenterService
from src.services.corporate_cash_flow_service import CorporateCashFlowService
from src.services.logos_expense_classifier import classify_logos_expense_v1_baseline
from src.services.multiselect_utils import empresa_snapshot_suffix
from src.services.network_financial_overview_service import FinancialOverviewFilters

LOGGER = logging.getLogger(__name__)


def _dec(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")


def _q2(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01")))


def _top_n(items: list[dict[str, Any]], key: str, n: int = 20) -> list[dict[str, Any]]:
    return sorted(items, key=lambda x: _dec(x.get(key)), reverse=True)[:n]


class FinancialIntelligenceService:
    def __init__(
        self,
        finance_center: CorporateFinanceCenterService,
        cash_flow: CorporateCashFlowService | None = None,
    ) -> None:
        self._fc = finance_center
        self._flow = cash_flow

    @staticmethod
    def snapshot_key(data_inicial: str, data_final: str, empresa_codigo: str | int | None, module: str) -> str:
        suffix = empresa_snapshot_suffix(empresa_codigo)
        return f"finance:{module}:{data_inicial}:{data_final}:{suffix}"

    async def build(
        self,
        filters: FinancialOverviewFilters,
        empresa_codigo_raw: str | int | None,
    ) -> WebPostoResponse:
        raw, err = await self._fc._overview._load_filtered_expenses(filters)
        if err is not None:
            return err
        expenses = self._fc._filter_expenses(raw, filters)

        by_desc: dict[str, dict[str, Any]] = {}
        by_supplier: dict[str, dict[str, Any]] = {}
        by_category_v2: dict[str, Decimal] = defaultdict(Decimal)
        by_category_legacy: dict[str, Decimal] = defaultdict(Decimal)
        by_empresa: dict[str, Decimal] = defaultdict(Decimal)
        by_centro: dict[str, Decimal] = defaultdict(Decimal)
        total = Decimal("0")
        outros_valor = Decimal("0")
        v1_outros_valor = Decimal("0")
        v3_outros_valor = Decimal("0")
        identified_from_outros = Decimal("0")
        plano_conta_hits = 0

        for row in expenses:
            val = _dec(row.get("valor"))
            total += val
            desc = str(row.get("planoConta") or "")
            cat_v3 = str(row.get("categoriaLogosV3") or row.get("categoriaLogosV2") or row.get("categoriaLogos") or "OUTROS")
            cat_legacy = str(row.get("categoriaLogos") or "OUTROS")
            by_category_v2[cat_v3] += val
            by_category_legacy[cat_legacy] += val
            if cat_legacy == "OUTROS":
                outros_valor += val
            if cat_v3 == "OUTROS":
                v3_outros_valor += val
            if str(row.get("classificationSource") or "") == "PLANO_CONTA":
                plano_conta_hits += 1
            if classify_logos_expense_v1_baseline(desc) == "OUTROS":
                v1_outros_valor += val
                if cat_v3 != "OUTROS":
                    identified_from_outros += val
            emp = str(row.get("empresaCodigo") or "")
            by_empresa[emp] += val
            centro = str(row.get("centroCusto") or "(sem centro)")
            by_centro[centro] += val

            dkey = desc[:120] or "(vazio)"
            if dkey not in by_desc:
                by_desc[dkey] = {"descricao": dkey, "count": 0, "valor": "0.00", "categoriaLogosV2": cat_v2}
            by_desc[dkey]["count"] += 1
            by_desc[dkey]["valor"] = _q2(_dec(by_desc[dkey]["valor"]) + val)

            supplier = desc.split(" - ")[-1].strip() if " - " in desc else desc[:40]
            if supplier not in by_supplier:
                by_supplier[supplier] = {"fornecedor": supplier, "count": 0, "valor": "0.00"}
            by_supplier[supplier]["count"] += 1
            by_supplier[supplier]["valor"] = _q2(_dec(by_supplier[supplier]["valor"]) + val)

        pct_outros = float(outros_valor / total * 100) if total else 0.0
        pct_v3_outros = float(v3_outros_valor / total * 100) if total else 0.0
        pct_v1_outros = float(v1_outros_valor / total * 100) if total else 0.0
        pct_identified_from_outros = float(identified_from_outros / v1_outros_valor * 100) if v1_outros_valor else 0.0
        pct_plano_source = round(plano_conta_hits / max(len(expenses), 1) * 100, 2)

        branch_compare = [
            {"empresaCodigo": k, "valor": _q2(v), "participacao": _q2(v / total * 100 if total else Decimal("0"))}
            for k, v in sorted(by_empresa.items(), key=lambda x: -x[1])
        ]

        category_rank = [
            {"categoriaLogosV2": k, "valor": _q2(v), "participacao": _q2(v / total * 100 if total else Decimal("0"))}
            for k, v in sorted(by_category_v2.items(), key=lambda x: -x[1])
        ]

        centro_rank = [
            {"centroCusto": k, "valor": _q2(v)} for k, v in sorted(by_centro.items(), key=lambda x: -x[1])[:20]
        ]

        anomalies: list[dict[str, Any]] = []
        avg = total / len(expenses) if expenses else Decimal("0")
        for row in expenses:
            val = _dec(row.get("valor"))
            if avg and val > avg * 5:
                anomalies.append(
                    {
                        "tipo": "DESPESA_ANORMAL",
                        "descricao": row.get("planoConta"),
                        "valor": row.get("valor"),
                        "empresaCodigo": row.get("empresaCodigo"),
                        "categoriaLogosV2": row.get("categoriaLogosV2"),
                    }
                )
        anomalies = sorted(anomalies, key=lambda x: _dec(x.get("valor")), reverse=True)[:20]

        concentration = {}
        if branch_compare:
            top = _dec(branch_compare[0]["valor"])
            concentration = {
                "filialDominante": branch_compare[0]["empresaCodigo"],
                "valor": branch_compare[0]["valor"],
                "participacao": branch_compare[0]["participacao"],
            }

        flow_insights: dict[str, Any] = {}
        if self._flow:
            flow_resp = await self._flow.build(filters, empresa_codigo_raw)
            if flow_resp.success and flow_resp.data:
                flow_insights = flow_resp.data.get("insights") or {}

        payload = {
            "classification": {
                "totalValor": _q2(total),
                "totalRegistros": len(expenses),
                "outrosValor": _q2(outros_valor),
                "outrosPercent": round(pct_outros, 2),
                "outrosV3Percent": round(pct_v3_outros, 2),
                "outrosV1Percent": round(pct_v1_outros, 2),
                "outrosV1Valor": _q2(v1_outros_valor),
                "outrosV3Valor": _q2(v3_outros_valor),
                "identifiedFromOutrosPercent": round(pct_identified_from_outros, 2),
                "identifiedFromOutrosValor": _q2(identified_from_outros),
                "planoContaSourcePercent": pct_plano_source,
                "identifiedPercent": round((total - outros_valor) / total * 100 if total else 0, 2),
                "porCategoriaLogosV2": {k: _q2(v) for k, v in sorted(by_category_v2.items())},
                "porCategoriaLogos": {k: _q2(v) for k, v in sorted(by_category_legacy.items())},
            },
            "topExpenses": _top_n(list(by_desc.values()), "valor"),
            "topSuppliers": _top_n(list(by_supplier.values()), "valor"),
            "topCategories": category_rank[:20],
            "topCostCenters": centro_rank,
            "branchComparison": branch_compare,
            "concentration": concentration,
            "anomalies": anomalies,
            "monthlyEvolution": [{"periodo": filters.data_inicial[:7], "valor": _q2(total)}],
            "cashFlowInsights": flow_insights,
            "snapshotKeys": {
                "intelligence": self.snapshot_key(filters.data_inicial, filters.data_final, empresa_codigo_raw, "intelligence"),
                "topExpenses": self.snapshot_key(filters.data_inicial, filters.data_final, empresa_codigo_raw, "top-expenses"),
                "topSuppliers": self.snapshot_key(filters.data_inicial, filters.data_final, empresa_codigo_raw, "top-suppliers"),
            },
        }
        return WebPostoResponse.ok(payload)
