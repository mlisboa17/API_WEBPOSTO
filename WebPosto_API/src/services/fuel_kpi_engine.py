from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class FuelKpiEngine:
    """Calcula KPIs executivos com base no resumo de combustiveis."""

    @staticmethod
    def _safe_pct(value: float, total: float) -> float:
        if total <= 0:
            return 0.0
        return round((value / total) * 100, 2)

    @staticmethod
    def _top_item(items: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
        if not items:
            return None
        return max(items, key=lambda item: float(item.get(key, 0.0) or 0.0))

    def build(self, summary: dict[str, Any]) -> dict[str, Any]:
        litros_total = float(summary.get("litrosTotal", 0.0) or 0.0)
        combustiveis = summary.get("combustiveis", []) or []
        filiais = summary.get("filiais", []) or []

        lider_combustivel = self._top_item(combustiveis, "litros")
        lider_filial = self._top_item(filiais, "litros")

        diesel_litros = sum(
            float(item.get("litros", 0.0) or 0.0)
            for item in combustiveis
            if "diesel" in str(item.get("categoria", "")).lower()
        )
        gasolina_litros = sum(
            float(item.get("litros", 0.0) or 0.0)
            for item in combustiveis
            if "gasolina" in str(item.get("categoria", "")).lower()
        )
        etanol_litros = sum(
            float(item.get("litros", 0.0) or 0.0)
            for item in combustiveis
            if "etanol" in str(item.get("categoria", "")).lower()
        )

        return {
            "litrosVendidos": round(litros_total, 3),
            "combustivelLider": {
                "nome": lider_combustivel.get("combustivel") if lider_combustivel else "Sem dados",
                "litros": round(float(lider_combustivel.get("litros", 0.0) or 0.0), 3) if lider_combustivel else 0.0,
            },
            "filialLider": {
                "empresaCodigo": lider_filial.get("empresaCodigo") if lider_filial else None,
                "nomeFilial": lider_filial.get("nomeFilial") if lider_filial else "Sem dados",
                "litros": round(float(lider_filial.get("litros", 0.0) or 0.0), 3) if lider_filial else 0.0,
            },
            "participacaoDiesel": self._safe_pct(diesel_litros, litros_total),
            "participacaoGasolina": self._safe_pct(gasolina_litros, litros_total),
            "participacaoEtanol": self._safe_pct(etanol_litros, litros_total),
        }
