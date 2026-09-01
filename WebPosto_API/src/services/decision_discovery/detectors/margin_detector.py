"""MarginDetector — desvios de margem de combustível (compra vs venda vs meta)."""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from src.domain.adelaide.abastecimento_filters import valor_financeiro_abastecimento
from src.services.analytics_multiselect import build_overview_filters
from src.services.decision_discovery.base_detector import BaseDetector
from src.services.decision_discovery.models import (
    ConfidenceFactors,
    DecisionCandidate,
    DecisionCategory,
    ImpactType,
    MoneyConfidence,
    MoneyFound,
)
from src.services.network_financial_overview_service import NetworkFinancialOverviewService
from src.services.performance.performance_metrics import performance_metrics
from src.services.snapshot_store import SnapshotStore
from src.utils.utc_datetime import age_seconds, utc_now_iso

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_MARGIN_TARGET_PCT = 0.10
MIN_MARGIN_GAP_PCT = 0.02
MIN_IMPACT_BRL = 3000.0
MIN_CONFIDENCE = 0.80


class MarginDetector(BaseDetector):
    """Detecta compressão de margem comparando preço de compra e venda históricos."""

    CURRENT_PERIOD_TTL_SECONDS = 5 * 60
    CLOSED_PERIOD_TTL_SECONDS = 24 * 60 * 60
    _cache_store: SnapshotStore | None = None

    def __init__(self) -> None:
        super().__init__(detector_name="MarginDetector")
        if MarginDetector._cache_store is None:
            MarginDetector._cache_store = SnapshotStore(
                "snapshots/discovery_margin",
                MarginDetector.CLOSED_PERIOD_TTL_SECONDS,
            )

    @classmethod
    def _cache_key(cls, tenant_id: str, start: str, end: str) -> str:
        return f"discovery_margin:{tenant_id}:{tenant_id}:{start}:{end}"

    @classmethod
    def _period_ttl(cls, data_final: str) -> float:
        try:
            if datetime.fromisoformat(data_final).date() >= datetime.now().date():
                return cls.CURRENT_PERIOD_TTL_SECONDS
        except ValueError:
            pass
        return cls.CLOSED_PERIOD_TTL_SECONDS

    async def detect(
        self,
        tenant_code: str,
        data_inicial: str,
        data_final: str,
        **kwargs: Any,
    ) -> Union[Optional[DecisionCandidate], List[DecisionCandidate]]:
        try:
            payload = await self._fetch_margin_bundle(
                tenant_code=tenant_code,
                data_inicial=data_inicial,
                data_final=data_final,
                webposto_api_key=kwargs.get("webposto_api_key"),
            )
            if not payload:
                return None

            analyses = self._analyze_margin_deviations(payload)
            if not analyses:
                return None

            tenant_name = kwargs.get("tenant_name", tenant_code)
            candidates: List[DecisionCandidate] = []
            for analysis in analyses:
                if analysis["confidence"] < MIN_CONFIDENCE:
                    continue
                if analysis["impact_brl"] < MIN_IMPACT_BRL:
                    continue
                candidates.append(
                    self._create_candidate(
                        tenant_code,
                        tenant_name,
                        data_inicial,
                        data_final,
                        analysis,
                    )
                )
            if not candidates:
                return None
            return candidates[0] if len(candidates) == 1 else candidates
        except Exception as exc:
            self.log("detection_error", {"error": str(exc)}, level="error")
            return None

    async def _fetch_margin_bundle(
        self,
        tenant_code: str,
        data_inicial: str,
        data_final: str,
        webposto_api_key: str | None,
    ) -> Optional[Dict[str, Any]]:
        store = self._cache_store
        key = self._cache_key(tenant_code, data_inicial, data_final)
        if store:
            stored, _ = store.load_stale(key)
            if stored and stored.get("margin_data"):
                ttl = self._period_ttl(data_final)
                try:
                    age = age_seconds(str(stored.get("lastUpdated")))
                except ValueError:
                    age = ttl + 1
                if age <= ttl:
                    performance_metrics.record_fuel_cache_hit()
                    return dict(stored["margin_data"])
            performance_metrics.record_fuel_cache_miss()

        live = await self._fetch_live(
            tenant_code, data_inicial, data_final, webposto_api_key
        )
        if live and store:
            store.save(
                key,
                {
                    "lastUpdated": utc_now_iso(),
                    "margin_data": {**live, "cache_status": "MISS"},
                },
            )
        return live

    async def _fetch_live(
        self,
        tenant_code: str,
        data_inicial: str,
        data_final: str,
        webposto_api_key: str | None,
    ) -> Optional[Dict[str, Any]]:
        from src.gateway.webposto_client import WebPostoClient
        from src.services.analytics_service import AnalyticsService

        client = WebPostoClient.for_api_key(webposto_api_key) if webposto_api_key else WebPostoClient()
        overview = NetworkFinancialOverviewService(client)
        analytics = AnalyticsService(overview)
        filters = build_overview_filters(data_inicial, data_final, tenant_code)

        fuel_resp = await analytics.get_fuel_summary(filters)
        fuel_rows = fuel_resp.data if fuel_resp.success and isinstance(fuel_resp.data, list) else []

        abast_resp = await client.call_endpoint(
            "abastecimento",
            params={
                "dataInicial": data_inicial,
                "dataFinal": data_final,
                "empresaCodigo": int(tenant_code),
            },
        )
        purchase_rows: list[dict] = []
        if abast_resp.success:
            raw = abast_resp.data
            if isinstance(raw, list):
                purchase_rows = [r for r in raw if isinstance(r, dict)]
            elif isinstance(raw, dict):
                purchase_rows = [
                    r
                    for r in (raw.get("resultados") or raw.get("data") or [])
                    if isinstance(r, dict)
                ]

        margin_target = self._load_margin_target_pct(tenant_code, data_inicial, data_final)

        return {
            "tenant_id": tenant_code,
            "fuel_rows": fuel_rows,
            "purchase_rows": purchase_rows,
            "margin_target_pct": margin_target,
            "data_quality": 0.9 if fuel_rows and purchase_rows else 0.65 if fuel_rows else 0.4,
        }

    @staticmethod
    def _load_margin_target_pct(
        tenant_code: str,
        data_inicial: str,
        data_final: str,
    ) -> float:
        scorecard_dir = ROOT / "snapshots" / "executive_scorecard"
        if not scorecard_dir.is_dir():
            return DEFAULT_MARGIN_TARGET_PCT
        patterns = [
            f"executive_scorecard_{data_inicial}_{data_final}_{tenant_code}.json",
            f"executive_scorecard_{data_inicial}_{data_final}_all.json",
            f"executive_scorecard_*_{tenant_code}.json",
        ]
        for pattern in patterns:
            for path in sorted(scorecard_dir.glob(pattern), reverse=True):
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                data = payload.get("data") or payload
                fin = data.get("financialScorecard") or {}
                for key in ("margemRedePct", "margemOperacionalPct"):
                    try:
                        val = float(fin.get(key) or 0)
                        if val > 0:
                            return val / 100.0 if val > 1 else val
                    except (TypeError, ValueError):
                        continue
        return DEFAULT_MARGIN_TARGET_PCT

    def _aggregate_sales(self, rows: list[dict]) -> dict[str, dict[str, float]]:
        acc: dict[str, dict[str, float]] = defaultdict(lambda: {"litros": 0.0, "valor": 0.0})
        for row in rows:
            name = str(row.get("combustivel") or row.get("produto") or "").strip()
            if not name:
                continue
            try:
                litros = float(row.get("litros") or 0)
                valor = float(row.get("valor") or 0)
            except (TypeError, ValueError):
                continue
            if litros <= 0:
                continue
            acc[name]["litros"] += litros
            acc[name]["valor"] += valor
        return dict(acc)

    def _aggregate_purchases(self, rows: list[dict], tenant_code: str) -> dict[str, dict[str, float]]:
        acc: dict[str, dict[str, float]] = defaultdict(lambda: {"litros": 0.0, "valor": 0.0})
        for row in rows:
            empresa = str(row.get("empresaCodigo") or "")
            if empresa and empresa != tenant_code:
                continue
            name = str(
                row.get("descricaoProduto")
                or row.get("produto")
                or row.get("combustivel")
                or ""
            ).strip()
            if not name:
                continue
            try:
                litros = float(row.get("quantidade") or row.get("litros") or 0)
            except (TypeError, ValueError):
                litros = 0.0
            valor = float(valor_financeiro_abastecimento(row))
            if litros <= 0 and valor <= 0:
                continue
            if litros <= 0:
                unit = float(row.get("valorUnitario") or 0)
                if unit > 0 and valor > 0:
                    litros = valor / unit
            acc[name]["litros"] += litros
            acc[name]["valor"] += valor
        return dict(acc)

    def _analyze_margin_deviations(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        sales = self._aggregate_sales(payload.get("fuel_rows") or [])
        tenant = str(payload.get("tenant_id") or "")
        purchases = self._aggregate_purchases(payload.get("purchase_rows") or [], tenant)
        target = float(payload.get("margin_target_pct") or DEFAULT_MARGIN_TARGET_PCT)
        analyses: list[dict[str, Any]] = []

        all_products = set(sales) | set(purchases)
        for product in all_products:
            sale = sales.get(product) or {"litros": 0.0, "valor": 0.0}
            purchase = purchases.get(product) or {"litros": 0.0, "valor": 0.0}
            litros = sale["litros"]
            if litros <= 0:
                continue
            sale_price = sale["valor"] / litros if litros > 0 else 0.0
            purchase_litros = purchase["litros"] or litros
            purchase_price = (
                purchase["valor"] / purchase_litros if purchase_litros > 0 else sale_price * (1 - target)
            )
            if sale_price <= 0:
                continue
            margin_real = (sale_price - purchase_price) / sale_price
            gap = target - margin_real
            if gap < MIN_MARGIN_GAP_PCT:
                continue
            impact = litros * sale_price * gap
            conf = self._confidence(payload, litros, purchase["litros"] > 0)
            analyses.append(
                {
                    "product_name": product,
                    "litros": litros,
                    "sale_price": sale_price,
                    "purchase_price": purchase_price,
                    "margin_real_pct": margin_real,
                    "margin_target_pct": target,
                    "margin_gap_pct": gap,
                    "impact_brl": impact,
                    "confidence": conf,
                    "money_found": MoneyFound(
                        at_risk=impact,
                        at_risk_type=MoneyConfidence.ESTIMATED,
                        recoverable=impact * 0.5,
                        recoverable_type=MoneyConfidence.ESTIMATED,
                    ),
                    "evidence": {
                        "product_name": product,
                        "current_margin": margin_real,
                        "target_margin": target,
                        "sale_price": round(sale_price, 4),
                        "purchase_price": round(purchase_price, 4),
                        "litros": round(litros, 2),
                    },
                    "baseline": {
                        "baseline_value": target,
                        "current_value": margin_real,
                        "period": "preço médio compra vs venda no período",
                    },
                }
            )
        analyses.sort(key=lambda x: x["impact_brl"], reverse=True)
        return analyses

    def _confidence(self, payload: dict, litros: float, has_purchase: bool) -> float:
        dq = float(payload.get("data_quality") or 0.7)
        volume_factor = min(1.0, litros / 10_000.0)
        purchase_factor = 0.92 if has_purchase else 0.72
        factors = ConfidenceFactors(
            data_quality=dq * volume_factor,
            comparison_validity=purchase_factor,
            period_adequacy=0.88,
            calculation_reliability=0.93,
        )
        return factors.overall_confidence()

    def _create_candidate(
        self,
        tenant_code: str,
        tenant_name: str,
        period_start: str,
        period_end: str,
        analysis: dict[str, Any],
    ) -> DecisionCandidate:
        impact = analysis["impact_brl"]
        product = analysis["product_name"]
        gap_pct = analysis["margin_gap_pct"]
        title = (
            f"Margem de {product} {gap_pct:.1%} abaixo da meta "
            f"(~R$ {impact:,.0f} em risco estimado)"
        )
        summary = (
            f"{tenant_name}: margem realizada de {analysis['margin_real_pct']:.1%} vs meta "
            f"{analysis['margin_target_pct']:.1%} em {product}. "
            f"Compra média R$ {analysis['purchase_price']:.3f}/L · "
            f"Venda média R$ {analysis['sale_price']:.3f}/L."
        )
        return DecisionCandidate(
            id=str(uuid.uuid4()),
            detector_name=self.detector_name,
            title=title,
            summary=summary,
            category=DecisionCategory.MARGIN,
            impact_type=ImpactType.MARGIN,
            tenant=tenant_code,
            tenant_name=tenant_name,
            period_start=period_start,
            period_end=period_end,
            money_found=analysis["money_found"],
            confidence=analysis["confidence"],
            confidence_factors=ConfidenceFactors(
                data_quality=0.85,
                comparison_validity=0.88,
                period_adequacy=0.88,
                calculation_reliability=0.93,
            ),
            recommended_actions=[
                f"Revisar política de preço de {product} na filial",
                "Conferir últimas notas de fornecedor (preço de compra)",
                "Comparar margem realizada com benchmark da rede",
            ],
            estimated_execution_time=20,
            evidence=analysis["evidence"],
            baseline_used=analysis["baseline"],
            source_endpoints=[
                "/api/v1/sales/fuel-summary",
                "/INTEGRACAO/ABASTECIMENTO",
                "/api/v1/fuel/executive",
            ],
        )
