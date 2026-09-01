#!/usr/bin/env python3
"""Valida o orçamento de desempenho dos serviços departamentais."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.departmental_alert_service import DepartmentalAlertService  # noqa: E402
from src.services.departmental_operations_service import DepartmentalOperationsService  # noqa: E402

DEFAULT_OUT = ROOT / "docs" / "performance" / "DEPARTMENTAL_PERFORMANCE_LATEST.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", default="2026-07-23")
    parser.add_argument("--samples", type=int, default=6)
    parser.add_argument("--warm-budget-ms", type=float, default=150.0)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    if args.samples < 2:
        parser.error("--samples deve ser pelo menos 2")

    service = DepartmentalOperationsService(alerts=DepartmentalAlertService())
    samples: list[float] = []
    for _ in range(args.samples):
        started = time.perf_counter()
        service.daily_report(args.day)
        samples.append(round((time.perf_counter() - started) * 1000, 1))

    warm = samples[1:]
    median = round(statistics.median(warm), 1)
    payload = {
        "day": args.day,
        "samples_ms": samples,
        "cold_ms": samples[0],
        "warm_median_ms": median,
        "warm_max_ms": max(warm),
        "warm_budget_ms": args.warm_budget_ms,
        "passed": median <= args.warm_budget_ms,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
