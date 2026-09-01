"""DATA-ON-DEMAND-01 — planner local com executor falso. Sem rede."""

from __future__ import annotations

import ast
import threading
from datetime import date, datetime, timezone
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from src.interfaces.http.dependencies import get_current_user
from src.interfaces.http.routes.executive_copilot_data_requests import (
    configure_data_on_demand,
    router,
)
from src.services.executive_copilot.contracts import ClaimStatus, WEBPOSTO_WRITES
from src.services.executive_copilot.coverage import DayCheckpoint, MemoryCheckpointStore
from src.services.executive_copilot.data_on_demand.executor import FakeDataRefreshExecutor
from src.services.executive_copilot.data_on_demand.models import ConfirmBody, PlanBody
from src.services.executive_copilot.data_on_demand.service import DataOnDemandService
from src.services.executive_copilot.data_on_demand.states import DataRequestState
from src.services.executive_copilot.data_on_demand.store import DataRequestStore
from src.services.sds_identity import STATUS_SUCESSO
from src.services.sds_process_lock import NullSdsProcessLock

DAY = date(2026, 8, 27)
GAP = date(2026, 8, 26)
TODAY = date(2026, 8, 29)


@pytest.fixture(autouse=True)
def block_external_http(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("chamada externa proibida")

    monkeypatch.setattr(httpx, "Client", boom)
    monkeypatch.setattr(httpx, "AsyncClient", boom)


def _clock() -> datetime:
    return datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)


def _director() -> dict:
    return {"role": "director", "sub": "qa.dod@logos.test", "email": "qa.dod@logos.test"}


def _body(units: list[int], start: str, end: str) -> PlanBody:
    return PlanBody.model_validate({"unidades": units, "periodo": {"inicio": start, "fim": end}})


def _service(
    tmp_path: Path,
    rows: list[DayCheckpoint] | None = None,
    *,
    executor: FakeDataRefreshExecutor | None = None,
    ttl: int = 900,
) -> DataOnDemandService:
    store = DataRequestStore(tmp_path / "data_on_demand.sqlite")
    return DataOnDemandService(
        store,
        MemoryCheckpointStore(rows or [_check(5555, DAY)]),
        executor=executor or FakeDataRefreshExecutor(),
        process_lock=NullSdsProcessLock(),
        clock=_clock,
        ttl_seconds=ttl,
    )


def _check(unit: int, day: date, status: str = STATUS_SUCESSO) -> DayCheckpoint:
    return DayCheckpoint(unit, day, status, 10)


def test_complete_coverage_does_not_create_job(tmp_path: Path) -> None:
    service = _service(tmp_path)
    result = service.plan(_body([5555], "2026-08-27", "2026-08-27"), _director())
    assert result["status"] == DataRequestState.ALREADY_AVAILABLE
    assert result["created"] is False
    assert result["requestId"] is None
    assert result["webpostoWrites"] == 0
    assert "6666" not in str(result)


def test_gap_creates_immutable_plan(tmp_path: Path) -> None:
    service = _service(tmp_path)
    result = service.plan(_body([5555], "2026-08-26", "2026-08-27"), _director())
    assert result["status"] == DataRequestState.AWAITING_CONFIRMATION
    assert result["created"] is True
    assert result["missingPairs"] == [{"unidade": 5555, "data": "2026-08-26"}]
    assert result["requiresConfirmation"] is True
    assert result["executorMode"] == "FAKE_LOCAL"
    assert result["estimatedSecondsMin"] == 8
    assert result["estimatedSecondsMax"] == 20
    assert result["queueDelaySeconds"] == 2
    assert result["estimateConfidence"] == "LOW"
    assert result["logicalEndpoint"] == "ABASTECIMENTO"


def test_confirm_moves_to_queued(tmp_path: Path) -> None:
    service = _service(tmp_path)
    planned = service.plan(_body([5555], "2026-08-26", "2026-08-27"), _director())
    confirmed = service.confirm(planned["requestId"], ConfirmBody.model_validate({"planHash": planned["planHash"]}), _director())
    assert confirmed["status"] == DataRequestState.QUEUED
    assert confirmed["ok"] is True


def test_expired_plan_does_not_confirm(tmp_path: Path) -> None:
    service = _service(tmp_path, ttl=0)
    planned = service.plan(_body([5555], "2026-08-26", "2026-08-27"), _director())
    confirmed = service.confirm(planned["requestId"], ConfirmBody.model_validate({"planHash": planned["planHash"]}), _director())
    assert confirmed["status"] == DataRequestState.EXPIRED
    assert confirmed["code"] == "PLAN_EXPIRED"
    assert confirmed["ok"] is False


def test_altered_plan_does_not_confirm(tmp_path: Path) -> None:
    service = _service(tmp_path)
    planned = service.plan(_body([5555], "2026-08-26", "2026-08-27"), _director())
    confirmed = service.confirm(
        planned["requestId"],
        ConfirmBody.model_validate({"planHash": "0" * 64}),
        _director(),
    )
    assert confirmed["code"] == "PLAN_HASH_MISMATCH"
    assert confirmed["status"] == DataRequestState.AWAITING_CONFIRMATION


def test_duplicate_confirm_is_idempotent(tmp_path: Path) -> None:
    service = _service(tmp_path)
    planned = service.plan(_body([5555], "2026-08-26", "2026-08-27"), _director())
    first = service.confirm(planned["requestId"], ConfirmBody.model_validate({"planHash": planned["planHash"]}), _director())
    second = service.confirm(planned["requestId"], ConfirmBody.model_validate({"planHash": planned["planHash"]}), _director())
    assert first["status"] == second["status"] == DataRequestState.QUEUED
    assert first["requestId"] == second["requestId"]
    assert second["ok"] is True


def test_duplicate_active_returns_same_request_id(tmp_path: Path) -> None:
    service = _service(tmp_path)
    first = service.plan(_body([5555], "2026-08-26", "2026-08-27"), _director())
    second = service.plan(_body([5555], "2026-08-26", "2026-08-27"), _director())
    assert first["requestId"] == second["requestId"]
    assert second["created"] is False


def test_dispute_does_not_run_twice(tmp_path: Path) -> None:
    executor = FakeDataRefreshExecutor()
    service = _service(tmp_path, executor=executor)
    planned = service.plan(_body([5555], "2026-08-26", "2026-08-27"), _director())
    service.confirm(planned["requestId"], ConfirmBody.model_validate({"planHash": planned["planHash"]}), _director())
    results: list[dict] = []

    def worker() -> None:
        results.append(service.run(planned["requestId"], _director()))

    threads = [threading.Thread(target=worker), threading.Thread(target=worker)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)
    executed = [item for item in results if item.get("status") in {DataRequestState.SUCCESS.value, DataRequestState.PARTIAL.value}]
    skipped = [item for item in results if item.get("code") == "NOT_CLAIMED"]
    assert len(executor.calls) == 1
    assert len(executed) == 1
    assert len(skipped) == 1


def test_forbidden_unit_is_blocked(tmp_path: Path) -> None:
    service = _service(tmp_path)
    result = service.plan(_body([5333], "2026-08-26", "2026-08-26"), _director())
    assert result["blocked"]["code"] == "UNIT_FORBIDDEN"
    assert result["requestId"] is None


def test_alias_6666_does_not_persist(tmp_path: Path) -> None:
    service = _service(tmp_path, rows=[_check(11495, DAY)])
    result = service.plan(_body([6666], "2026-08-26", "2026-08-27"), _director())
    assert result["units"] == [11495]
    assert 6666 not in result["units"]
    blob = service._store.raw_blob()
    assert "6666" not in blob
    assert result["missingPairs"][0]["unidade"] == 11495


def test_current_day_blocked(tmp_path: Path) -> None:
    service = _service(tmp_path)
    result = service.plan(_body([5555], "2026-08-29", "2026-08-29"), _director())
    assert result["blocked"]["code"] == "CURRENT_DAY_INCOMPLETE"


def test_future_period_blocked(tmp_path: Path) -> None:
    service = _service(tmp_path)
    result = service.plan(_body([5555], "2026-08-30", "2026-08-30"), _director())
    assert result["blocked"]["code"] == "PERIOD_FUTURE"


def test_more_than_31_days_blocked(tmp_path: Path) -> None:
    service = _service(tmp_path)
    result = service.plan(_body([5555], "2026-07-01", "2026-08-01"), _director())
    assert result["blocked"]["code"] == "PERIOD_TOO_LONG"


def test_partial_never_produces_fact(tmp_path: Path) -> None:
    previous = [_check(5555, DAY)]
    executor = FakeDataRefreshExecutor(
        fail_pages={(5555, "2026-08-26", 2)},
        fail_detail="https://erp.example/INTEGRACAO/ABASTECIMENTO?token=super-secret",
    )
    service = _service(tmp_path, rows=previous, executor=executor)
    planned = service.plan(_body([5555], "2026-08-26", "2026-08-27"), _director())
    service.confirm(planned["requestId"], ConfirmBody.model_validate({"planHash": planned["planHash"]}), _director())
    ran = service.run(planned["requestId"], _director())
    assert ran["status"] == DataRequestState.PARTIAL
    pair = ran["execution"]["pairs"][0]
    assert pair["consolidated"] is False
    assert pair["claimStatus"] == ClaimStatus.UNAVAILABLE
    assert ran["execution"]["publishesFact"] is False
    assert ClaimStatus.FACT.value not in str(ran)
    assert "super-secret" not in str(ran)
    intact = previous[0]
    assert intact.status == STATUS_SUCESSO
    assert intact.data_referencia == DAY
    events = str(service._store.events(planned["requestId"]))
    assert "super-secret" not in events
    assert "https://erp.example" not in events
    assert "token=super-secret" not in events


def test_later_page_failure_does_not_commit_pair(tmp_path: Path) -> None:
    executor = FakeDataRefreshExecutor(fail_pages={(5555, "2026-08-26", 2)})
    service = _service(tmp_path, executor=executor)
    planned = service.plan(_body([5555], "2026-08-26", "2026-08-27"), _director())
    service.confirm(planned["requestId"], ConfirmBody.model_validate({"planHash": planned["planHash"]}), _director())
    ran = service.run(planned["requestId"], _director())
    pages = ran["execution"]["pairs"][0]["pages"]
    assert pages[0]["ok"] is True
    assert pages[1]["ok"] is False
    assert ran["execution"]["pairs"][0]["consolidated"] is False


def test_cancel_before_execution(tmp_path: Path) -> None:
    service = _service(tmp_path)
    planned = service.plan(_body([5555], "2026-08-26", "2026-08-27"), _director())
    service.confirm(planned["requestId"], ConfirmBody.model_validate({"planHash": planned["planHash"]}), _director())
    cancelled = service.cancel(planned["requestId"], _director())
    assert cancelled["status"] == DataRequestState.CANCELLED
    ran = service.run(planned["requestId"], _director())
    assert ran["code"] == "NOT_CLAIMED"


def test_cancel_during_committing_refused(tmp_path: Path) -> None:
    service = _service(tmp_path)
    planned = service.plan(_body([5555], "2026-08-26", "2026-08-27"), _director())
    service.confirm(planned["requestId"], ConfirmBody.model_validate({"planHash": planned["planHash"]}), _director())
    service._store.transition(
        planned["requestId"],
        DataRequestState.QUEUED,
        DataRequestState.COMMITTING,
        event="FORCE",
        detail={},
    )
    refused = service.cancel(planned["requestId"], _director())
    assert refused["code"] == "CANCEL_NOT_ALLOWED"
    assert refused["status"] == DataRequestState.COMMITTING


def test_http_router_isolated_not_in_app_py() -> None:
    app_text = Path("src/interfaces/http/app.py").read_text(encoding="utf-8")
    assert "executive_copilot_data_requests" not in app_text
    assert "data-requests" not in app_text


def test_http_plan_confirm_get_cancel(tmp_path: Path) -> None:
    service = _service(tmp_path)
    configure_data_on_demand(service)
    app = FastAPI()
    app.include_router(router)

    async def _user():
        return _director()

    app.dependency_overrides[get_current_user] = _user
    client = TestClient(app)
    planned = client.post(
        "/api/v1/executive-copilot/data-requests/plan",
        json={"unidades": [5555], "periodo": {"inicio": "2026-08-26", "fim": "2026-08-27"}},
    )
    assert planned.status_code == 200
    request_id = planned.json()["requestId"]
    confirmed = client.post(
        f"/api/v1/executive-copilot/data-requests/{request_id}/confirm",
        json={"planHash": planned.json()["planHash"]},
    )
    fetched = client.get(f"/api/v1/executive-copilot/data-requests/{request_id}")
    cancelled = client.post(f"/api/v1/executive-copilot/data-requests/{request_id}/cancel")
    extra = client.post(
        f"/api/v1/executive-copilot/data-requests/{request_id}/confirm",
        json={"planHash": planned.json()["planHash"], "unidades": [5555]},
    )
    assert confirmed.json()["status"] == DataRequestState.QUEUED
    assert fetched.json()["requestId"] == request_id
    assert cancelled.json()["status"] == DataRequestState.CANCELLED
    assert extra.status_code == 422


def test_http_requires_auth(tmp_path: Path) -> None:
    configure_data_on_demand(_service(tmp_path))
    app = FastAPI()
    app.include_router(router)

    async def _anon():
        raise HTTPException(status_code=401, detail="Not authenticated")

    app.dependency_overrides[get_current_user] = _anon
    client = TestClient(app)
    resp = client.post(
        "/api/v1/executive-copilot/data-requests/plan",
        json={"unidades": [5555], "periodo": {"inicio": "2026-08-26", "fim": "2026-08-27"}},
    )
    assert resp.status_code == 401


def test_package_has_no_network_imports() -> None:
    root = Path("src/services/executive_copilot/data_on_demand")
    imported: list[str] = []
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
    joined = " ".join(imported)
    assert "httpx" not in joined
    assert "webposto_client" not in joined
    assert "sds_catchup" not in joined
    assert "alembic" not in joined


def test_writes_constant_remains_zero() -> None:
    assert WEBPOSTO_WRITES == 0
