"""Limites e allowlist do DATA-ON-DEMAND. Sem rede e sem URL de usuário."""

from __future__ import annotations

from datetime import date
from typing import Any

from src.services.executive_copilot.contracts import PeriodWindow, WEBPOSTO_WRITES
from src.services.sds_identity import COMPLETE_STATUSES

OPERATION = "REFRESH_SDS"
LOGICAL_ENDPOINT = "ABASTECIMENTO"
ALLOWED_OPERATIONS = frozenset({OPERATION})
ALLOWED_ENDPOINTS = frozenset({LOGICAL_ENDPOINT})
MAX_DAYS = 31
PLAN_TTL_SECONDS = 15 * 60
SECONDS_PER_GAP_MIN = 8
SECONDS_PER_GAP_MAX = 20
QUEUE_DELAY_SECONDS = 2
ESTIMATE_CONFIDENCE = "LOW"
IDEMPOTENCY_VERSION = "dod-v1"


def validate_period(period: PeriodWindow, today: date) -> dict[str, str] | None:
    days = (period.end - period.start).days + 1
    if days > MAX_DAYS:
        return {"code": "PERIOD_TOO_LONG", "message": f"Período máximo é {MAX_DAYS} dias."}
    if period.start > today or period.end > today:
        return {"code": "PERIOD_FUTURE", "message": "Datas futuras são bloqueadas."}
    if period.start <= today <= period.end:
        return {"code": "CURRENT_DAY_INCOMPLETE", "message": "O dia corrente é incompleto e está bloqueado."}
    return None


def planned_gaps(store: Any, units: list[int], start: date, end: date) -> list[dict[str, object]]:
    rows = store.list_days(units, start, end)
    by_key = {(row.empresa_codigo, row.data_referencia): row for row in rows}
    gaps: list[dict[str, object]] = []
    cursor = start
    while cursor <= end:
        for unit in units:
            row = by_key.get((unit, cursor))
            if row is None or row.status not in COMPLETE_STATUSES:
                gaps.append({"unidade": unit, "data": cursor.isoformat()})
        cursor = date.fromordinal(cursor.toordinal() + 1)
    return gaps


def estimate_for_gaps(gap_count: int) -> dict[str, object]:
    return {
        "estimatedSecondsMin": int(gap_count) * SECONDS_PER_GAP_MIN,
        "estimatedSecondsMax": int(gap_count) * SECONDS_PER_GAP_MAX,
        "queueDelaySeconds": QUEUE_DELAY_SECONDS,
        "estimateConfidence": ESTIMATE_CONFIDENCE,
        "webpostoWrites": WEBPOSTO_WRITES,
    }


def assert_allowlisted(operation: str, logical_endpoint: str) -> None:
    if operation not in ALLOWED_OPERATIONS or logical_endpoint not in ALLOWED_ENDPOINTS:
        raise ValueError("comando fora da allowlist")
