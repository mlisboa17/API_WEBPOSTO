"""Preference Model Service — FASE 5 (APRENDER), sprint "Preference Model".

Consumes per-category efficacy/preference scores from EfficacyAnalyticsEngine
and applies a bounded preference multiplier to the ranking of decisions coming
out of the Owner Intelligence Engine.

Design constraints:
- Multiplier is clamped to [0.85, 1.15] so preference never suppresses or
  over-boosts decisions beyond a safe band.
- CRITICAL decisions are never reduced; their score is always multiplied by
  the upper bound (1.15) or left untouched if already higher.
- All calculations are tenant-isolated and use the cached data from
  EfficacyAnalyticsEngine, keeping ranking latency in sub-millisecond range.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.services.decision_execution.efficacy_analytics import EfficacyAnalyticsEngine

if TYPE_CHECKING:
    from src.services.owner_intelligence.schemas import DailyDecision


@dataclass(frozen=True)
class PreferenceWeightResult:
    """Result of applying preference weighting to a single decision."""

    decision_id: str
    category: str
    original_score: float
    adjusted_score: float
    multiplier: float
    reason: str


class PreferenceModelService:
    """Applies owner-preference multipliers to decision rankings.

    The service uses EfficacyAnalyticsEngine's cached per-category
    preference_score to nudge decision scores. Multipliers are bounded to
    [min_multiplier, max_multiplier], and CRITICAL priority decisions are
    protected from any reduction.
    """

    MIN_MULTIPLIER: float = 0.85
    MAX_MULTIPLIER: float = 1.15
    CRITICAL_FLOOR: float = MAX_MULTIPLIER

    def __init__(self, efficacy_engine: EfficacyAnalyticsEngine | None = None) -> None:
        self._efficacy_engine = (
            efficacy_engine if efficacy_engine is not None else EfficacyAnalyticsEngine()
        )

    def apply_preference_weights(
        self,
        decisions: Sequence[DailyDecision],
        tenant_id: str,
        empresa_codigo: str,
    ) -> tuple[list[DailyDecision], list[PreferenceWeightResult]]:
        """Return re-ranked decisions and the list of adjustments applied.

        Decisions are sorted by adjusted score descending. The original
        DailyDecision objects are NOT mutated; new copies are returned.
        """
        category_scores = self._efficacy_engine.calculate(tenant_id, empresa_codigo)

        adjusted: list[DailyDecision] = []
        audit: list[PreferenceWeightResult] = []
        for decision in decisions:
            category = self._extract_category(decision)
            multiplier = self._compute_multiplier(decision, category, category_scores)
            original_score = decision.total_score
            adjusted_score = self._clamp_score(original_score * multiplier)

            adjusted_decision = decision.model_copy(update={"total_score": adjusted_score})
            adjusted.append(adjusted_decision)
            audit.append(
                PreferenceWeightResult(
                    decision_id=decision.id,
                    category=category,
                    original_score=original_score,
                    adjusted_score=adjusted_score,
                    multiplier=multiplier,
                    reason=self._reason(decision.action.priority, multiplier, category),
                )
            )

        adjusted.sort(key=lambda d: d.total_score, reverse=True)
        self._reassign_ranks(adjusted)
        return adjusted, audit

    def _compute_multiplier(
        self,
        decision: DailyDecision,
        category: str,
        category_scores: Mapping[str, Any],
    ) -> float:
        """Compute the bounded multiplier for a single decision."""
        from src.services.owner_intelligence.schemas import ActionPriority

        is_critical = decision.action.priority == ActionPriority.CRITICAL
        efficacy = category_scores.get(category)
        if efficacy is None:
            return self.MAX_MULTIPLIER if is_critical else 1.0

        preference_score = getattr(efficacy, "preference_score", 0.5)
        score_range = self.MAX_MULTIPLIER - self.MIN_MULTIPLIER
        # preference_score is in [0, 1]; map linearly to [MIN, MAX]
        multiplier = self.MIN_MULTIPLIER + preference_score * score_range

        if is_critical and multiplier < self.CRITICAL_FLOOR:
            return self.CRITICAL_FLOOR
        return multiplier

    @staticmethod
    def _extract_category(decision: DailyDecision) -> str:
        """Extract a normalized category string from a decision."""
        category = decision.action.category
        if isinstance(category, str) and category:
            return category.strip().lower()
        return "unknown"

    @staticmethod
    def _clamp_score(score: float) -> float:
        """Keep scores within the engine's valid range [0, 100]."""
        if score < 0.0:
            return 0.0
        if score > 100.0:
            return 100.0
        return score

    @staticmethod
    def _reassign_ranks(decisions: list[DailyDecision]) -> None:
        """Re-assign sequential ranks after sorting."""
        for index, decision in enumerate(decisions, start=1):
            decision.rank = index

    @staticmethod
    def _reason(priority: Any, multiplier: float, category: str) -> str:
        """Human-readable reason for the multiplier applied."""
        from src.services.owner_intelligence.schemas import ActionPriority

        if (
            priority == ActionPriority.CRITICAL
            and multiplier >= PreferenceModelService.CRITICAL_FLOOR
        ):
            return f"critical priority protected from reduction (category={category})"
        if multiplier > 1.0:
            return f"category {category} has positive preference bias"
        if multiplier < 1.0:
            return f"category {category} has negative preference bias"
        return f"category {category} has neutral preference"
