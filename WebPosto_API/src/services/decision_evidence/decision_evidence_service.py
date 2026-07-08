"""Resolve decisões e evidence_items para DIR-01."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.services.decision_discovery.models import DecisionCandidate, DecisionCategory
from src.services.decision_discovery.root_cause.investigators import ExpenseRootCause
from src.services.decision_evidence.expense_evidence_builder import (
    EXPENSE_SOURCE,
    build_expense_evidence_items,
    evidence_items_summary,
)
from src.services.decision_evidence.models import DecisionEvidenceItem, DecisionEvidenceResponse
from src.services.decision_evidence.nominal_enrichment_service import NominalEnrichmentService
from src.services.owner_analysis_models import OWNER_ANALYSIS_SNAPSHOT_DIR
from src.services.snapshot_store import SnapshotStore

ROOT = Path(__file__).resolve().parents[3]
OWNER_SNAPSHOT_DIR = ROOT / OWNER_ANALYSIS_SNAPSHOT_DIR
EXPENSE_SNAPSHOT_DIR = ROOT / "snapshots" / "discovery_expense"


class DecisionEvidenceService:
    """Localiza decisão em snapshots e materializa evidence_items."""

    def __init__(self) -> None:
        self._owner_store = SnapshotStore(str(OWNER_SNAPSHOT_DIR), ttl_seconds=86400 * 365)
        self._expense_store = SnapshotStore(str(EXPENSE_SNAPSHOT_DIR), ttl_seconds=86400 * 365)
        self._nominal = NominalEnrichmentService()

    async def get_evidence(
        self,
        decision_id: str,
        *,
        enrich_nominal: bool = True,
    ) -> DecisionEvidenceResponse | None:
        candidate = self._find_candidate(decision_id)
        if not candidate:
            return None

        evidence = dict(candidate.get("evidence") or {})
        items = self._load_evidence_items(candidate, evidence)
        period = candidate.get("period") or {}
        tenant_id = str(candidate.get("tenant") or "")
        period_start = str(period.get("start") or "")
        period_end = str(period.get("end") or "")
        nominal_metadata: dict[str, Any] = {}
        if enrich_nominal and items and tenant_id and period_start and period_end:
            items, nominal_metadata = await self._nominal.enrich_items(
                items,
                tenant_id=tenant_id,
                period_start=period_start,
                period_end=period_end,
            )
        root_cause = await self._root_cause_text(candidate)
        money = candidate.get("money_found") or {}
        limitations = self._limitations(candidate, evidence, items, nominal_metadata)

        return DecisionEvidenceResponse(
            decision_id=decision_id,
            decision_summary=str(candidate.get("summary") or candidate.get("title") or ""),
            root_cause=root_cause,
            money_found=money if isinstance(money, dict) else {},
            confidence=candidate.get("confidence"),
            evidence_items=items,
            evidence_items_count=len(items),
            evidence_items_total=round(sum(item.amount for item in items), 2),
            limitations=limitations,
            source_metadata={
                "detector": candidate.get("detector"),
                "tenant_id": candidate.get("tenant"),
                "tenant_name": candidate.get("tenant_name"),
                "period": candidate.get("period") or {},
                "source_endpoints": candidate.get("source_endpoints") or [],
                "baseline": candidate.get("baseline") or candidate.get("baseline_used") or {},
                "evidence_aggregate": {
                    "category": evidence.get("category"),
                    "current_count": evidence.get("current_count"),
                    "baseline_count": evidence.get("baseline_count"),
                    "anomaly_type": evidence.get("anomaly_type"),
                },
                "nominal_enrichment": nominal_metadata,
            },
        )

    @staticmethod
    def _expense_cache_key(tenant_id: str, period_start: str, period_end: str) -> str:
        return f"discovery_expense:{tenant_id}:{tenant_id}:{period_start}:{period_end}"

    def _find_candidate(self, decision_id: str) -> dict[str, Any] | None:
        if not OWNER_SNAPSHOT_DIR.is_dir():
            return None

        for path in sorted(OWNER_SNAPSHOT_DIR.glob("owner_analysis_last_valid_*.json"), reverse=True):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            snapshot = payload.get("snapshot") or payload
            response = snapshot.get("response") or snapshot
            data = response.get("data") or {}
            for entry in data.get("top_5_decisions") or []:
                action = entry.get("action") or {}
                candidate = entry.get("candidate") or {}
                ids = {
                    str(action.get("id") or ""),
                    str(entry.get("decision_id") or ""),
                    str(candidate.get("id") or ""),
                }
                if decision_id in ids:
                    return candidate if candidate else self._candidate_from_entry(entry)

            for entry in data.get("stored_candidates") or []:
                if str(entry.get("id") or "") == decision_id:
                    return entry
        return None

    @staticmethod
    def _candidate_from_entry(entry: dict[str, Any]) -> dict[str, Any]:
        action = entry.get("action") or {}
        return {
            "id": action.get("id"),
            "title": action.get("title"),
            "summary": action.get("description"),
            "tenant": entry.get("tenant_id"),
            "tenant_name": entry.get("tenant_name"),
            "confidence": action.get("confidence"),
            "money_found": action.get("financial_impact"),
            "evidence": entry.get("evidence") or {},
        }

    def _load_evidence_items(
        self,
        candidate: dict[str, Any],
        evidence: dict[str, Any],
    ) -> list[DecisionEvidenceItem]:
        raw_items = evidence.get("evidence_items") or []
        if raw_items:
            return [DecisionEvidenceItem.model_validate(item) for item in raw_items]

        category = evidence.get("category") or evidence.get("label")
        tenant_id = str(candidate.get("tenant") or "")
        if not category or not tenant_id:
            return []

        period = candidate.get("period") or {}
        period_start = str(period.get("start") or "")
        period_end = str(period.get("end") or "")
        if not period_start or not period_end:
            return []

        cache_key = self._expense_cache_key(tenant_id, period_start, period_end)
        stored, _ = self._expense_store.load_stale(cache_key)
        expense_data = (stored or {}).get("expense_data") or {}
        rows = expense_data.get("current_expenses") or []
        if not rows:
            return []

        return build_expense_evidence_items(
            rows,
            category=str(category),
            tenant_id=tenant_id,
            tenant_name=candidate.get("tenant_name"),
            source=EXPENSE_SOURCE,
        )

    async def _root_cause_text(self, candidate: dict[str, Any]) -> str | None:
        category = str(candidate.get("category") or "")
        if category != DecisionCategory.COST.value:
            return None
        try:
            decision = self._to_decision_candidate(candidate)
            analysis = await ExpenseRootCause().investigate(decision)
            cause = analysis.most_probable_cause
            if cause and cause.description:
                return cause.description
            return analysis.insufficient_data_message
        except Exception:
            return None

    @staticmethod
    def _to_decision_candidate(data: dict[str, Any]) -> DecisionCandidate:
        from src.services.decision_discovery.models import ImpactType, MoneyFound

        period = data.get("period") or {}
        money_raw = data.get("money_found") or {}
        at_risk = 0.0
        if isinstance(money_raw, dict):
            nested = money_raw.get("at_risk")
            if isinstance(nested, dict):
                at_risk = float(nested.get("value") or 0)
            else:
                at_risk = float(money_raw.get("estimated_value") or money_raw.get("at_risk") or 0)

        return DecisionCandidate(
            id=str(data.get("id") or ""),
            detector_name=str(data.get("detector") or "ExpenseDetector"),
            title=str(data.get("title") or ""),
            summary=str(data.get("summary") or ""),
            category=DecisionCategory(data.get("category") or DecisionCategory.COST.value),
            impact_type=ImpactType(data.get("impact_type") or ImpactType.COST.value),
            tenant=str(data.get("tenant") or ""),
            tenant_name=data.get("tenant_name"),
            period_start=str(period.get("start") or ""),
            period_end=str(period.get("end") or ""),
            money_found=MoneyFound(at_risk=at_risk),
            confidence=float(data.get("confidence") or 0),
            evidence=dict(data.get("evidence") or {}),
            baseline_used=dict(data.get("baseline") or data.get("baseline_used") or {}),
            source_endpoints=list(data.get("source_endpoints") or []),
        )

    @staticmethod
    def _limitations(
        candidate: dict[str, Any],
        evidence: dict[str, Any],
        items: list[DecisionEvidenceItem],
        nominal_metadata: dict[str, Any] | None = None,
    ) -> list[str]:
        limitations: list[str] = []
        nominal_metadata = nominal_metadata or {}
        match_summary = nominal_metadata.get("match_summary") or {}
        if not items:
            limitations.append("Nenhum lançamento detalhado disponível para esta decisão.")
        elif match_summary:
            identified = int(match_summary.get("with_funcionario") or 0)
            total = len(items)
            if identified == 0:
                limitations.append(
                    "Nenhum lançamento recebeu match nominal com CAIXA/CAIXA_APRESENTADO — "
                    "beneficiário individual indisponível na origem financeira."
                )
            elif identified < total:
                limitations.append(
                    f"{identified} de {total} lançamentos com funcionário identificado via match operacional; "
                    f"{total - identified} permanecem sem beneficiário nominal."
                )
            no_match = int(match_summary.get("NO_MATCH") or 0)
            ambiguous = int(match_summary.get("AMBIGUOUS") or 0)
            if no_match:
                limitations.append(
                    f"{no_match} lançamento(s) sem candidato operacional (NO_MATCH) — "
                    "consolidação financeira sem espelho linha a linha na API."
                )
            if ambiguous:
                limitations.append(
                    f"{ambiguous} lançamento(s) com match ambíguo — múltiplos turnos/caixas candidatos."
                )
            for note in nominal_metadata.get("complementary_sources_required") or []:
                limitations.append(f"Fonte complementar necessária: {note}")
        elif not any(item.person_name for item in items):
            limitations.append(
                "A fonte /INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE não traz nome do funcionário "
                "beneficiário nestes lançamentos — apenas categoria e valor."
            )
        baseline = candidate.get("baseline") or candidate.get("baseline_used") or {}
        current_total = float(baseline.get("current_value") or 0)
        items_total = round(sum(item.amount for item in items), 2)
        if current_total > 0 and abs(items_total - current_total) > 0.05:
            limitations.append(
                f"Total dos lançamentos listados (R$ {items_total:,.2f}) corresponde à categoria no período; "
                f"excesso estimado da decisão usa baseline (atual R$ {current_total:,.2f})."
            )
        if evidence.get("anomaly_type") == "CATEGORY_SPIKE":
            limitations.append(
                "Estes lançamentos explicam o aumento versus comportamento de referência — "
                "não constituem acusação automática."
            )
        return limitations
