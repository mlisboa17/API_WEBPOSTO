"""Deteccao de duplicidade por EAN e descricao."""

from __future__ import annotations

from typing import Any

from .duplicate_checker import find_description_duplicates
from .policies.duplicate_policy import DuplicatePolicy
from .product_family import commercial_family


class DuplicateDetectionService:
    """Compara EAN e descricao; diferencia mesmo produto e variante legitima."""

    def __init__(self, policy: DuplicatePolicy | None = None) -> None:
        self.policy = policy or DuplicatePolicy()

    def find_by_ean(self, ean: str, catalog_by_ean: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
        return catalog_by_ean.get(str(ean).strip())

    def classify_description(
        self,
        candidate_description: str,
        catalog: list[dict[str, Any]],
        *,
        candidate_family: str | None = None,
    ) -> dict[str, Any]:
        matches = find_description_duplicates(candidate_description, catalog)
        if not matches:
            return {"matches": [], "decision": None}
        existing = matches[0]
        decision = self.policy.evaluate(
            candidate_description,
            existing.get("nome") or "",
            candidate_family=candidate_family,
            existing_family=commercial_family(existing.get("nome") or ""),
            existing_code=existing.get("produtoCodigo"),
        )
        return {
            "matches": matches,
            "decision": decision,
            "action": self.policy.pre_post_action(decision),
        }
