from __future__ import annotations

from collections import defaultdict
from difflib import SequenceMatcher
from typing import Iterable


def _normalize(text: str) -> str:
    normalized = text.lower().strip()
    replacements = {
        "cerv": "cerveja",
        "refri": "refrigerante",
        "skol": "skol",
        "lata": "lata",
    }
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return " ".join(normalized.split())


class FuzzyTaxMatcher:
    """Simple fiscal matcher for abbreviated product names."""

    def __init__(self, national_catalog: Iterable[str]):
        self.catalog = [_normalize(item) for item in national_catalog]

    def match(self, local_name: str) -> tuple[str | None, float]:
        target = _normalize(local_name)
        best_name = None
        best_score = 0.0
        for candidate in self.catalog:
            score = SequenceMatcher(None, target, candidate).ratio()
            if score > best_score:
                best_name = candidate
                best_score = score
        return best_name, best_score


def risk_abc_curve(findings: list[dict]) -> dict[str, list[dict]]:
    ordered = sorted(findings, key=lambda item: item.get("risk_score", 0), reverse=True)
    total = max(sum(item.get("risk_score", 0) for item in ordered), 1)
    running = 0
    buckets: dict[str, list[dict]] = defaultdict(list)
    for finding in ordered:
        running += finding.get("risk_score", 0)
        share = running / total
        if share <= 0.8:
            buckets["A"].append(finding)
        elif share <= 0.95:
            buckets["B"].append(finding)
        else:
            buckets["C"].append(finding)
    return dict(buckets)


async def process_in_chunks(items: list[dict], chunk_size: int = 500) -> list[list[dict]]:
    """Prepare chunk slices for high-throughput async pipelines."""
    return [items[index:index + chunk_size] for index in range(0, len(items), chunk_size)]
