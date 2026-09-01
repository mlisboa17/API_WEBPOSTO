"""Cobertura dinâmica, formatação pt-BR e health isolado. Sem rede."""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from src.infrastructure.security.jwt_utils import create_access_token
from src.interfaces.http.dependencies import get_current_user
from src.interfaces.http.routes.executive_copilot_ask import configure_orchestrator, router
from src.services.executive_copilot.coverage import (
    DayCheckpoint,
    MemoryCheckpointStore,
    common_checkpoint_coverage,
)
from src.services.executive_copilot.demo_app import create_demo_app
from src.services.executive_copilot.http_models import AskRequest
from src.services.executive_copilot.llm_port import _brl, _format_observed_delta
from src.services.executive_copilot.metrics import MemoryFuelFactsStore, UnitDayFacts
from src.services.executive_copilot.orchestrator import ExecutiveCopilotOrchestrator
from src.services.sds_identity import STATUS_FALHA, STATUS_SUCESSO

DAY = date(2026, 8, 27)


@pytest.fixture(autouse=True)
def block_external_http(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("chamada externa proibida")

    monkeypatch.setattr(httpx, "Client", boom)
    monkeypatch.setattr(httpx, "AsyncClient", boom)


def _check(unit: int, day: date, status: str = STATUS_SUCESSO) -> DayCheckpoint:
    return DayCheckpoint(unit, day, status, 10)


def _days(start: date, end: date) -> list[date]:
    out: list[date] = []
    cursor = start
    while cursor <= end:
        out.append(cursor)
        cursor += timedelta(days=1)
    return out


def _store_common() -> MemoryCheckpointStore:
    rows = [_check(unit, day) for unit in (5555, 11495) for day in _days(date(2026, 8, 13), date(2026, 8, 28))]
    return MemoryCheckpointStore(rows)


def _orch_from_store(store: MemoryCheckpointStore) -> ExecutiveCopilotOrchestrator:
    facts = [
        UnitDayFacts(row.empresa_codigo, row.data_referencia, STATUS_SUCESSO, 10.0, 50.0, 2)
        for row in store.list_available([5555, 11495])
        if row.status == STATUS_SUCESSO
    ]
    return ExecutiveCopilotOrchestrator(checkpoint_store=store, facts_store=MemoryFuelFactsStore(facts))


def _http(orch: ExecutiveCopilotOrchestrator, user: dict | None) -> TestClient:
    configure_orchestrator(orch)
    app = FastAPI()
    app.include_router(router)

    async def _user():
        if user is None:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return user

    app.dependency_overrides[get_current_user] = _user
    return TestClient(app)


def test_financial_delta_is_pt_br() -> None:
    assert _brl(576795.36) == "R$ 576.795,36"
    assert _format_observed_delta("faturamento", 576795.36) == "R$ 576.795,36"
    assert "576,795.36" not in _format_observed_delta("faturamento", 576795.36)
    orch = ExecutiveCopilotOrchestrator(
        checkpoint_store=MemoryCheckpointStore([_check(5555, DAY), _check(11495, DAY)]),
        facts_store=MemoryFuelFactsStore(
            [
                UnitDayFacts(5555, DAY, STATUS_SUCESSO, 10.0, 100000.00, 10),
                UnitDayFacts(11495, DAY, STATUS_SUCESSO, 10.0, 676795.36, 10),
            ]
        ),
    )
    answer = orch.ask(
        AskRequest.model_validate(
            {
                "pergunta": "Compare o faturamento entre as unidades",
                "especialista": "PRESIDENTE",
                "unidades": [5555, 11495],
                "periodo": {"inicio": "2026-08-27", "fim": "2026-08-27"},
            }
        ),
        {"role": "director"},
    )
    assert "R$ 576.795,36" in answer.inference
    assert "576,795.36" not in answer.inference
    assert "AP Casa Caiada teve o menor faturamento" in answer.recommendation
    assert "economia atribuída" in answer.recommendation.casefold() or "economia atribuida" in answer.recommendation.casefold()
    assert "vazamento" not in answer.recommendation.casefold()
    assert "perdeu" not in answer.recommendation.casefold()


def test_common_coverage_is_intersection_not_max_date() -> None:
    rows = [
        *[_check(5555, day) for day in _days(date(2026, 8, 13), date(2026, 8, 28))],
        *[_check(11495, day) for day in _days(date(2026, 8, 13), date(2026, 8, 20))],
        *[_check(11495, day, STATUS_FALHA) for day in _days(date(2026, 8, 21), date(2026, 8, 28))],
    ]
    report = common_checkpoint_coverage(MemoryCheckpointStore(rows), [5555, 11495])
    payload = report.to_public_payload()
    assert payload["firstCompleteDate"] == "2026-08-13"
    assert payload["lastCompleteDate"] == "2026-08-20"
    assert payload["suggestedStartDate"] == "2026-08-13"
    assert payload["suggestedEndDate"] == "2026-08-20"
    assert payload["source"] == "LOCAL_CHECKPOINT"
    assert payload["webpostoWrites"] == 0
    assert payload["empty"] is False
    assert payload["lastCompleteDate"] != "2026-08-28"
    assert any(gap["data"] == "2026-08-21" and 11495 in gap["unidades"] for gap in payload["gaps"])


def test_coverage_reports_interior_gaps_and_longest_window() -> None:
    rows = []
    for unit in (5555, 11495):
        rows.extend(_check(unit, day) for day in _days(date(2026, 8, 13), date(2026, 8, 20)))
        rows.extend(_check(unit, day) for day in _days(date(2026, 8, 22), date(2026, 8, 28)))
    report = common_checkpoint_coverage(MemoryCheckpointStore(rows), [5555, 11495])
    assert report.first_complete == date(2026, 8, 13)
    assert report.last_complete == date(2026, 8, 28)
    assert report.suggested_start == date(2026, 8, 13)
    assert report.suggested_end == date(2026, 8, 20)
    assert any(gap["data"] == "2026-08-21" for gap in report.gaps)


def test_coverage_empty_is_explicit() -> None:
    payload = common_checkpoint_coverage(MemoryCheckpointStore(), [5555, 11495]).to_public_payload()
    assert payload["empty"] is True
    assert payload["firstCompleteDate"] is None
    assert payload["lastCompleteDate"] is None
    assert payload["suggestedStartDate"] is None
    assert payload["suggestedEndDate"] is None
    assert payload["source"] == "LOCAL_CHECKPOINT"
    assert payload["webpostoWrites"] == 0


def test_http_coverage_requires_auth() -> None:
    client = _http(_orch_from_store(_store_common()), None)
    resp = client.get("/api/v1/executive-copilot/coverage", params={"unidades": [5555, 11495]})
    assert resp.status_code == 401


def test_http_coverage_respects_unit_scope() -> None:
    client = _http(_orch_from_store(_store_common()), {"role": "manager", "company_id": 5555})
    forbidden = client.get("/api/v1/executive-copilot/coverage", params={"unidades": [11495]})
    allowed = client.get("/api/v1/executive-copilot/coverage", params={"unidades": [5555]})
    assert forbidden.status_code == 200
    assert forbidden.json()["blocked"]["code"] == "UNIT_FORBIDDEN_FOR_USER"
    assert forbidden.json()["empty"] is True
    assert forbidden.json()["webpostoWrites"] == 0
    assert allowed.status_code == 200
    assert allowed.json()["units"] == [5555]
    assert allowed.json()["empty"] is False
    assert allowed.json()["source"] == "LOCAL_CHECKPOINT"


def test_http_coverage_common_window() -> None:
    client = _http(_orch_from_store(_store_common()), {"role": "director"})
    resp = client.get("/api/v1/executive-copilot/coverage", params={"unidades": [5555, 11495]})
    body = resp.json()
    assert resp.status_code == 200
    assert body["firstCompleteDate"] == "2026-08-13"
    assert body["lastCompleteDate"] == "2026-08-28"
    assert body["suggestedStartDate"] == "2026-08-13"
    assert body["suggestedEndDate"] == "2026-08-28"
    assert body["gaps"] == []
    assert body["webpostoWrites"] == 0


def test_demo_health_has_no_side_effects(monkeypatch) -> None:
    def boom(*_a, **_k):
        raise AssertionError("health nao pode abrir sqlite")

    monkeypatch.setattr(sqlite3, "connect", boom)
    client = TestClient(create_demo_app())
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"service": "executive-copilot-local", "webpostoWrites": 0}


def test_ask_regression_still_facts_after_coverage() -> None:
    orch = _orch_from_store(
        MemoryCheckpointStore([_check(5555, DAY), _check(11495, DAY)])
    )
    client = _http(orch, {"role": "director"})
    ask = client.post(
        "/api/v1/executive-copilot/ask",
        json={
            "pergunta": "Qual o faturamento?",
            "especialista": "FINANCEIRO",
            "unidades": [5555],
            "periodo": {"inicio": "2026-08-27", "fim": "2026-08-27"},
        },
    )
    coverage = client.get("/api/v1/executive-copilot/coverage", params={"unidades": [5555]})
    assert ask.status_code == 200
    assert ask.json()["impact"]["status"] == "FACT"
    assert ask.json()["webpostoWrites"] == 0
    assert coverage.status_code == 200
    assert coverage.json()["source"] == "LOCAL_CHECKPOINT"


def test_demo_coverage_uses_official_auth() -> None:
    configure_orchestrator(_orch_from_store(_store_common()))
    client = TestClient(create_demo_app())
    denied = client.get("/api/v1/executive-copilot/coverage", params={"unidades": [5555]})
    token = create_access_token("qa.coverage@logos.test", extra={"role": "director"})
    allowed = client.get(
        "/api/v1/executive-copilot/coverage",
        params={"unidades": [5555, 11495]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert denied.status_code == 401
    assert allowed.status_code == 200
    assert allowed.json()["empty"] is False
