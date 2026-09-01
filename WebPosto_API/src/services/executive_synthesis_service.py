"""Síntese executiva para Dashboard do Presidente — Sprint 44."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExecutiveSynthesis(BaseModel):
    """Resumo executivo consolidado para visualização < 1s."""

    model_config = ConfigDict(frozen=True)

    period_start: str
    period_end: str
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    cache_hit: bool = False

    total_revenue: float | None = None
    total_gross_margin: float | None = None
    gross_margin_pct: float | None = None

    fuel_revenue: float | None = None
    fuel_margin_per_liter: float | None = None
    fuel_liters_sold: float | None = None

    convenience_revenue: float | None = None
    convenience_ticket_avg: float | None = None

    lubricants_revenue: float | None = None

    pending_expenses_count: int = 0
    pending_expenses_value: float = 0.0
    dre_status: str = "BLOQUEADO"
    dre_released_lines: int = 0
    dre_total_lines: int = 0

    critical_alerts: list[dict[str, Any]] = Field(default_factory=list)
    cash_alerts: list[dict[str, Any]] = Field(default_factory=list)

    companies_analyzed: int = 0
    data_completeness_pct: float = 0.0


class ExecutiveSynthesisService:
    """Gera resumo executivo consolidado com cache para resposta < 1s."""

    CACHE_TTL_SECONDS = 300

    def __init__(
        self,
        dre_service: Any = None,
        fuel_service: Any = None,
        convenience_service: Any = None,
        alert_service: Any = None,
        pending_service: Any = None,
    ) -> None:
        self._dre = dre_service
        self._fuel = fuel_service
        self._convenience = convenience_service
        self._alerts = alert_service
        self._pending = pending_service
        self._cache: dict[str, tuple[datetime, ExecutiveSynthesis]] = {}

    def _cache_key(self, start: str, end: str, company: int | None) -> str:
        return f"{start}:{end}:{company or 'all'}"

    def _get_cached(self, key: str) -> ExecutiveSynthesis | None:
        if key not in self._cache:
            return None
        cached_at, synthesis = self._cache[key]
        if (datetime.now(timezone.utc) - cached_at).total_seconds() > self.CACHE_TTL_SECONDS:
            del self._cache[key]
            return None
        return synthesis

    def _set_cache(self, key: str, synthesis: ExecutiveSynthesis) -> None:
        self._cache[key] = (datetime.now(timezone.utc), synthesis)

    async def build(
        self,
        start: str,
        end: str,
        company_code: int | None = None,
        force_refresh: bool = False,
    ) -> ExecutiveSynthesis:
        key = self._cache_key(start, end, company_code)

        if not force_refresh:
            cached = self._get_cached(key)
            if cached:
                return ExecutiveSynthesis(
                    **{**cached.model_dump(), "cache_hit": True}
                )

        dre_data, fuel_data, alerts_data, pending_data = await asyncio.gather(
            self._fetch_dre(start, end, company_code),
            self._fetch_fuel(start, end, company_code),
            self._fetch_alerts(end),
            self._fetch_pending(start, end, company_code),
            return_exceptions=True,
        )

        dre = dre_data if isinstance(dre_data, dict) else {}
        fuel = fuel_data if isinstance(fuel_data, dict) else {}
        alerts = self._normalize_alerts(alerts_data)
        pending = pending_data if isinstance(pending_data, dict) else {}

        synthesis = self._consolidate(start, end, dre, fuel, alerts, pending)
        self._set_cache(key, synthesis)
        return synthesis

    async def _fetch_dre(self, start: str, end: str, company: int | None) -> dict[str, Any]:
        if not self._dre:
            return {}
        try:
            return await self._dre.build(start, end, company)
        except Exception:
            return {}

    async def _fetch_fuel(self, start: str, end: str, company: int | None) -> dict[str, Any]:
        if not self._fuel:
            return {}
        try:
            response = await self._fuel.build(start, end, company)
            return response.data if hasattr(response, "data") else response
        except Exception:
            return {}

    async def _fetch_alerts(self, date: str) -> list[dict[str, Any]]:
        if not self._alerts:
            return []
        try:
            return self._normalize_alerts(self._alerts.list(date))
        except Exception:
            return []

    @staticmethod
    def _normalize_alerts(payload: Any) -> list[dict[str, Any]]:
        """DepartmentalAlertService.list() devolve dict; nunca iterar o dict raiz."""
        if isinstance(payload, Exception) or payload is None:
            return []
        if isinstance(payload, list):
            return [a for a in payload if isinstance(a, dict)]
        if isinstance(payload, dict):
            raw = payload.get("alerts")
            if isinstance(raw, list):
                return [a for a in raw if isinstance(a, dict)]
            if isinstance(raw, dict):
                return [a for a in raw.values() if isinstance(a, dict)]
        return []

    async def _fetch_pending(self, start: str, end: str, company: int | None) -> dict[str, Any]:
        if not self._pending:
            return {}
        try:
            return self._pending.group_pending_expenses([]).model_dump()
        except Exception:
            return {}

    def _consolidate(
        self,
        start: str,
        end: str,
        dre: dict[str, Any],
        fuel: dict[str, Any],
        alerts: list[dict[str, Any]],
        pending: dict[str, Any],
    ) -> ExecutiveSynthesis:
        lines = [line for line in (dre.get("lines") or []) if isinstance(line, dict)]
        released = [line for line in lines if line.get("status") == "LIBERADO"]

        total_revenue = Decimal("0")
        total_margin = Decimal("0")
        fuel_revenue = Decimal("0")
        conv_revenue = Decimal("0")
        lub_revenue = Decimal("0")
        companies = set()

        for line in released:
            companies.add(line.get("companyCode"))
            revenue = Decimal(str(line.get("revenue") or 0))
            margin = Decimal(str(line.get("grossMargin") or 0))
            dept = line.get("department")

            total_revenue += revenue
            total_margin += margin

            if dept == "combustiveis":
                fuel_revenue += revenue
            elif dept == "conveniencia":
                conv_revenue += revenue
            elif dept == "lubrificantes":
                lub_revenue += revenue

        fuel_liters = Decimal("0")
        fuel_margin_liter = None
        for empresa in (fuel.get("empresas") or []):
            if not isinstance(empresa, dict):
                continue
            for prod in (empresa.get("produtos") or []):
                if not isinstance(prod, dict):
                    continue
                fuel_liters += Decimal(str(prod.get("litrosVendidos") or 0))

        if fuel_liters > 0 and fuel_revenue > 0:
            fuel_margin_liter = float(
                (fuel_revenue * Decimal("0.05") / fuel_liters).quantize(Decimal("0.0001"))
            )

        critical_alerts = [a for a in alerts if a.get("severity") == "CRITICAL"]
        cash_alerts = [
            a
            for a in alerts
            if "caixa" in (a.get("type") or a.get("rule") or a.get("message") or "").lower()
        ]

        gross_margin_pct = None
        if total_revenue > 0:
            gross_margin_pct = float((total_margin / total_revenue * 100).quantize(Decimal("0.01")))

        completeness = len(released) / len(lines) * 100 if lines else 0

        return ExecutiveSynthesis(
            period_start=start,
            period_end=end,
            total_revenue=float(total_revenue) if total_revenue else None,
            total_gross_margin=float(total_margin) if total_margin else None,
            gross_margin_pct=gross_margin_pct,
            fuel_revenue=float(fuel_revenue) if fuel_revenue else None,
            fuel_margin_per_liter=fuel_margin_liter,
            fuel_liters_sold=float(fuel_liters) if fuel_liters else None,
            convenience_revenue=float(conv_revenue) if conv_revenue else None,
            convenience_ticket_avg=None,
            lubricants_revenue=float(lub_revenue) if lub_revenue else None,
            pending_expenses_count=pending.get("total_pending_count", 0),
            pending_expenses_value=pending.get("total_pending_value", 0.0),
            dre_status="LIBERADO" if dre.get("allReleased") else "BLOQUEADO",
            dre_released_lines=len(released),
            dre_total_lines=len(lines),
            critical_alerts=critical_alerts[:5],
            cash_alerts=cash_alerts[:3],
            companies_analyzed=len(companies),
            data_completeness_pct=round(completeness, 1),
        )
