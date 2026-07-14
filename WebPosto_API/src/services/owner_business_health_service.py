"""Business Health Score a partir de anomalias reais nos snapshots owner_analysis."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from src.services.decision_discovery.discovery_scope import DiscoveryScope
from src.services.owner_analysis_models import (
    DETECTOR_SET_SIGNATURE,
    LEGACY_DETECTOR_SET_SIGNATURE,
    OWNER_ANALYSIS_SNAPSHOT_DIR,
)
from src.services.snapshot_store import safe_filename

ROOT = Path(__file__).resolve().parents[2]
OWNER_SNAPSHOT_DIR = ROOT / OWNER_ANALYSIS_SNAPSHOT_DIR

HEALTH_SCORE_DETECTORS = frozenset(
    {
        "CardReceivableDetector",
        "ExpenseDetector",
        "FuelRevenueDetector",
        "MarginDetector",
    }
)

DETECTOR_WEIGHTS: dict[str, float] = {
    "FuelRevenueDetector": 1.0,
    "ExpenseDetector": 0.9,
    "CardReceivableDetector": 0.85,
    "MarginDetector": 1.1,
}

MAX_DEDUCTION_PER_ANOMALY = 15.0
IMPACT_NORMALIZER_BRL = 50_000.0


@dataclass(frozen=True)
class BusinessHealthResult:
    overall_score: float
    status: str
    risk_count: int
    has_sufficient_data: bool
    message: str | None
    last_update: str
    deductions: list[dict[str, Any]]
    snapshot_hit: bool
    snapshot_stale: bool

    def to_response_data(self) -> dict[str, Any]:
        return {
            "overall_score": round(self.overall_score, 1),
            "status": self.status,
            "risk_count": self.risk_count,
            "last_update": self.last_update,
            "has_sufficient_data": self.has_sufficient_data,
            "message": self.message,
            "deductions": self.deductions,
            "formula": "100 - sum(peso_detector * severidade_impacto * confidence)",
        }


def _money_impact(candidate: dict[str, Any]) -> float:
    money = candidate.get("money_found") or {}
    if isinstance(money, dict):
        for key in ("at_risk", "recoverable", "additional"):
            block = money.get(key)
            if isinstance(block, dict):
                try:
                    return float(block.get("value") or 0)
                except (TypeError, ValueError):
                    continue
            try:
                val = float(block or 0)
                if val > 0:
                    return val
            except (TypeError, ValueError):
                continue
        for key in ("total", "at_risk"):
            try:
                return float(money.get(key) or 0)
            except (TypeError, ValueError):
                continue
    evidence = candidate.get("evidence") or {}
    for key in ("gap_value", "impact_brl"):
        try:
            val = float(evidence.get(key) or 0)
            if val > 0:
                return val
        except (TypeError, ValueError):
            continue
    return 0.0


def _candidate_confidence(candidate: dict[str, Any]) -> float:
    try:
        return float(candidate.get("confidence") or 0)
    except (TypeError, ValueError):
        return 0.0


def _deduction_for_anomaly(candidate: dict[str, Any]) -> float:
    detector = str(candidate.get("detector") or candidate.get("detector_name") or "")
    weight = DETECTOR_WEIGHTS.get(detector, 0.75)
    impact = _money_impact(candidate)
    confidence = _candidate_confidence(candidate)
    if impact <= 0 or confidence <= 0:
        return 0.0
    severity = min(1.0, impact / IMPACT_NORMALIZER_BRL)
    return weight * severity * confidence * MAX_DEDUCTION_PER_ANOMALY


def _status_from_score(score: float, has_data: bool) -> str:
    if not has_data:
        return "unknown"
    if score >= 80:
        return "healthy"
    if score >= 60:
        return "attention"
    if score >= 40:
        return "risk"
    return "critical"


def _detector_signature_tokens() -> list[str]:
    tokens = [DETECTOR_SET_SIGNATURE.replace(",", "_")]
    legacy = LEGACY_DETECTOR_SET_SIGNATURE.replace(",", "_")
    if legacy not in tokens:
        tokens.append(legacy)
    return tokens


def _build_scope_key(period_start: str, period_end: str, scope: DiscoveryScope) -> str:
    empresa = scope.empresa_snapshot_suffix()
    return f"{period_start}:{period_end}:all_discovered:{DETECTOR_SET_SIGNATURE}:{empresa}"


def _resolve_snapshot_paths(
    period_start: str,
    period_end: str,
    scope: DiscoveryScope,
) -> list[Path]:
    if not OWNER_SNAPSHOT_DIR.is_dir():
        return []

    scope_key = _build_scope_key(period_start, period_end, scope)
    indexed = OWNER_SNAPSHOT_DIR / f"{safe_filename(f'owner_analysis:last_valid:{scope_key}')}.json"
    if indexed.exists():
        return [indexed]

    suffix = scope.empresa_snapshot_suffix().replace(",", "_")
    paths: list[Path] = []
    for sig in _detector_signature_tokens():
        pattern = f"owner_analysis_last_valid_{period_start}_{period_end}_all_discovered_{sig}_{suffix}.json"
        paths.extend(sorted(OWNER_SNAPSHOT_DIR.glob(pattern), reverse=True))
    if paths:
        return paths

    for sig in _detector_signature_tokens():
        pattern = f"owner_analysis_last_valid_*_all_discovered_{sig}_{suffix}.json"
        paths.extend(sorted(OWNER_SNAPSHOT_DIR.glob(pattern), reverse=True))
    return paths


def _iter_candidates(data: dict[str, Any], scope: DiscoveryScope) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []

    for entry in data.get("top_5_decisions") or []:
        candidate = entry.get("candidate") or {}
        if candidate:
            found.append(candidate)

    for entry in data.get("observations") or []:
        candidate = entry.get("candidate") or entry
        if candidate:
            found.append(candidate)

    for entry in data.get("stored_candidates") or []:
        if isinstance(entry, dict):
            found.append(entry)

    scoped: list[dict[str, Any]] = []
    for candidate in found:
        detector = str(candidate.get("detector") or candidate.get("detector_name") or "")
        if detector not in HEALTH_SCORE_DETECTORS:
            continue
        tenant = candidate.get("tenant") or candidate.get("tenant_id")
        if not scope.allows_tenant(tenant):
            continue
        scoped.append(candidate)
    return scoped


def _load_snapshot_data(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    snapshot = payload.get("snapshot") or payload
    response = snapshot.get("response") or snapshot
    return response.get("data") or {}


class OwnerBusinessHealthService:
    """Calcula health score (100 base) com deduções ponderadas por anomalias ativas."""

    def calculate(
        self,
        period_start: str,
        period_end: str,
        *,
        scope: DiscoveryScope,
    ) -> BusinessHealthResult:
        paths = _resolve_snapshot_paths(period_start, period_end, scope)
        if not paths:
            return BusinessHealthResult(
                overall_score=0,
                status="unknown",
                risk_count=0,
                has_sufficient_data=False,
                message="Dados insuficientes para calcular health score",
                last_update=datetime.now().isoformat(),
                deductions=[],
                snapshot_hit=False,
                snapshot_stale=False,
            )

        data = _load_snapshot_data(paths[0]) or {}
        if not data.get("has_sufficient_data", True) and not (
            data.get("top_5_decisions") or data.get("stored_candidates")
        ):
            return BusinessHealthResult(
                overall_score=0,
                status="unknown",
                risk_count=0,
                has_sufficient_data=False,
                message="Dados insuficientes para calcular health score",
                last_update=datetime.now().isoformat(),
                deductions=[],
                snapshot_hit=True,
                snapshot_stale=False,
            )

        candidates = _iter_candidates(data, scope)
        deductions_detail: list[dict[str, Any]] = []
        total_deduction = 0.0

        for candidate in candidates:
            points = _deduction_for_anomaly(candidate)
            if points <= 0:
                continue
            total_deduction += points
            deductions_detail.append(
                {
                    "detector": candidate.get("detector") or candidate.get("detector_name"),
                    "tenant": candidate.get("tenant") or candidate.get("tenant_id"),
                    "title": candidate.get("title"),
                    "impact_brl": round(_money_impact(candidate), 2),
                    "confidence": round(_candidate_confidence(candidate), 3),
                    "deduction_points": round(points, 2),
                }
            )

        overall = max(0.0, 100.0 - total_deduction)
        has_data = bool(candidates) or bool(data.get("analysis_proof"))
        status = _status_from_score(overall, has_data)

        proof = data.get("analysis_proof") or {}
        last_update = str(proof.get("completed_at") or datetime.now().isoformat())

        return BusinessHealthResult(
            overall_score=overall,
            status=status,
            risk_count=len(deductions_detail),
            has_sufficient_data=has_data and overall > 0,
            message=None if has_data and overall > 0 else "Dados insuficientes para calcular health score",
            last_update=last_update,
            deductions=deductions_detail,
            snapshot_hit=True,
            snapshot_stale=False,
        )

    def calculate_or_forbid(
        self,
        period_start: str,
        period_end: str,
        *,
        scope: DiscoveryScope,
    ) -> BusinessHealthResult:
        if not scope.authorized_empresa_codes:
            raise HTTPException(status_code=403, detail="Portfólio corporativo indisponível")
        return self.calculate(period_start, period_end, scope=scope)
