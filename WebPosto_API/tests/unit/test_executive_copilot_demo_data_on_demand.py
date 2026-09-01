"""DATA-ON-DEMAND-01B — router no demo_app com FakeDataRefreshExecutor. Sem rede."""

from __future__ import annotations

import ast
import threading
from datetime import date, datetime, timezone
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from src.infrastructure.security.jwt_utils import create_access_token
from src.interfaces.http.routes.executive_copilot_ask import configure_orchestrator
from src.services.executive_copilot.coverage import DayCheckpoint, MemoryCheckpointStore
from src.services.executive_copilot.data_on_demand.executor import FakeDataRefreshExecutor
from src.services.executive_copilot.data_on_demand.http_contract import PUBLIC_KEYS
from src.services.executive_copilot.data_on_demand.models import ConfirmBody, PlanBody
from src.services.executive_copilot.data_on_demand.service import DataOnDemandService
from src.services.executive_copilot.data_on_demand.states import DataRequestState
from src.services.executive_copilot.data_on_demand.store import DataRequestStore
from src.services.executive_copilot.demo_app import create_demo_app, demo_cli_error
from src.services.executive_copilot.metrics import MemoryFuelFactsStore, UnitDayFacts
from src.services.executive_copilot.orchestrator import ExecutiveCopilotOrchestrator
from src.services.sds_identity import STATUS_SUCESSO
from src.services.sds_process_lock import NullSdsProcessLock

DAY = date(2026, 8, 27)
PLAN = {"unidades": [5555], "periodo": {"inicio": "2026-08-26", "fim": "2026-08-27"}}


@pytest.fixture(autouse=True)
def block_external_http(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("chamada externa proibida")

    monkeypatch.setattr(httpx, "Client", boom)
    monkeypatch.setattr(httpx, "AsyncClient", boom)


def _clock() -> datetime:
    return datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)


def _check(unit: int, day: date = DAY) -> DayCheckpoint:
    return DayCheckpoint(unit, day, STATUS_SUCESSO, 10)


def _dod(
    tmp_path: Path,
    rows: list[DayCheckpoint] | None = None,
    *,
    executor: FakeDataRefreshExecutor | None = None,
    lock=None,
    ttl: int = 900,
    auto_run: bool = True,
) -> DataOnDemandService:
    return DataOnDemandService(
        DataRequestStore(tmp_path / "dod.sqlite"),
        MemoryCheckpointStore(rows or [_check(5555), _check(11495), _check(74014)]),
        executor=executor or FakeDataRefreshExecutor(auto_by_units=True),
        process_lock=lock or NullSdsProcessLock(),
        clock=_clock,
        ttl_seconds=ttl,
        auto_run_on_confirm=auto_run,
    )


def _orch() -> ExecutiveCopilotOrchestrator:
    return ExecutiveCopilotOrchestrator(
        checkpoint_store=MemoryCheckpointStore([_check(5555)]),
        facts_store=MemoryFuelFactsStore(
            [UnitDayFacts(5555, DAY, STATUS_SUCESSO, 100.0, 500.0, 10)]
        ),
    )


def _client(tmp_path: Path, service: DataOnDemandService | None = None) -> TestClient:
    configure_orchestrator(_orch())
    return TestClient(create_demo_app(data_on_demand_service=service or _dod(tmp_path)))


def _headers(role: str = "director", **extra) -> dict[str, str]:
    token = create_access_token("qa.dod.demo@logos.test", extra={"role": role, **extra})
    return {"Authorization": f"Bearer {token}"}


def _plan(client: TestClient, body: dict | None = None, **header_kw):
    return client.post(
        "/api/v1/executive-copilot/data-requests/plan",
        json=body or PLAN,
        headers=_headers(**header_kw),
    )


def test_demo_plan_requires_auth(tmp_path: Path) -> None:
    client = _client(tmp_path)
    resp = client.post("/api/v1/executive-copilot/data-requests/plan", json=PLAN)
    assert resp.status_code == 401


def test_demo_plan_forbids_wrong_role(tmp_path: Path) -> None:
    client = _client(tmp_path)
    resp = _plan(client, role="cashier")
    assert resp.status_code == 403


def test_demo_manager_unit_isolation(tmp_path: Path) -> None:
    client = _client(tmp_path)
    resp = _plan(client, {"unidades": [11495], "periodo": {"inicio": "2026-08-26", "fim": "2026-08-27"}}, role="manager", company_id=5555)
    assert resp.status_code == 200
    assert resp.json()["blocked"]["code"] == "UNIT_FORBIDDEN_FOR_USER"
    assert resp.json()["webpostoWrites"] == 0


def test_demo_plan_already_available(tmp_path: Path) -> None:
    client = _client(tmp_path)
    resp = _plan(client, {"unidades": [5555], "periodo": {"inicio": "2026-08-27", "fim": "2026-08-27"}})
    body = resp.json()
    assert resp.status_code == 200
    assert body["status"] == DataRequestState.ALREADY_AVAILABLE
    assert body["requestId"] is None
    assert body["requiresConfirmation"] is False
    assert body["created"] is False
    assert body["executorMode"] == "FAKE_LOCAL"
    assert body["externalRequests"] == 0
    assert body["dataChanged"] is False


def test_demo_plan_with_gaps_contract(tmp_path: Path) -> None:
    client = _client(tmp_path)
    body = _plan(client).json()
    for key in PUBLIC_KEYS:
        assert key in body
    assert body["status"] == DataRequestState.AWAITING_CONFIRMATION
    assert body["requiresConfirmation"] is True
    assert body["logicalEndpoint"] == "ABASTECIMENTO"
    assert body["missingPairs"] == [{"unidade": 5555, "data": "2026-08-26"}]
    assert body["requestedPeriod"] == {"inicio": "2026-08-26", "fim": "2026-08-27"}
    assert body["confirmationExpiresAt"]
    assert "sqlite" not in str(body).casefold()
    assert "pid" not in str(body).casefold()


def test_demo_confirm_and_progress_success(tmp_path: Path) -> None:
    client = _client(tmp_path)
    planned = _plan(client).json()
    confirmed = client.post(
        f"/api/v1/executive-copilot/data-requests/{planned['requestId']}/confirm",
        json={"planHash": planned["planHash"]},
        headers=_headers(),
    ).json()
    progress = client.get(
        f"/api/v1/executive-copilot/data-requests/{planned['requestId']}",
        headers=_headers(),
    ).json()
    assert confirmed["status"] == DataRequestState.SUCCESS
    assert progress["status"] == DataRequestState.SUCCESS
    assert progress["progress"]["pairsDone"] == 1
    assert progress["externalRequests"] == 0
    assert progress["dataChanged"] is False
    assert progress["publishesFact"] is False


def test_demo_invalid_plan_hash(tmp_path: Path) -> None:
    client = _client(tmp_path)
    planned = _plan(client).json()
    resp = client.post(
        f"/api/v1/executive-copilot/data-requests/{planned['requestId']}/confirm",
        json={"planHash": "0" * 64},
        headers=_headers(),
    ).json()
    assert resp["code"] == "PLAN_HASH_MISMATCH"
    assert resp["status"] == DataRequestState.AWAITING_CONFIRMATION


def test_demo_expired_plan(tmp_path: Path) -> None:
    client = _client(tmp_path, _dod(tmp_path, ttl=0, auto_run=False))
    planned = _plan(client).json()
    resp = client.post(
        f"/api/v1/executive-copilot/data-requests/{planned['requestId']}/confirm",
        json={"planHash": planned["planHash"]},
        headers=_headers(),
    ).json()
    assert resp["status"] == DataRequestState.EXPIRED
    assert resp["ok"] is False


def test_demo_plan_idempotency(tmp_path: Path) -> None:
    client = _client(tmp_path)
    first = _plan(client).json()
    second = _plan(client).json()
    assert first["requestId"] == second["requestId"]


def test_demo_confirm_idempotent(tmp_path: Path) -> None:
    client = _client(tmp_path)
    planned = _plan(client).json()
    url = f"/api/v1/executive-copilot/data-requests/{planned['requestId']}/confirm"
    first = client.post(url, json={"planHash": planned["planHash"]}, headers=_headers()).json()
    second = client.post(url, json={"planHash": planned["planHash"]}, headers=_headers()).json()
    assert first["requestId"] == second["requestId"]
    assert first["status"] == second["status"] == DataRequestState.SUCCESS


def test_demo_dispute_single_execution(tmp_path: Path) -> None:
    executor = FakeDataRefreshExecutor()
    service = _dod(tmp_path, executor=executor, auto_run=False)
    client = _client(tmp_path, service)
    planned = _plan(client).json()
    client.post(
        f"/api/v1/executive-copilot/data-requests/{planned['requestId']}/confirm",
        json={"planHash": planned["planHash"]},
        headers=_headers(),
    )
    results: list[dict] = []

    def worker() -> None:
        results.append(service.run(planned["requestId"], {"role": "director", "sub": "qa.dod.demo@logos.test"}))

    threads = [threading.Thread(target=worker), threading.Thread(target=worker)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)
    assert len(executor.calls) == 1
    assert sum(1 for item in results if item.get("code") == "NOT_CLAIMED") == 1


def test_demo_cancel_before_run(tmp_path: Path) -> None:
    client = _client(tmp_path, _dod(tmp_path, auto_run=False))
    planned = _plan(client).json()
    cancelled = client.post(
        f"/api/v1/executive-copilot/data-requests/{planned['requestId']}/cancel",
        headers=_headers(),
    ).json()
    assert cancelled["status"] == DataRequestState.CANCELLED


def test_demo_partial_never_fact(tmp_path: Path) -> None:
    client = _client(tmp_path)
    planned = _plan(
        client,
        {"unidades": [11495], "periodo": {"inicio": "2026-08-26", "fim": "2026-08-27"}},
    ).json()
    confirmed = client.post(
        f"/api/v1/executive-copilot/data-requests/{planned['requestId']}/confirm",
        json={"planHash": planned["planHash"]},
        headers=_headers(),
    ).json()
    assert confirmed["status"] == DataRequestState.PARTIAL
    assert confirmed["publishesFact"] is False
    assert confirmed["dataChanged"] is False
    assert "FACT" not in str(confirmed["execution"]["pairs"])


def test_demo_failed_fake(tmp_path: Path) -> None:
    client = _client(tmp_path)
    planned = _plan(
        client,
        {"unidades": [74014], "periodo": {"inicio": "2026-08-26", "fim": "2026-08-27"}},
    ).json()
    confirmed = client.post(
        f"/api/v1/executive-copilot/data-requests/{planned['requestId']}/confirm",
        json={"planHash": planned["planHash"]},
        headers=_headers(),
    ).json()
    assert confirmed["status"] == DataRequestState.FAILED
    assert confirmed["externalRequests"] == 0
    assert confirmed["executorMode"] == "FAKE_LOCAL"


def test_demo_locked(tmp_path: Path) -> None:
    class Deny:
        def acquire(self, trigger: str = "manual") -> bool:
            return False

        def release(self) -> bool:
            return True

        def peek(self):
            return None

    client = _client(tmp_path, _dod(tmp_path, lock=Deny()))
    planned = _plan(client).json()
    confirmed = client.post(
        f"/api/v1/executive-copilot/data-requests/{planned['requestId']}/confirm",
        json={"planHash": planned["planHash"]},
        headers=_headers(),
    ).json()
    assert confirmed["status"] == DataRequestState.LOCKED


def test_fake_executor_zero_external_and_sds_intact(tmp_path: Path) -> None:
    rows = [_check(5555)]
    store = MemoryCheckpointStore(rows)
    executor = FakeDataRefreshExecutor()
    service = DataOnDemandService(
        DataRequestStore(tmp_path / "dod.sqlite"),
        store,
        executor=executor,
        process_lock=NullSdsProcessLock(),
        clock=_clock,
        auto_run_on_confirm=True,
    )
    planned = service.plan(PlanBody.model_validate(PLAN), {"role": "director"})
    service.confirm(
        planned["requestId"],
        ConfirmBody.model_validate({"planHash": planned["planHash"]}),
        {"role": "director"},
    )
    assert executor.external_requests == 0
    assert store.list_days([5555], DAY, DAY)[0].status == STATUS_SUCESSO
    assert store.list_available([5555]) == rows


def test_demo_app_does_not_bind_and_refuses_8040() -> None:
    create_demo_app()
    assert demo_cli_error(bind=False, host="127.0.0.1", port=8095)
    assert demo_cli_error(bind=True, host="127.0.0.1", port=8040)


def test_ask_and_coverage_regression(tmp_path: Path) -> None:
    client = _client(tmp_path)
    ask = client.post(
        "/api/v1/executive-copilot/ask",
        json={
            "pergunta": "Qual o faturamento?",
            "especialista": "FINANCEIRO",
            "unidades": [5555],
            "periodo": {"inicio": "2026-08-27", "fim": "2026-08-27"},
        },
        headers=_headers(),
    )
    coverage = client.get("/api/v1/executive-copilot/coverage", params={"unidades": [5555]}, headers=_headers())
    health = client.get("/health")
    assert ask.status_code == 200
    assert ask.json()["impact"]["status"] == "FACT"
    assert coverage.status_code == 200
    assert coverage.json()["source"] == "LOCAL_CHECKPOINT"
    assert health.json() == {"service": "executive-copilot-local", "webpostoWrites": 0}


def test_demo_app_imports_stay_local() -> None:
    tree = ast.parse(Path("src/services/executive_copilot/demo_app.py").read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    joined = " ".join(imported)
    assert "httpx" not in joined
    assert "webposto_client" not in joined
    assert "sds_catchup" not in joined
    assert "src.jobs" not in joined
