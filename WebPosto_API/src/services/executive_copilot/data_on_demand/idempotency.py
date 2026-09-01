"""Chave canônica versionada do plano. Sem URL, token ou credencial."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any

from src.services.executive_copilot.data_on_demand.policy import (
    IDEMPOTENCY_VERSION,
    LOGICAL_ENDPOINT,
    OPERATION,
)
from src.services.sds_identity import LICENSED_SDS_CODES

VIP_ALIAS = 6666


def official_units(units: list[int]) -> list[int]:
    cleaned = [int(code) for code in units if int(code) != VIP_ALIAS]
    return sorted({code for code in cleaned if code in LICENSED_SDS_CODES})


def canonical_gaps(gaps: list[dict[str, Any]]) -> list[dict[str, object]]:
    items: list[tuple[int, str]] = []
    for gap in gaps:
        unit = int(gap["unidade"])
        if unit == VIP_ALIAS:
            continue
        items.append((unit, str(gap["data"])))
    return [{"unidade": unit, "data": day} for unit, day in sorted(set(items))]


def plan_payload(
    *,
    units: list[int],
    start: date,
    end: date,
    gaps: list[dict[str, Any]],
    authorized_scope: list[int],
    operation: str = OPERATION,
    logical_endpoint: str = LOGICAL_ENDPOINT,
) -> dict[str, object]:
    return {
        "version": IDEMPOTENCY_VERSION,
        "operation": operation,
        "logicalEndpoint": logical_endpoint,
        "units": official_units(units),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "gaps": canonical_gaps(gaps),
        "authorizedScope": official_units(authorized_scope),
    }


def plan_hash(payload: dict[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def idempotency_key(payload: dict[str, object]) -> str:
    return f"{IDEMPOTENCY_VERSION}:{plan_hash(payload)}"
