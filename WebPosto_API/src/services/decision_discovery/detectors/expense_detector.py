"""Expense Loss Detector — VALUE-03."""

from __future__ import annotations

import statistics
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

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


class ExpenseDetector(BaseDetector):
    """Detecta anomalias explicáveis em despesas reais (ERP WebPosto)."""

    MIN_IMPACT_BRL = 3000.0
    MIN_CONFIDENCE = 0.80
    MIN_DAYS = 21
    MIN_PCT_SPIKE = 0.20
    ANALYSIS_DAYS = 30

    CURRENT_PERIOD_TTL_SECONDS = 5 * 60
    CLOSED_PERIOD_TTL_SECONDS = 24 * 60 * 60

    _cache_store: SnapshotStore | None = None

    def __init__(self) -> None:
        super().__init__(detector_name="ExpenseDetector")
        if ExpenseDetector._cache_store is None:
            ExpenseDetector._cache_store = SnapshotStore(
                "snapshots/discovery_expense",
                ExpenseDetector.CLOSED_PERIOD_TTL_SECONDS,
            )

    @classmethod
    def _cache_key(cls, tenant_id: str, empresa_codigo: str, start: str, end: str) -> str:
        return f"discovery_expense:{tenant_id}:{empresa_codigo}:{start}:{end}"

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
            end = datetime.fromisoformat(data_final).date()
            start = end - timedelta(days=self.ANALYSIS_DAYS - 1)
            cur_start = start.isoformat()
            cur_end = end.isoformat()
            base_end = start - timedelta(days=1)
            base_start = (base_end - timedelta(days=self.ANALYSIS_DAYS - 1)).isoformat()

            payload = await self._fetch_expense_bundle(
                tenant_code=tenant_code,
                cur_start=cur_start,
                cur_end=cur_end,
                base_start=base_start,
                base_end=base_end.isoformat(),
                webposto_api_key=kwargs.get("webposto_api_key"),
            )
            if not payload:
                return None

            analyses = self._detect_anomalies(payload)
            if not analyses:
                return None

            tenant_name = kwargs.get("tenant_name", tenant_code)
            candidates: List[DecisionCandidate] = []
            for analysis in analyses:
                if analysis["confidence"] < self.MIN_CONFIDENCE:
                    continue
                if analysis["impact_brl"] < self.MIN_IMPACT_BRL:
                    continue
                candidates.append(
                    self._create_candidate(tenant_code, tenant_name, cur_start, cur_end, analysis)
                )
            if not candidates:
                return None
            return candidates[0] if len(candidates) == 1 else candidates
        except Exception as exc:
            self.log("detection_error", {"error": str(exc)}, level="error")
            return None

    async def _fetch_expense_bundle(
        self,
        tenant_code: str,
        cur_start: str,
        cur_end: str,
        base_start: str,
        base_end: str,
        webposto_api_key: str | None,
    ) -> Optional[Dict[str, Any]]:
        store = self._cache_store
        key = self._cache_key(tenant_code, tenant_code, cur_start, cur_end)
        if store:
            stored, _ = store.load_stale(key)
            if stored and stored.get("expense_data"):
                ttl = self._period_ttl(cur_end)
                try:
                    age = age_seconds(str(stored.get("lastUpdated")))
                except ValueError:
                    age = ttl + 1
                if age <= ttl:
                    performance_metrics.record_expense_cache_hit()
                    return dict(stored["expense_data"])
            performance_metrics.record_expense_cache_miss()

        live = await self._fetch_live(
            tenant_code, cur_start, cur_end, base_start, base_end, webposto_api_key
        )
        if live and store:
            store.save(
                key,
                {
                    "lastUpdated": utc_now_iso(),
                    "expense_data": {
                        **live,
                        "tenant_id": tenant_code,
                        "period_start": cur_start,
                        "period_end": cur_end,
                        "cache_status": "MISS",
                    },
                },
            )
        return live

    async def _fetch_live(
        self,
        tenant_code: str,
        cur_start: str,
        cur_end: str,
        base_start: str,
        base_end: str,
        webposto_api_key: str | None,
    ) -> Optional[Dict[str, Any]]:
        from src.gateway.webposto_client import WebPostoClient

        client = WebPostoClient.for_api_key(webposto_api_key) if webposto_api_key else WebPostoClient()
        overview = NetworkFinancialOverviewService(client)
        cur_f = build_overview_filters(cur_start, cur_end, tenant_code)
        base_f = build_overview_filters(base_start, base_end, tenant_code)

        cur_rows, cur_err = await overview._load_filtered_expenses(cur_f)
        base_rows, base_err = await overview._load_filtered_expenses(base_f)
        if cur_err and not cur_rows:
            return None

        titulo_cur = await overview._fetch_titulo_pagar(cur_f, int(tenant_code))
        titulo_base = await overview._fetch_titulo_pagar(base_f, int(tenant_code))

        def norm_titulos(resp) -> list[dict]:
            if not resp.success:
                return []
            out = []
            for row in overview._rows(resp.data):
                item = overview._normalize_titulo_pagar(row)
                if item and overview._titulo_matches(item, cur_f if resp is titulo_cur else base_f):
                    out.append(item)
            return out

        return {
            "current_expenses": cur_rows,
            "baseline_expenses": base_rows,
            "current_titulos": norm_titulos(titulo_cur),
            "baseline_titulos": norm_titulos(titulo_base),
            "data_quality": 0.9 if cur_rows and base_rows else 0.65,
        }

    def _sum_by(self, rows: list[dict], key_fn) -> dict[str, float]:
        acc: dict[str, float] = defaultdict(float)
        for row in rows:
            k = key_fn(row)
            if not k:
                continue
            try:
                acc[k] += float(row.get("valor") or 0)
            except (TypeError, ValueError):
                continue
        return dict(acc)

    def _detect_anomalies(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        cur = payload["current_expenses"]
        base = payload["baseline_expenses"]
        analyses: list[dict[str, Any]] = []

        cur_cat = self._sum_by(cur, lambda r: str(r.get("planoConta") or "SEM_CATEGORIA"))
        base_cat = self._sum_by(base, lambda r: str(r.get("planoConta") or "SEM_CATEGORIA"))

        for cat, cur_val in cur_cat.items():
            base_val = base_cat.get(cat, 0.0)
            excess = cur_val - base_val
            if excess < self.MIN_IMPACT_BRL:
                continue
            pct = excess / base_val if base_val > 0 else 1.0
            if base_val > 0 and pct < self.MIN_PCT_SPIKE:
                continue
            cur_count = sum(1 for r in cur if str(r.get("planoConta") or "SEM_CATEGORIA") == cat)
            base_count = sum(1 for r in base if str(r.get("planoConta") or "SEM_CATEGORIA") == cat)
            conf = self._confidence(payload, cur_count, base_count, base_val > 0)
            analyses.append(
                self._analysis(
                    anomaly_type="CATEGORY_SPIKE",
                    title_cat=cat,
                    impact_brl=excess,
                    pct=pct,
                    cur_val=cur_val,
                    base_val=base_val,
                    confidence=conf,
                    evidence={
                        "category": cat,
                        "current_count": cur_count,
                        "baseline_count": base_count,
                        "anomaly_type": "CATEGORY_SPIKE",
                    },
                )
            )

        cur_sup = self._sum_by(payload["current_titulos"], lambda r: str(r.get("fornecedor") or "").strip())
        base_sup = self._sum_by(payload["baseline_titulos"], lambda r: str(r.get("fornecedor") or "").strip())
        for sup, cur_val in cur_sup.items():
            if not sup:
                continue
            base_val = base_sup.get(sup, 0.0)
            excess = cur_val - base_val
            if excess < self.MIN_IMPACT_BRL:
                continue
            pct = excess / base_val if base_val > 0 else 1.0
            if base_val > 0 and pct < self.MIN_PCT_SPIKE:
                continue
            conf = self._confidence(payload, 3, 2, base_val > 0)
            analyses.append(
                self._analysis(
                    anomaly_type="SUPPLIER_SPIKE",
                    title_cat=sup,
                    impact_brl=excess,
                    pct=pct,
                    cur_val=cur_val,
                    base_val=base_val,
                    confidence=conf * 0.95,
                    evidence={"supplier": sup, "anomaly_type": "SUPPLIER_SPIKE"},
                )
            )

        dup = self._duplicate_signals(cur)
        if dup:
            excess = dup["amount"]
            if excess >= self.MIN_IMPACT_BRL:
                analyses.append(
                    self._analysis(
                        anomaly_type="DUPLICATE_PAYMENT_SIGNAL",
                        title_cat=dup["label"],
                        impact_brl=excess,
                        pct=0.0,
                        cur_val=excess,
                        base_val=0.0,
                        confidence=self._confidence(payload, dup["pairs"], 0, False) * 0.85,
                        evidence=dup,
                    )
                )

        analyses.sort(key=lambda x: x["impact_brl"], reverse=True)
        return analyses

    def _duplicate_signals(self, rows: list[dict]) -> Optional[dict]:
        seen: dict[tuple, list] = defaultdict(list)
        for row in rows:
            cat = str(row.get("planoConta") or "")
            try:
                val = round(float(row.get("valor") or 0), 2)
            except (TypeError, ValueError):
                continue
            if val <= 0:
                continue
            key = (cat, val)
            seen[key].append(str(row.get("data") or ""))
        best = None
        for (cat, val), dates in seen.items():
            if len(dates) < 2:
                continue
            amount = val * (len(dates) - 1)
            item = {
                "anomaly_type": "DUPLICATE_PAYMENT_SIGNAL",
                "label": cat or "lançamento",
                "pairs": len(dates),
                "amount": amount,
                "valor": val,
                "dates": sorted(dates)[:6],
                "note": "POSSÍVEL DUPLICIDADE — requer conferência documental",
            }
            if not best or amount > best["amount"]:
                best = item
        return best

    def _confidence(self, payload: dict, cur_n: int, base_n: int, has_base: bool) -> float:
        dq = float(payload.get("data_quality") or 0.7)
        comp = min(1.0, (cur_n + base_n) / 20.0)
        base_ok = 0.85 if has_base else 0.55
        period = 0.9 if self.ANALYSIS_DAYS >= 28 else 0.75
        factors = ConfidenceFactors(
            data_quality=dq * comp,
            comparison_validity=base_ok,
            period_adequacy=period,
            calculation_reliability=0.95,
        )
        return factors.overall_confidence()

    def _analysis(
        self,
        *,
        anomaly_type: str,
        title_cat: str,
        impact_brl: float,
        pct: float,
        cur_val: float,
        base_val: float,
        confidence: float,
        evidence: dict,
    ) -> dict:
        factors = ConfidenceFactors(
            data_quality=0.85,
            comparison_validity=0.85 if base_val > 0 else 0.6,
            period_adequacy=0.9,
            calculation_reliability=0.95,
        )
        money = MoneyFound(
            at_risk=impact_brl,
            at_risk_type=MoneyConfidence.ESTIMATED,
            recoverable=impact_brl * 0.5,
            recoverable_type=MoneyConfidence.ESTIMATED,
        )
        return {
            "anomaly_type": anomaly_type,
            "title_cat": title_cat,
            "impact_brl": impact_brl,
            "impact_pct": pct,
            "confidence": confidence,
            "confidence_factors": factors,
            "money_found": money,
            "evidence": evidence,
            "baseline": {
                "baseline_value": base_val,
                "current_value": cur_val,
                "period": f"{self.ANALYSIS_DAYS}d vs {self.ANALYSIS_DAYS}d anteriores",
            },
        }

    def _create_candidate(
        self,
        tenant_code: str,
        tenant_name: str,
        period_start: str,
        period_end: str,
        analysis: dict[str, Any],
    ) -> DecisionCandidate:
        impact = analysis["impact_brl"]
        cat = analysis["title_cat"]
        atype = analysis["anomaly_type"]
        if atype == "DUPLICATE_PAYMENT_SIGNAL":
            title = f"Possível duplicidade em despesas de {cat} (~R$ {impact:,.0f} acima do padrão)"
        else:
            title = f"R$ {impact:,.0f} acima do comportamento de referência em {cat}"
        summary = (
            f"Despesas em {tenant_name}: {cat} ficou R$ {impact:,.2f} acima do baseline de "
            f"{self.ANALYSIS_DAYS} dias (tipo: {atype}). Valor estimado em risco — não é perda confirmada."
        )
        actions = [
            f"Revisar os maiores lançamentos de {cat} no período ({period_start} a {period_end})",
            "Conferir documentos/notas dos lançamentos sinalizados",
            "Validar se o aumento corresponde a serviços/contratos reais",
        ]
        if atype == "DUPLICATE_PAYMENT_SIGNAL":
            actions.insert(0, "Conferir possível duplicidade nos lançamentos com mesmo valor e categoria")

        return DecisionCandidate(
            id=str(uuid.uuid4()),
            detector_name=self.detector_name,
            title=title,
            summary=summary,
            category=DecisionCategory.COST,
            impact_type=ImpactType.COST,
            tenant=tenant_code,
            tenant_name=tenant_name,
            period_start=period_start,
            period_end=period_end,
            money_found=analysis["money_found"],
            confidence=analysis["confidence"],
            confidence_factors=analysis["confidence_factors"],
            recommended_actions=actions,
            estimated_execution_time=25,
            evidence=analysis["evidence"],
            baseline_used=analysis["baseline"],
            source_endpoints=[
                "/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
                "/INTEGRACAO/TITULO_PAGAR",
            ],
        )
