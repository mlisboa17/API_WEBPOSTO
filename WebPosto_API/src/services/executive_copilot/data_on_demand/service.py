"""Planner e ciclo de vida do DATA-ON-DEMAND. Chat não dispara ETL."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable

from src.services.executive_copilot.access import restrict_requested_units, user_accessible_units
from src.services.executive_copilot.contracts import ClaimStatus, PeriodWindow, WEBPOSTO_WRITES
from src.services.executive_copilot.coverage import CheckpointStore, MemoryCheckpointStore
from src.services.executive_copilot.data_on_demand.executor import DataRefreshExecutor, FakeDataRefreshExecutor
from src.services.executive_copilot.data_on_demand.idempotency import (
    VIP_ALIAS,
    canonical_gaps,
    idempotency_key,
    official_units,
    plan_hash,
    plan_payload,
)
from src.services.executive_copilot.data_on_demand.models import ConfirmBody, DataRefreshCommand, PlanBody
from src.services.executive_copilot.data_on_demand.policy import (
    LOGICAL_ENDPOINT,
    OPERATION,
    PLAN_TTL_SECONDS,
    estimate_for_gaps,
    planned_gaps,
    validate_period,
)
from src.services.executive_copilot.data_on_demand.http_contract import fake_meta, public_base
from src.services.executive_copilot.data_on_demand.states import (
    CANCELABLE_STATES,
    DataRequestState,
    NON_CANCELABLE_EXECUTION,
)
from src.services.executive_copilot.data_on_demand.store import DataRequestStore
from src.services.executive_copilot.unit_capabilities import (
    UNIT_SOURCE_NOT_APPLICABLE,
    UNIT_SOURCE_NOT_APPLICABLE_MESSAGE,
    dod_units,
)
from src.services.sds_process_lock import NullSdsProcessLock, SdsProcessLock
from src.services.sds_sanitize import sanitize_value

Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DataOnDemandService:
    def __init__(
        self,
        store: DataRequestStore,
        checkpoint_store: CheckpointStore | None = None,
        *,
        executor: DataRefreshExecutor | None = None,
        process_lock: SdsProcessLock | None = None,
        clock: Clock | None = None,
        ttl_seconds: int = PLAN_TTL_SECONDS,
        auto_run_on_confirm: bool = False,
    ) -> None:
        self._store = store
        self._checkpoints = checkpoint_store or MemoryCheckpointStore()
        self._executor = executor or FakeDataRefreshExecutor()
        self._lock = process_lock or NullSdsProcessLock()
        self._clock = clock or _utc_now
        self._ttl_seconds = ttl_seconds
        self._auto_run_on_confirm = auto_run_on_confirm

    def plan(self, body: PlanBody, user: dict[str, Any] | None) -> dict[str, Any]:
        auth = self._authorize(body.units, user)
        if auth.get("blocked"):
            return auth
        today = self._clock().date()
        period_error = validate_period(body.period, today)
        if period_error:
            return self._blocked(period_error, units=auth["units"], period=body.period)
        units = dod_units(auth["units"])
        if not units:
            return self._blocked(
                {"code": UNIT_SOURCE_NOT_APPLICABLE, "message": UNIT_SOURCE_NOT_APPLICABLE_MESSAGE},
                units=[],
                period=body.period,
            )
        units = official_units(units)
        gaps = planned_gaps(self._checkpoints, units, body.period.start, body.period.end)
        estimate = estimate_for_gaps(len(gaps))
        if not gaps:
            return sanitize_value(
                public_base(
                    request_id=None,
                    status=DataRequestState.ALREADY_AVAILABLE.value,
                    units=units,
                    start=body.period.start.isoformat(),
                    end=body.period.end.isoformat(),
                    missing_pairs=[],
                    requires_confirmation=False,
                    estimate=estimate,
                    created=False,
                )
            )
        payload = plan_payload(
            units=units,
            start=body.period.start,
            end=body.period.end,
            gaps=gaps,
            authorized_scope=auth["scope"],
        )
        digest = plan_hash(payload)
        key = idempotency_key(payload)
        now = self._clock()
        request_id = uuid.uuid4().hex
        row = {
            "request_id": request_id,
            "idempotency_key": key,
            "state": DataRequestState.AWAITING_CONFIRMATION.value,
            "plan_hash": digest,
            "operation": OPERATION,
            "logical_endpoint": LOGICAL_ENDPOINT,
            "units": units,
            "start_date": body.period.start.isoformat(),
            "end_date": body.period.end.isoformat(),
            "gaps": canonical_gaps(gaps),
            "authorized_scope": official_units(auth["scope"]),
            "progress": {"pairsTotal": len(gaps), "pairsDone": 0, "pagesOk": 0, "pagesFailed": 0},
            "estimated_seconds_min": estimate["estimatedSecondsMin"],
            "estimated_seconds_max": estimate["estimatedSecondsMax"],
            "queue_delay_seconds": estimate["queueDelaySeconds"],
            "estimate_confidence": estimate["estimateConfidence"],
            "created_by": str((user or {}).get("sub") or (user or {}).get("email") or ""),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=self._ttl_seconds)).isoformat(),
        }
        duplicate = self._store.insert_plan(row, {"planHash": digest, "gaps": len(gaps)})
        chosen = duplicate or self._store.get(request_id)
        assert chosen is not None
        return self._public(chosen, created=duplicate is None)

    def confirm(self, request_id: str, body: ConfirmBody, user: dict[str, Any] | None) -> dict[str, Any]:
        row = self._store.get(request_id)
        if row is None:
            return self._blocked({"code": "REQUEST_NOT_FOUND", "message": "Pedido não encontrado."})
        auth = self._authorize(row["units"], user)
        if auth.get("blocked"):
            return auth
        if row["state"] is DataRequestState.EXPIRED:
            return self._public(row, ok=False, code="PLAN_EXPIRED")
        if self._expired(row):
            updated = self._store.transition(
                request_id,
                DataRequestState.AWAITING_CONFIRMATION,
                DataRequestState.EXPIRED,
                event="EXPIRED",
                detail={"code": "PLAN_EXPIRED"},
            )
            return self._public(updated or row, ok=False, code="PLAN_EXPIRED")
        if body.plan_hash != row["plan_hash"]:
            return self._public(row, ok=False, code="PLAN_HASH_MISMATCH")
        if row["state"] is not DataRequestState.AWAITING_CONFIRMATION:
            if row["state"] is DataRequestState.EXPIRED:
                return self._public(row, ok=False, code="PLAN_EXPIRED")
            return self._public(row)
        updated = self._store.transition(
            request_id,
            DataRequestState.AWAITING_CONFIRMATION,
            DataRequestState.QUEUED,
            extra={"confirmed_at": self._clock().isoformat(), "updated_at": self._clock().isoformat()},
            event="CONFIRMED",
            detail={"planHash": row["plan_hash"]},
        )
        payload = self._public(updated or row)
        if self._auto_run_on_confirm:
            return self.run(request_id, user)
        return payload

    def get(self, request_id: str, user: dict[str, Any] | None) -> dict[str, Any]:
        row = self._store.get(request_id)
        if row is None:
            return self._blocked({"code": "REQUEST_NOT_FOUND", "message": "Pedido não encontrado."})
        auth = self._authorize(row["units"], user)
        if auth.get("blocked"):
            return auth
        if row["state"] is DataRequestState.AWAITING_CONFIRMATION and self._expired(row):
            row = (
                self._store.transition(
                    request_id,
                    DataRequestState.AWAITING_CONFIRMATION,
                    DataRequestState.EXPIRED,
                    event="EXPIRED",
                    detail={"code": "PLAN_EXPIRED"},
                )
                or row
            )
        return self._public(row)

    def cancel(self, request_id: str, user: dict[str, Any] | None) -> dict[str, Any]:
        row = self._store.get(request_id)
        if row is None:
            return self._blocked({"code": "REQUEST_NOT_FOUND", "message": "Pedido não encontrado."})
        auth = self._authorize(row["units"], user)
        if auth.get("blocked"):
            return auth
        if row["state"] in NON_CANCELABLE_EXECUTION:
            return self._public(row, ok=False, code="CANCEL_NOT_ALLOWED")
        if row["state"] not in CANCELABLE_STATES:
            return self._public(row, ok=False, code="INVALID_STATE")
        updated = self._store.transition(
            request_id,
            CANCELABLE_STATES,
            DataRequestState.CANCELLED,
            event="CANCELLED",
            detail={"from": row["state"].value},
        )
        self._store.release_own_pairs(request_id)
        return self._public(updated or row)

    def run(self, request_id: str, user: dict[str, Any] | None) -> dict[str, Any]:
        row = self._store.get(request_id)
        if row is None:
            return self._blocked({"code": "REQUEST_NOT_FOUND", "message": "Pedido não encontrado."})
        auth = self._authorize(row["units"], user)
        if auth.get("blocked"):
            return auth
        claimed = self._store.transition(
            request_id,
            DataRequestState.QUEUED,
            DataRequestState.RUNNING,
            extra={"updated_at": self._clock().isoformat()},
            event="STARTED",
            detail={"requestId": request_id},
        )
        if claimed is None:
            return self._public(row, ok=False, code="NOT_CLAIMED")
        acquired = False
        try:
            acquired = self._lock.acquire("data-on-demand")
            if not acquired:
                locked = self._store.transition(
                    request_id,
                    DataRequestState.RUNNING,
                    DataRequestState.LOCKED,
                    event="LOCKED",
                    detail={"code": "SDS_LOCK_UNAVAILABLE"},
                )
                return self._public(locked or claimed, ok=False, code="SDS_LOCK_UNAVAILABLE")
            pairs = [(int(gap["unidade"]), str(gap["data"])) for gap in claimed["gaps"]]
            if not self._store.acquire_pairs(request_id, pairs):
                locked = self._store.transition(
                    request_id,
                    DataRequestState.RUNNING,
                    DataRequestState.LOCKED,
                    event="LOCKED",
                    detail={"code": "PAIR_LOCKED"},
                )
                return self._public(locked or claimed, ok=False, code="PAIR_LOCKED")
            command = DataRefreshCommand(
                units=tuple(claimed["units"]),
                start=date.fromisoformat(claimed["start_date"]),
                end=date.fromisoformat(claimed["end_date"]),
                gaps=tuple(pairs),
                request_id=request_id,
                plan_hash=claimed["plan_hash"],
            )
            self._store.transition(
                request_id,
                DataRequestState.RUNNING,
                DataRequestState.VALIDATING,
                event="VALIDATING",
                detail={"pairs": len(pairs)},
            )
            try:
                result = self._executor.execute(command)
                if result.publishes_fact() or any(
                    item.claim_status == ClaimStatus.FACT.value for item in result.pairs
                ):
                    raise RuntimeError("FACT bloqueado durante ingestão DATA-ON-DEMAND")
            except Exception as exc:
                failed = self._store.transition(
                    request_id,
                    frozenset({DataRequestState.VALIDATING, DataRequestState.RUNNING}),
                    DataRequestState.FAILED,
                    event="FAILED",
                    detail={"code": "EXECUTOR_FAILED", "message": str(exc)},
                )
                return self._public(failed or claimed, ok=False, code="EXECUTOR_FAILED")
            self._store.transition(
                request_id,
                DataRequestState.VALIDATING,
                DataRequestState.COMMITTING,
                event="COMMITTING",
                detail={"consolidated": sum(1 for item in result.pairs if item.consolidated)},
            )
            progress = {
                "pairsTotal": len(result.pairs),
                "pairsDone": sum(1 for item in result.pairs if item.consolidated),
                "pagesOk": sum(1 for item in result.pairs for page in item.pages if page.ok),
                "pagesFailed": sum(1 for item in result.pairs for page in item.pages if not page.ok),
                "partial": result.state is DataRequestState.PARTIAL,
            }
            final = self._store.transition(
                request_id,
                DataRequestState.COMMITTING,
                result.state,
                extra={"progress": progress, "updated_at": self._clock().isoformat()},
                event=result.state.value,
                detail=sanitize_value(
                    {
                        "pairs": [
                            {
                                "unidade": item.unit,
                                "data": item.day.isoformat(),
                                "consolidated": item.consolidated,
                                "claimStatus": item.claim_status,
                            }
                            for item in result.pairs
                        ],
                        "webpostoWrites": WEBPOSTO_WRITES,
                    }
                ),
            )
            payload = self._public(final or claimed)
            payload["execution"] = sanitize_value(
                {
                    "status": result.state.value,
                    "publishesFact": False,
                    "dataChanged": False,
                    "externalRequests": 0,
                    "executorMode": fake_meta()["executorMode"],
                    "pairs": [
                        {
                            "unidade": item.unit,
                            "data": item.day.isoformat(),
                            "consolidated": item.consolidated,
                            "claimStatus": item.claim_status,
                            "pages": [{"page": page.page, "ok": page.ok} for page in item.pages],
                        }
                        for item in result.pairs
                    ],
                    "webpostoWrites": WEBPOSTO_WRITES,
                }
            )
            return payload
        finally:
            self._store.release_own_pairs(request_id)
            if acquired:
                self._lock.release()

    def _authorize(self, requested: list[int] | None, user: dict[str, Any] | None) -> dict[str, Any]:
        resolved = restrict_requested_units(requested, user)
        if resolved.blocked:
            return self._blocked(resolved.blocked)
        if VIP_ALIAS in list(requested or []) and VIP_ALIAS in resolved.units:
            return self._blocked({"code": "UNIT_ALIAS_LEAK", "message": "6666 não pode persistir."})
        scope = user_accessible_units(user)
        return {"units": official_units(resolved.persisted_units), "scope": official_units(scope.units)}

    def _expired(self, row: dict[str, Any]) -> bool:
        expires = row.get("expires_at")
        if not expires:
            return False
        return self._clock() >= datetime.fromisoformat(str(expires))

    def _blocked(self, blocked: dict[str, str], *, units: list[int] | None = None, period: PeriodWindow | None = None) -> dict[str, Any]:
        start = period.start.isoformat() if period is not None else None
        end = period.end.isoformat() if period is not None else None
        return sanitize_value(
            public_base(
                request_id=None,
                status=DataRequestState.FAILED.value,
                units=units or [],
                start=start,
                end=end,
                requires_confirmation=False,
                created=False,
                ok=False,
                blocked=blocked,
            )
        )

    def _public(self, row: dict[str, Any], *, created: bool | None = None, ok: bool = True, code: str | None = None) -> dict[str, Any]:
        status = row["state"].value if isinstance(row["state"], DataRequestState) else str(row["state"])
        return sanitize_value(
            public_base(
                request_id=row["request_id"],
                status=status,
                units=row["units"],
                start=row["start_date"],
                end=row["end_date"],
                missing_pairs=row["gaps"],
                plan_hash=row["plan_hash"],
                requires_confirmation=status == DataRequestState.AWAITING_CONFIRMATION.value,
                confirmation_expires_at=row["expires_at"],
                progress=row["progress"],
                estimate={
                    "estimatedSecondsMin": row["estimated_seconds_min"],
                    "estimatedSecondsMax": row["estimated_seconds_max"],
                    "queueDelaySeconds": row["queue_delay_seconds"],
                    "estimateConfidence": row["estimate_confidence"],
                },
                ok=ok,
                created=created,
                code=code,
            )
        )
