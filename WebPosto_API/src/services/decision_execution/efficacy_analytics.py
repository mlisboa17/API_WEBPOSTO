"""Efficacy Analytics & Preference Model — FASE 5 (APRENDER), sprint 3.

Analyzes historical decision outcomes per category to compute:
- success_rate:      % of terminal decisions fully completed
- execution_rate:    % of presented decisions that were acted upon
- rejection_rate:    % of terminal decisions explicitly rejected
- efficacy_score:    success_rate normalized to 0.0-1.0
- preference_score:  softmax-normalized score reflecting owner preference
                     for a category relative to others (0.0-1.0)

Data is aggregated directly via SQLExecutionRecordStore, avoiding loading
full ExecutionRecord payloads. Results are cached per (tenant_id,
empresa_codigo) with a configurable TTL to protect the database from
redundant queries during high-frequency prioritization loops.
"""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Tuple

from src.services.decision_execution.sql_store import SQLExecutionRecordStore


@dataclass(frozen=True)
class CategoryEfficacy:
    """Efficacy and preference metrics for a single decision category."""

    category: str
    presented: int
    executed: int
    completed: int
    not_completed: int
    partial: int
    expired: int
    success_rate: float
    execution_rate: float
    rejection_rate: float
    efficacy_score: float
    preference_score: float


class EfficacyAnalyticsEngine:
    """Computes per-category efficacy and owner-preference scores.

    The engine is tenant-isolated: every calculation is scoped to a
    (tenant_id, empresa_codigo) pair. Results are cached in memory with a TTL
    so that repeated prioritization calls do not hit the database every time.
    """

    def __init__(
        self,
        store: SQLExecutionRecordStore | None = None,
        ttl_seconds: float = 60.0,
    ) -> None:
        self._store = store if store is not None else SQLExecutionRecordStore()
        self._ttl = timedelta(seconds=ttl_seconds)
        self._cache: Dict[Tuple[str, str], Tuple[datetime, Dict[str, CategoryEfficacy]]] = {}
        self._cache_lock = threading.RLock()

    def calculate(self, tenant_id: str, empresa_codigo: str) -> Dict[str, CategoryEfficacy]:
        """Return per-category efficacy and preference metrics.

        Results are fetched from cache when available and not expired; otherwise
        the store is queried via SQL aggregation and the cache is refreshed.
        """
        cache_key = (tenant_id, empresa_codigo)

        with self._cache_lock:
            cached = self._cache.get(cache_key)
            if cached is not None:
                cached_at, result = cached
                if datetime.utcnow() - cached_at < self._ttl:
                    return result

        raw = self._store.aggregate_category_stats(tenant_id, empresa_codigo)
        result = self._compute_scores(raw)

        with self._cache_lock:
            self._cache[cache_key] = (datetime.utcnow(), result)

        return result

    def clear_cache(self) -> None:
        """Invalidate the in-memory cache. Useful for tests and admin ops."""
        with self._cache_lock:
            self._cache.clear()

    def _compute_scores(self, raw: Dict[str, Dict[str, int]]) -> Dict[str, CategoryEfficacy]:
        """Convert raw SQL counts into normalized efficacy/preference scores."""
        if not raw:
            return {}

        base_scores: Dict[str, float] = {}
        for category, stats in raw.items():
            presented = stats["presented"]
            executed = stats["executed"]
            completed = stats["completed"]
            not_completed = stats["not_completed"]
            partial = stats["partial"]
            terminal = completed + not_completed + partial

            success_rate = (completed / terminal * 100.0) if terminal else 0.0
            execution_rate = (executed / presented * 100.0) if presented else 0.0

            base_scores[category] = (execution_rate + success_rate) / 200.0

        preference_scores = self._softmax(base_scores)

        result: Dict[str, CategoryEfficacy] = {}
        for category, stats in raw.items():
            presented = stats["presented"]
            executed = stats["executed"]
            completed = stats["completed"]
            not_completed = stats["not_completed"]
            partial = stats["partial"]
            expired = stats["expired"]
            terminal = completed + not_completed + partial

            success_rate = (completed / terminal * 100.0) if terminal else 0.0
            execution_rate = (executed / presented * 100.0) if presented else 0.0
            rejection_rate = (not_completed / terminal * 100.0) if terminal else 0.0

            result[category] = CategoryEfficacy(
                category=category,
                presented=presented,
                executed=executed,
                completed=completed,
                not_completed=not_completed,
                partial=partial,
                expired=expired,
                success_rate=round(success_rate, 1),
                execution_rate=round(execution_rate, 1),
                rejection_rate=round(rejection_rate, 1),
                efficacy_score=round(success_rate / 100.0, 3),
                preference_score=round(preference_scores[category], 3),
            )

        return result

    @staticmethod
    def _softmax(scores: Dict[str, float], temperature: float = 0.5) -> Dict[str, float]:
        """Convert raw scores to a probability distribution over categories."""
        if not scores:
            return {}
        if len(scores) == 1:
            return {next(iter(scores)): 1.0}

        exp_scores = {category: math.exp(score / temperature) for category, score in scores.items()}
        total = sum(exp_scores.values())
        return {category: value / total for category, value in exp_scores.items()}
