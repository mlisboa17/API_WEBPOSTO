"""Supplier Invoice Spike Detector — NEXT EXECUTIVE VALUE."""

from __future__ import annotations

import re
import uuid
from collections import defaultdict
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
from src.services.decision_evidence.expense_evidence_builder import attach_expense_evidence_items
from src.services.network_financial_overview_service import NetworkFinancialOverviewService
from src.services.performance.performance_metrics import performance_metrics
from src.services.snapshot_store import SnapshotStore
from src.utils.utc_datetime import age_seconds, utc_now_iso

_NF_REF_PATTERN = re.compile(
    r"^REF\s+NF:(?P<nf>\d+)\s*-\s*(?P<supplier>.+?)(?:\s*-\s*.+)?$",
    re.IGNORECASE,
)


class SupplierInvoiceSpikeDetector(BaseDetector):
    """Detecta notas fiscais de fornecedor sem histórico no baseline (REF NF)."""

    MIN_IMPACT_BRL = 5000.0
    MIN_CONFIDENCE = 0.80
    ANALYSIS_DAYS = 30

    CURRENT_PERIOD_TTL_SECONDS = 5 * 60
    CLOSED_PERIOD_TTL_SECONDS = 24 * 60 * 60

    _cache_store: SnapshotStore | None = None

    def __init__(self) -> None:
        super().__init__(detector_name="SupplierInvoiceSpikeDetector")
        if SupplierInvoiceSpikeDetector._cache_store is None:
            SupplierInvoiceSpikeDetector._cache_store = SnapshotStore(
                "snapshots/discovery_supplier_invoice",
                SupplierInvoiceSpikeDetector.CLOSED_PERIOD_TTL_SECONDS,
            )

    @classmethod
    def _cache_key(cls, tenant_id: str, start: str, end: str) -> str:
        return f"discovery_supplier_invoice:{tenant_id}:{tenant_id}:{start}:{end}"

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

            payload = await self._fetch_bundle(
                tenant_code=tenant_code,
                cur_start=cur_start,
                cur_end=cur_end,
                base_start=base_start,
                base_end=base_end.isoformat(),
                webposto_api_key=kwargs.get("webposto_api_key"),
            )
            if not payload:
                return None

            analyses = self._detect_invoice_spikes(payload)
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
                    self._create_candidate(
                        tenant_code,
                        tenant_name,
                        cur_start,
                        cur_end,
                        analysis,
                    )
                )
            if not candidates:
                return None
            return candidates[0] if len(candidates) == 1 else candidates
        except Exception as exc:
            self.log("detection_error", {"error": str(exc)}, level="error")
            return None

    async def _fetch_bundle(
        self,
        tenant_code: str,
        cur_start: str,
        cur_end: str,
        base_start: str,
        base_end: str,
        webposto_api_key: str | None,
    ) -> Optional[Dict[str, Any]]:
        store = self._cache_store
        key = self._cache_key(tenant_code, cur_start, cur_end)
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
                    "expense_data": {**live, "cache_status": "MISS"},
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

        return {
            "current_expenses": cur_rows,
            "baseline_expenses": base_rows,
            "data_quality": 0.9 if cur_rows and base_rows else 0.65,
        }

    @staticmethod
    def _parse_nf_ref(plano_conta: str) -> Optional[dict[str, str]]:
        match = _NF_REF_PATTERN.match(str(plano_conta or "").strip())
        if not match:
            return None
        supplier = match.group("supplier").strip()
        if " - " in supplier:
            supplier = supplier.split(" - ", 1)[0].strip()
        return {"nf_number": match.group("nf").strip(), "supplier": supplier}

    def _sum_nf_categories(self, rows: list[dict]) -> dict[str, dict[str, Any]]:
        acc: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"amount": 0.0, "count": 0, "rows": [], "parsed": None}
        )
        for row in rows:
            cat = str(row.get("planoConta") or "")
            parsed = self._parse_nf_ref(cat)
            if not parsed:
                continue
            acc[cat]["amount"] += float(row.get("valor") or 0)
            acc[cat]["count"] += 1
            acc[cat]["rows"].append(row)
            acc[cat]["parsed"] = parsed
        return dict(acc)

    def _detect_invoice_spikes(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        cur = self._sum_nf_categories(payload["current_expenses"])
        base = self._sum_nf_categories(payload["baseline_expenses"])
        analyses: list[dict[str, Any]] = []

        for cat, cur_data in cur.items():
            base_data = base.get(cat)
            base_val = base_data["amount"] if base_data else 0.0
            base_count = base_data["count"] if base_data else 0
            cur_val = cur_data["amount"]
            excess = cur_val - base_val
            if excess < self.MIN_IMPACT_BRL:
                continue
            if base_val > 0:
                continue
            parsed = cur_data["parsed"] or {}
            conf = self._confidence(payload, bool(parsed.get("nf_number")))
            analyses.append(
                {
                    "category": cat,
                    "supplier": parsed.get("supplier"),
                    "nf_number": parsed.get("nf_number"),
                    "impact_brl": excess,
                    "current_value": cur_val,
                    "baseline_value": base_val,
                    "current_count": cur_data["count"],
                    "baseline_count": base_count,
                    "confidence": conf,
                    "confidence_factors": ConfidenceFactors(
                        data_quality=float(payload.get("data_quality") or 0.85),
                        comparison_validity=0.90 if parsed.get("nf_number") else 0.70,
                        period_adequacy=0.9,
                        calculation_reliability=0.92,
                    ),
                    "money_found": MoneyFound(
                        at_risk=excess,
                        at_risk_type=MoneyConfidence.ESTIMATED,
                        recoverable=excess * 0.4,
                        recoverable_type=MoneyConfidence.ESTIMATED,
                    ),
                    "current_rows": cur_data["rows"],
                }
            )

        analyses.sort(key=lambda x: x["impact_brl"], reverse=True)
        return analyses

    def _confidence(self, payload: dict, has_nf_number: bool) -> float:
        factors = ConfidenceFactors(
            data_quality=float(payload.get("data_quality") or 0.85),
            comparison_validity=0.90 if has_nf_number else 0.70,
            period_adequacy=0.9,
            calculation_reliability=0.92,
        )
        return min(0.92, factors.overall_confidence())

    def _create_candidate(
        self,
        tenant_code: str,
        tenant_name: str,
        period_start: str,
        period_end: str,
        analysis: dict[str, Any],
    ) -> DecisionCandidate:
        impact = analysis["impact_brl"]
        supplier = analysis.get("supplier") or "fornecedor"
        nf_number = analysis.get("nf_number") or "—"
        evidence = {
            "anomaly_type": "SUPPLIER_INVOICE_SPIKE",
            "category": analysis["category"],
            "supplier": supplier,
            "nf_number": nf_number,
            "current_count": analysis["current_count"],
            "baseline_count": analysis["baseline_count"],
            "limitation": (
                "NF referenciada no plano de contas sem histórico no baseline — "
                "não confirma erro; requer validação de pedido/contrato"
            ),
        }
        evidence = attach_expense_evidence_items(
            evidence,
            analysis.get("current_rows") or [],
            category=analysis["category"],
            tenant_id=tenant_code,
            tenant_name=tenant_name,
        )

        title = f"R$ {impact:,.0f} em NF {nf_number} ({supplier}) sem histórico no período anterior"
        summary = (
            f"{tenant_name}: NF {nf_number} de {supplier} totalizou R$ {impact:,.2f} "
            f"no período atual vs R$ {analysis['baseline_value']:,.2f} no baseline de "
            f"{self.ANALYSIS_DAYS} dias. Valor estimado em risco — não é perda confirmada."
        )
        actions = [
            f"Conferir NF {nf_number} e pedido/contrato de {supplier} ({period_start} a {period_end})",
            f"Validar se os R$ {impact:,.2f} correspondem a mercadoria/serviço recebido",
            "Comparar preço unitário com últimas compras do mesmo fornecedor",
        ]

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
            estimated_execution_time=20,
            evidence=evidence,
            baseline_used={
                "baseline_value": analysis["baseline_value"],
                "current_value": analysis["current_value"],
                "period": f"{self.ANALYSIS_DAYS}d vs {self.ANALYSIS_DAYS}d anteriores",
            },
            source_endpoints=["/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE"],
        )
