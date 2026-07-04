"""Card Receivable Loss Detector — VALUE-04."""

from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

from src.domain.value_objects.payment_method import PaymentMethod
from src.services.analytics_multiselect import build_overview_filters
from src.services.corporate_finance_center_service import CorporateFinanceCenterService
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


class CardReceivableDetector(BaseDetector):
    """Detecta gaps explicáveis entre expectativa de recebível e evidência de liquidação."""

    RECONCILIATION_LEVEL = 1
    MIN_IMPACT_BRL = 2000.0
    MIN_CONFIDENCE = 0.80
    ANALYSIS_DAYS = 30
    MIN_OVERDUE_DAYS = 7

    CURRENT_PERIOD_TTL_SECONDS = 5 * 60
    CLOSED_PERIOD_TTL_SECONDS = 24 * 60 * 60

    _cache_store: SnapshotStore | None = None

    def __init__(self) -> None:
        super().__init__(detector_name="CardReceivableDetector")
        if CardReceivableDetector._cache_store is None:
            CardReceivableDetector._cache_store = SnapshotStore(
                "snapshots/discovery_receivable",
                CardReceivableDetector.CLOSED_PERIOD_TTL_SECONDS,
            )

    @classmethod
    def _cache_key(cls, tenant_id: str, start: str, end: str) -> str:
        return f"discovery_receivable:{tenant_id}:{tenant_id}:{start}:{end}"

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

            payload = await self._fetch_bundle(
                tenant_code=tenant_code,
                cur_start=cur_start,
                cur_end=cur_end,
                ref_date=cur_end,
                webposto_api_key=kwargs.get("webposto_api_key"),
            )
            if not payload:
                return None

            analyses = self._detect_signals(payload, ref_date=end)
            if not analyses:
                return None

            tenant_name = kwargs.get("tenant_name", tenant_code)
            candidates: List[DecisionCandidate] = []
            for analysis in analyses:
                if analysis["gap_value"] < self.MIN_IMPACT_BRL:
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

    async def _fetch_bundle(
        self,
        tenant_code: str,
        cur_start: str,
        cur_end: str,
        ref_date: str,
        webposto_api_key: str | None,
    ) -> Optional[Dict[str, Any]]:
        store = self._cache_store
        key = self._cache_key(tenant_code, cur_start, cur_end)
        if store:
            stored, _ = store.load_stale(key)
            if stored and stored.get("receivable_data"):
                ttl = self._period_ttl(cur_end)
                try:
                    age = age_seconds(str(stored.get("lastUpdated")))
                except ValueError:
                    age = ttl + 1
                if age <= ttl:
                    performance_metrics.record_receivable_cache_hit()
                    return dict(stored["receivable_data"])
            performance_metrics.record_receivable_cache_miss()

        live = await self._fetch_live(tenant_code, cur_start, cur_end, ref_date, webposto_api_key)
        if live and store:
            store.save(
                key,
                {
                    "lastUpdated": utc_now_iso(),
                    "receivable_data": {**live, "cache_status": "MISS"},
                },
            )
        return live

    async def _fetch_live(
        self,
        tenant_code: str,
        cur_start: str,
        cur_end: str,
        ref_date: str,
        webposto_api_key: str | None,
    ) -> Optional[Dict[str, Any]]:
        from src.gateway.webposto_client import WebPostoClient

        client = WebPostoClient.for_api_key(webposto_api_key) if webposto_api_key else WebPostoClient()
        overview = NetworkFinancialOverviewService(client)
        finance = CorporateFinanceCenterService(overview)
        filters = build_overview_filters(cur_start, cur_end, tenant_code)

        rec_rows, _ = await finance._fetch_titulo_receber_all(filters)
        rec_rows = [
            r for r in rec_rows
            if str(r.get("empresaCodigo") or "") == tenant_code or finance._matches_empresa(r, filters)
        ]
        buckets = finance._classify_receivables(rec_rows, ref_date)

        card_rows: list[dict] = []
        card_gross = Decimal("0")
        vendas_resp = await overview._fetch_vendas_produtos(filters, int(tenant_code))
        if vendas_resp.success:
            fp_rows = overview._rows((vendas_resp.data or {}).get("venda_forma_pagamento"))
            for row in fp_rows:
                if str(row.get("empresaCodigo") or "") not in ("", tenant_code) and not finance._matches_empresa(row, filters):
                    continue
                forma = str(row.get("formaPagamento") or row.get("descricaoFormaPagamento") or "")
                pm = PaymentMethod.from_raw(forma)
                if pm not in {PaymentMethod.CARTAO_CREDITO, PaymentMethod.CARTAO_DEBITO}:
                    continue
                card_rows.append(row)
                try:
                    card_gross += Decimal(str(row.get("valor") or 0))
                except Exception:
                    pass

        bank_rows, _ = await finance._fetch_movimento_conta_all(filters)
        bank_rows = [
            r for r in bank_rows
            if str(r.get("empresaCodigo") or "") == tenant_code or finance._matches_empresa(r, filters)
        ]
        bank = finance._classify_bank_movements(bank_rows)

        return {
            "receivable_rows": rec_rows,
            "buckets": buckets,
            "card_sales_count": len(card_rows),
            "card_sales_gross": float(card_gross),
            "bank_credits": float(bank["creditos"]["valor"]),
            "data_quality": 0.85 if rec_rows else 0.4,
            "card_data_available": len(card_rows) > 0,
        }

    def _detect_signals(self, payload: dict[str, Any], ref_date: date) -> list[dict[str, Any]]:
        buckets = payload["buckets"]
        overdue = buckets.get("vencido") or []
        analyses: list[dict[str, Any]] = []

        overdue_val = sum(self._dec(r.get("valor")) for r in overdue)
        settled_val = sum(self._dec(r.get("valor")) for r in buckets.get("recebido") or [])
        expected_pending = sum(self._dec(r.get("valor")) for r in buckets.get("pendente") or [])

        if overdue and overdue_val >= self.MIN_IMPACT_BRL:
            days = self._avg_overdue_days(overdue, ref_date)
            top_client = self._top_client_share(overdue)
            conf = self._confidence(payload, len(overdue), days, has_card=payload.get("card_data_available", False))
            analyses.append(
                self._analysis(
                    signal_type="OVERDUE_RECEIVABLE",
                    gap_value=float(overdue_val),
                    expected_value=float(expected_pending),
                    settled_value=float(settled_val),
                    overdue_count=len(overdue),
                    avg_overdue_days=days,
                    top_client_share=top_client,
                    confidence=conf,
                    limitation="LEVEL 1: titulos vencidos sem baixa contábil — não prova gap de cartão TEF",
                )
            )

        dup = self._duplicate_settlement_signal(overdue)
        if dup and dup["amount"] >= self.MIN_IMPACT_BRL:
            analyses.append(
                self._analysis(
                    signal_type="DUPLICATE_SETTLEMENT_SIGNAL",
                    gap_value=dup["amount"],
                    expected_value=dup["amount"],
                    settled_value=0.0,
                    overdue_count=dup["pairs"],
                    avg_overdue_days=0,
                    top_client_share=0,
                    confidence=self._confidence(payload, dup["pairs"], 14, False) * 0.85,
                    limitation="POSSÍVEL DUPLICIDADE — requer conferência documental",
                    extra=dup,
                )
            )

        if payload.get("card_data_available") and payload.get("card_sales_gross", 0) > 0:
            gap = float(payload["card_sales_gross"]) - settled_val
            if gap >= self.MIN_IMPACT_BRL:
                analyses.append(
                    self._analysis(
                        signal_type="EXPECTED_VS_SETTLED_GAP",
                        gap_value=gap,
                        expected_value=float(payload["card_sales_gross"]),
                        settled_value=settled_val,
                        overdue_count=0,
                        avg_overdue_days=0,
                        top_client_share=0,
                        confidence=self._confidence(payload, 5, 30, True) * 0.75,
                        limitation="LEVEL 1 agregado: vendas cartão vs titulos recebidos — sem vínculo transacional",
                    )
                )

        analyses.sort(key=lambda x: x["gap_value"], reverse=True)
        return analyses

    @staticmethod
    def _dec(val: Any) -> Decimal:
        try:
            return Decimal(str(val or 0))
        except Exception:
            return Decimal("0")

    def _avg_overdue_days(self, rows: list[dict], ref: date) -> float:
        days: list[int] = []
        for row in rows:
            venc = str(row.get("vencimento") or "")[:10]
            if not venc:
                continue
            try:
                d = date.fromisoformat(venc)
                if d < ref:
                    days.append((ref - d).days)
            except ValueError:
                continue
        return sum(days) / len(days) if days else 0.0

    @staticmethod
    def _top_client_share(rows: list[dict]) -> float:
        totals: dict[str, Decimal] = defaultdict(Decimal)
        for row in rows:
            client = str(row.get("cliente") or "sem_cliente")
            totals[client] += CardReceivableDetector._dec(row.get("valor"))
        if not totals:
            return 0.0
        grand = sum(totals.values())
        if grand <= 0:
            return 0.0
        return float(max(totals.values()) / grand)

    def _duplicate_settlement_signal(self, rows: list[dict]) -> Optional[dict]:
        seen: Counter = Counter()
        for row in rows:
            key = (str(row.get("cliente") or ""), str(row.get("valor") or ""), str(row.get("vencimento") or ""))
            seen[key] += 1
        best = None
        for key, count in seen.items():
            if count < 2:
                continue
            val = self._dec(key[1])
            amount = float(val * (count - 1))
            item = {"pairs": count, "amount": amount, "cliente": key[0], "note": "POSSÍVEL DUPLICIDADE"}
            if not best or amount > best["amount"]:
                best = item
        return best

    def _confidence(self, payload: dict, record_count: int, avg_overdue_days: float, has_card: bool) -> float:
        level_factor = 0.72 if self.RECONCILIATION_LEVEL <= 1 else 0.88
        dq = float(payload.get("data_quality") or 0.7) * min(1.0, record_count / 10.0)
        overdue_factor = min(1.0, avg_overdue_days / 30.0) if avg_overdue_days else 0.5
        card_penalty = 0.95 if has_card else 0.88
        factors = ConfidenceFactors(
            data_quality=dq,
            comparison_validity=level_factor * card_penalty,
            period_adequacy=0.9 if self.ANALYSIS_DAYS >= 28 else 0.75,
            calculation_reliability=0.92,
        )
        base = factors.overall_confidence()
        return min(0.92, base * (0.85 + overdue_factor * 0.15))

    def _analysis(
        self,
        *,
        signal_type: str,
        gap_value: float,
        expected_value: float,
        settled_value: float,
        overdue_count: int,
        avg_overdue_days: float,
        top_client_share: float,
        confidence: float,
        limitation: str,
        extra: dict | None = None,
    ) -> dict:
        factors = ConfidenceFactors(
            data_quality=0.85,
            comparison_validity=0.72,
            period_adequacy=0.9,
            calculation_reliability=0.9,
        )
        money = MoneyFound(
            at_risk=gap_value,
            at_risk_type=MoneyConfidence.ESTIMATED,
            recoverable=gap_value * 0.6,
            recoverable_type=MoneyConfidence.ESTIMATED,
        )
        evidence = {
            "signal_type": signal_type,
            "reconciliation_level": self.RECONCILIATION_LEVEL,
            "expected_value": expected_value,
            "settled_value": settled_value,
            "gap_value": gap_value,
            "overdue_count": overdue_count,
            "avg_overdue_days": round(avg_overdue_days, 1),
            "top_client_share": round(top_client_share, 3),
            "expectation_source": "/INTEGRACAO/TITULO_RECEBER",
            "settlement_source": "/INTEGRACAO/TITULO_RECEBER (dataPagamento/pendente)",
            "limitation": limitation,
        }
        if extra:
            evidence.update(extra)
        return {
            "signal_type": signal_type,
            "gap_value": gap_value,
            "confidence": confidence,
            "confidence_factors": factors,
            "money_found": money,
            "evidence": evidence,
            "baseline": {
                "expected_value": expected_value,
                "settled_value": settled_value,
                "gap_value": gap_value,
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
        gap = analysis["gap_value"]
        signal = analysis["signal_type"]
        ev = analysis["evidence"]

        if signal == "OVERDUE_RECEIVABLE":
            title = f"R$ {gap:,.0f} em recebíveis vencidos sem evidência de liquidação"
        elif signal == "DUPLICATE_SETTLEMENT_SIGNAL":
            title = f"Possível duplicidade em recebíveis (~R$ {gap:,.0f} em risco estimado)"
        else:
            title = f"R$ {gap:,.0f} acima do esperado vs liquidação registrada (agregado)"

        summary = (
            f"{tenant_name}: {ev['overdue_count']} título(s) analisado(s). "
            f"Esperado pendente R$ {ev.get('expected_value', analysis['baseline']['expected_value']):,.2f}; "
            f"com evidência de liquidação R$ {analysis['baseline']['settled_value']:,.2f}. "
            f"Gap estimado R$ {gap:,.2f} — {ev['limitation']}"
        )
        actions = [
            f"Revisar os {min(ev['overdue_count'], 10)} maiores recebíveis vencidos sem baixa ({period_start} a {period_end})",
            "Conferir `dataPagamento`/`pendente` nos títulos listados no ERP",
            "Validar se clientes concentrados correspondem a contratos/prazo ativos",
        ]
        if signal == "DUPLICATE_SETTLEMENT_SIGNAL":
            actions.insert(0, "Conferir possível duplicidade nos títulos com mesmo cliente/valor/vencimento")

        return DecisionCandidate(
            id=str(uuid.uuid4()),
            detector_name=self.detector_name,
            title=title,
            summary=summary,
            category=DecisionCategory.CASH,
            impact_type=ImpactType.CASH,
            tenant=tenant_code,
            tenant_name=tenant_name,
            period_start=period_start,
            period_end=period_end,
            money_found=analysis["money_found"],
            confidence=analysis["confidence"],
            confidence_factors=analysis["confidence_factors"],
            recommended_actions=actions,
            estimated_execution_time=20,
            evidence=analysis["evidence"],
            baseline_used=analysis["baseline"],
            source_endpoints=[
                "/INTEGRACAO/TITULO_RECEBER",
                "/INTEGRACAO/VENDA_FORMA_PAGAMENTO",
                "/INTEGRACAO/MOVIMENTO_CONTA",
            ],
        )
