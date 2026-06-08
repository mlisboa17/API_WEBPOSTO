"""Financial Health Score V3 — F01.4-B."""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from src.models.response_model import WebPostoResponse
from src.services.corporate_finance_center_service import CorporateFinanceCenterService
from src.services.financial_intelligence_advanced_service import FinancialIntelligenceAdvancedService
from src.services.multiselect_utils import empresa_snapshot_suffix
from src.services.network_financial_overview_service import FinancialOverviewFilters

LOGGER = logging.getLogger(__name__)


def _dec(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")


def _clamp(value: float) -> int:
    return max(0, min(100, int(round(value))))


class FinancialHealthScoreV3Service:
    def __init__(
        self,
        finance_center: CorporateFinanceCenterService,
        advanced: FinancialIntelligenceAdvancedService,
    ) -> None:
        self._fc = finance_center
        self._advanced = advanced

    @staticmethod
    def snapshot_key(data_inicial: str, data_final: str, empresa_codigo: str | int | None) -> str:
        suffix = empresa_snapshot_suffix(empresa_codigo)
        return f"finance:health-score-v3:{data_inicial}:{data_final}:{suffix}"

    async def build(
        self,
        filters: FinancialOverviewFilters,
        empresa_codigo_raw: str | int | None,
    ) -> WebPostoResponse:
        adv_resp = await self._advanced.build(filters, empresa_codigo_raw)
        if not adv_resp.success:
            return adv_resp
        adv = adv_resp.data or {}
        dq = adv.get("dataQuality") or {}
        benchmark = adv.get("benchmark") or {}
        filiais = benchmark.get("filiais") or []

        plano_score = float((dq.get("components") or {}).get("planoConta") or 0)
        centro_score = float((dq.get("components") or {}).get("centroCusto") or 0)

        branch_scores = []
        for f in filiais:
            idx = float(f.get("indiceBenchmarkRede") or 1)
            bench_component = max(0, 100 - (idx - 1) * 80)
            score = _clamp(plano_score * 0.4 + centro_score * 0.3 + bench_component * 0.3)
            branch_scores.append(
                {
                    "empresaCodigo": f.get("empresaCodigo"),
                    "scoreV3": score,
                    "components": {
                        "planoConta": round(plano_score * 0.4, 1),
                        "centroCusto": round(centro_score * 0.3, 1),
                        "benchmarkRede": round(bench_component * 0.3, 1),
                    },
                    "indiceBenchmarkRede": f.get("indiceBenchmarkRede"),
                    "classificacao": f.get("classificacaoRede"),
                }
            )

        branch_scores.sort(key=lambda x: x["scoreV3"], reverse=True)
        network = _clamp(sum(b["scoreV3"] for b in branch_scores) / len(branch_scores) if branch_scores else 0)

        payload = {
            "networkScoreV3": network,
            "networkLevel": "saudavel" if network >= 70 else "atencao" if network >= 50 else "critico",
            "dataQualityScore": dq.get("score"),
            "branches": branch_scores,
            "ranking": [{"empresaCodigo": b["empresaCodigo"], "scoreV3": b["scoreV3"]} for b in branch_scores],
            "healthiest": branch_scores[0] if branch_scores else None,
            "critical": branch_scores[-1] if branch_scores else None,
            "composition": {"planoConta": "40%", "centroCusto": "30%", "benchmarkRede": "30%"},
            "snapshotKey": self.snapshot_key(filters.data_inicial, filters.data_final, empresa_codigo_raw),
        }
        return WebPostoResponse.ok(payload)
