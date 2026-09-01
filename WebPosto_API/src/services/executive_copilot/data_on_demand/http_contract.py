"""Contrato HTTP público do DATA-ON-DEMAND. Sem I/O e sem segredos."""

from __future__ import annotations

from src.services.executive_copilot.contracts import WEBPOSTO_WRITES
from src.services.executive_copilot.data_on_demand.policy import LOGICAL_ENDPOINT, OPERATION

EXECUTOR_MODE = "FAKE_LOCAL"
FAKE_META = {
    "executorMode": EXECUTOR_MODE,
    "externalRequests": 0,
    "webpostoWrites": WEBPOSTO_WRITES,
    "dataChanged": False,
    "publishesFact": False,
}

PUBLIC_KEYS = (
    "requestId",
    "planHash",
    "status",
    "units",
    "requestedPeriod",
    "missingPairs",
    "estimatedSecondsMin",
    "estimatedSecondsMax",
    "queueDelaySeconds",
    "estimateConfidence",
    "confirmationExpiresAt",
    "requiresConfirmation",
    "logicalEndpoint",
    "operation",
    "progress",
    "executorMode",
    "externalRequests",
    "webpostoWrites",
    "dataChanged",
    "publishesFact",
    "ok",
)


def fake_meta() -> dict[str, object]:
    return dict(FAKE_META)


def requested_period(start: str, end: str) -> dict[str, str]:
    return {"inicio": start, "fim": end}


def public_base(
    *,
    request_id: str | None,
    status: str,
    units: list[int],
    start: str | None = None,
    end: str | None = None,
    missing_pairs: list[dict[str, object]] | None = None,
    plan_hash: str | None = None,
    requires_confirmation: bool = False,
    confirmation_expires_at: str | None = None,
    progress: dict[str, object] | None = None,
    estimate: dict[str, object] | None = None,
    ok: bool = True,
    created: bool | None = None,
    code: str | None = None,
    blocked: dict[str, str] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "requestId": request_id,
        "planHash": plan_hash,
        "status": status,
        "units": list(units),
        "requestedPeriod": requested_period(start, end) if start and end else None,
        "missingPairs": list(missing_pairs or []),
        "logicalEndpoint": LOGICAL_ENDPOINT,
        "operation": OPERATION,
        "requiresConfirmation": requires_confirmation,
        "confirmationExpiresAt": confirmation_expires_at,
        "progress": progress or {"pairsTotal": 0, "pairsDone": 0, "pagesOk": 0, "pagesFailed": 0},
        "ok": ok,
        **fake_meta(),
    }
    if estimate:
        payload.update(estimate)
    if created is not None:
        payload["created"] = created
    if code:
        payload["code"] = code
    if blocked:
        payload["blocked"] = dict(blocked)
    return payload
