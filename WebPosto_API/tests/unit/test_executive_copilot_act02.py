"""ACT-02 — UnitCapabilities, fonte incompatível e CREATE_EXPENSE_DRAFT local."""

from __future__ import annotations

from datetime import date

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from src.core.config import OFFICIAL_COMPANY_CODES
from src.interfaces.http.dependencies import get_current_user
from src.interfaces.http.routes.executive_copilot_action_drafts import (
    configure_expense_drafts,
    router as drafts_router,
)
from src.services.ai_ops.models import connect_action_hub_db
from src.services.executive_copilot.action_proposals import ACTION_EXECUTION_NOT_ENABLED
from src.services.executive_copilot.contracts import WEBPOSTO_WRITES
from src.services.executive_copilot.coverage import DayCheckpoint, MemoryCheckpointStore
from src.services.executive_copilot.data_on_demand.executor import FakeDataRefreshExecutor
from src.services.executive_copilot.data_on_demand.models import PlanBody
from src.services.executive_copilot.data_on_demand.service import DataOnDemandService
from src.services.executive_copilot.data_on_demand.store import DataRequestStore
from src.services.executive_copilot.expense_drafts import ExpenseDraftService
from src.services.executive_copilot.http_models import AskRequest
from src.services.executive_copilot.metrics import MemoryFuelFactsStore, UnitDayFacts
from src.services.executive_copilot.orchestrator import ExecutiveCopilotOrchestrator
from src.services.executive_copilot.unit_capabilities import (
    CONVENIENCIA_24H,
    UNIT_SOURCE_NOT_APPLICABLE,
    UNIT_SOURCE_NOT_APPLICABLE_MESSAGE,
    codes_from_text,
    public_name,
    select_requested_units,
)
from src.services.sds_identity import LICENSED_SDS_CODES, STATUS_SUCESSO
from src.services.sds_process_lock import NullSdsProcessLock

DAY = date(2026, 8, 27)
PERIOD = {"inicio": "2026-08-27", "fim": "2026-08-27"}


@pytest.fixture(autouse=True)
def block_external_http(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("chamada externa proibida")

    monkeypatch.setattr(httpx, "Client", boom)
    monkeypatch.setattr(httpx, "AsyncClient", boom)


def _director() -> dict:
    return {"role": "director", "sub": "qa.act02@logos.test", "email": "qa.act02@logos.test"}


def _manager(unit: int = 5555) -> dict:
    return {"role": "manager", "company_id": unit, "sub": "mgr@logos.test"}


def _ask(**overrides) -> AskRequest:
    payload = {
        "pergunta": "Qual o faturamento de combustível?",
        "especialista": "FINANCEIRO",
        "unidades": [5555],
        "periodo": PERIOD,
    }
    payload.update(overrides)
    return AskRequest.model_validate(payload)


def _orch(*units: int) -> ExecutiveCopilotOrchestrator:
    codes = units or (5555, 11495, 74014)
    return ExecutiveCopilotOrchestrator(
        checkpoint_store=MemoryCheckpointStore(
            [DayCheckpoint(unit, DAY, STATUS_SUCESSO, 10) for unit in codes]
        ),
        facts_store=MemoryFuelFactsStore(
            [UnitDayFacts(unit, DAY, STATUS_SUCESSO, 100.0, 500.0, 10) for unit in codes]
        ),
    )


def test_public_names_and_aliases_from_config() -> None:
    assert OFFICIAL_COMPANY_CODES[-1] == CONVENIENCIA_24H == 118508
    assert public_name(5555) == "AP Casa Caiada"
    assert public_name(11495) == "Posto VIP"
    assert public_name(74014) == "Posto Real/Doze"
    assert public_name(118508) == "Conveniência 24 Horas"
    for alias in (
        "Conveniência 24 Horas",
        "Conveniencia 24 Horas",
        "Conveniência 24H",
        "Conveniencia 24H",
        "Loja 24 Horas",
        "Loja 24H",
    ):
        found = codes_from_text(alias)
        assert found.codes == [118508]
        assert found.ambiguous is False
    assert 6666 not in codes_from_text("VIP").codes
    assert codes_from_text("6666").codes == [11495]


def test_loja_isolated_is_ambiguous() -> None:
    found = codes_from_text("Lance uma despesa na loja")
    assert found.ambiguous is True
    answer = _orch().ask(
        _ask(pergunta="Lance uma despesa de R$ 120 de gelo na loja", especialista="FINANCEIRO"),
        _director(),
    )
    assert answer.impact.status.value == "BLOCKED"
    assert answer.blocked.code == "UNIT_NAME_AMBIGUOUS"


def test_codes_stay_technical_and_6666_never_public() -> None:
    selection = select_requested_units("Posto VIP", [6666])
    assert selection.codes == [11495]
    assert 6666 not in selection.codes
    answer = _orch(11495).ask(_ask(unidades=[6666], pergunta="Quantos litros?"), _director())
    assert 6666 not in answer.units
    assert "6666" not in str(answer.to_public_payload())
    assert answer.unit_public_names == ["Posto VIP"]


def test_fuel_on_convenience_is_not_applicable() -> None:
    answer = _orch().ask(
        _ask(pergunta="Quantos litros na Conveniência 24 Horas?", especialista="OPERACIONAL", unidades=[118508]),
        _director(),
    )
    assert answer.impact.status.value == "BLOCKED"
    assert answer.blocked.code == UNIT_SOURCE_NOT_APPLICABLE
    assert answer.blocked.message == UNIT_SOURCE_NOT_APPLICABLE_MESSAGE
    assert answer.impact.amount is None


def test_todas_litros_uses_only_three_pistas() -> None:
    orch = _orch(5555, 11495, 74014)
    answer = orch.ask(
        _ask(pergunta="Quantos litros em todas as unidades?", especialista="OPERACIONAL", unidades=None),
        _director(),
    )
    assert answer.impact.status.value == "FACT"
    assert set(answer.units) == set(LICENSED_SDS_CODES)
    assert 118508 not in answer.units
    assert "Conveniência 24 Horas" not in answer.fact


def test_convenience_does_not_create_abastecimento_request(tmp_path) -> None:
    store = DataRequestStore(tmp_path / "dod.sqlite")
    service = DataOnDemandService(
        store,
        MemoryCheckpointStore([DayCheckpoint(5555, DAY, STATUS_SUCESSO, 10)]),
        executor=FakeDataRefreshExecutor(),
        process_lock=NullSdsProcessLock(),
    )
    result = service.plan(
        PlanBody.model_validate({"unidades": [118508], "periodo": {"inicio": "2026-08-26", "fim": "2026-08-27"}}),
        _director(),
    )
    assert result.get("blocked", {}).get("code") == UNIT_SOURCE_NOT_APPLICABLE
    assert result.get("missingPairs") == []
    assert result.get("requestId") in (None, "")
    mixed = service.plan(
        PlanBody.model_validate({"unidades": [5555, 118508], "periodo": {"inicio": "2026-08-26", "fim": "2026-08-27"}}),
        _director(),
    )
    assert 118508 not in (mixed.get("units") or [])
    for gap in mixed.get("missingPairs") or []:
        assert gap["unidade"] != 118508


def test_natural_expense_preview_does_not_persist(tmp_path) -> None:
    db = str(tmp_path / "hub.sqlite")
    with connect_action_hub_db(db):
        pass
    orch = _orch()
    answer = orch.ask(
        _ask(
            pergunta="Lance uma despesa de R$ 120 de gelo na Conveniência 24 Horas.",
            especialista="FINANCEIRO",
            unidades=[5555],
        ),
        _director(),
    )
    action = answer.suggested_action or {}
    assert action["persisted"] is False
    assert action["unitPublicName"] == "Conveniência 24 Horas"
    assert action["filledFields"]["valor"] == 120.0
    assert action["filledFields"]["descricao"] == "gelo"
    assert "empresaCodigo" not in action["filledFields"]
    assert "empresaCodigo" not in action["camposPreenchidos"]
    assert action["autoClassifiedFields"][0]["status"] == "AUTO_CLASSIFIED"
    assert action["webpostoWrites"] == 0
    with connect_action_hub_db(db) as conn:
        n = conn.execute("SELECT COUNT(*) FROM webposto_action_hub_copilot_drafts").fetchone()[0]
    assert n == 0


def test_save_confirm_approve_and_execute_blocked(tmp_path) -> None:
    db = str(tmp_path / "hub.sqlite")
    service = ExpenseDraftService(db_path=db)
    saved = service.save(
        user=_director(),
        unit=118508,
        valor=120.0,
        descricao="gelo",
    )
    assert saved["ok"] is True
    assert saved["duplicate"] is False
    assert saved["status"] == "DRAFT"
    assert saved["draftId"]
    assert saved["unitPublicName"] == "Conveniência 24 Horas"
    assert saved["filledFields"]["valor"] == 120.0
    assert saved["filledFields"]["descricao"] == "gelo"
    assert "empresaCodigo" not in saved["filledFields"]
    assert saved["autoClassifiedFields"][0]["status"] == "AUTO_CLASSIFIED"
    assert saved["canExecute"] is False
    assert saved["executionCode"] == ACTION_EXECUTION_NOT_ENABLED
    assert saved["webpostoWrites"] == WEBPOSTO_WRITES == 0
    assert "6666" not in str(saved)
    first_id = saved["draftId"]

    dup = service.save(user=_director(), unit=118508, valor=120.0, descricao="gelo")
    assert dup["duplicate"] is True
    assert dup["draftId"] == first_id

    confirmed = service.confirm(first_id, _director())
    assert confirmed["status"] == "CONFIRMED"
    approved = service.approve(first_id, _director())
    assert approved["status"] == "APPROVED_LOCAL"
    assert approved["canExecute"] is False
    executed = service.execute(first_id, _director())
    assert executed["status"] == "EXECUTION_BLOCKED"
    assert executed["blocked"]["code"] == ACTION_EXECUTION_NOT_ENABLED
    assert executed["webpostoWrites"] == 0


def test_action_without_unit_and_todas_blocked() -> None:
    orch = _orch()
    missing = orch.ask(
        _ask(pergunta="Lance uma despesa de R$ 120 de gelo", especialista="FINANCEIRO", unidades=None),
        _director(),
    )
    assert missing.impact.status.value == "BLOCKED"
    assert missing.blocked.code == "UNIT_REQUIRED_FOR_ACTION"
    todas = orch.ask(
        _ask(
            pergunta="Lance uma despesa de R$ 120 de gelo em todas as unidades",
            especialista="FINANCEIRO",
            unidades=None,
        ),
        _director(),
    )
    assert todas.impact.status.value == "BLOCKED"
    assert todas.blocked.code == "ACTION_NETWORK_SCOPE_FORBIDDEN"


def test_manager_limited_and_approval_revalidated(tmp_path) -> None:
    db = str(tmp_path / "hub.sqlite")
    service = ExpenseDraftService(db_path=db)
    denied = service.save(user=_manager(5555), unit=118508, valor=120.0, descricao="gelo")
    assert denied.get("blocked", {}).get("code") == "UNIT_FORBIDDEN_FOR_USER"
    saved = service.save(user=_manager(118508), unit=118508, valor=120.0, descricao="gelo")
    assert saved["ok"] is True
    confirmed = service.confirm(saved["draftId"], _manager(118508))
    assert confirmed["status"] == "CONFIRMED"
    approve = service.approve(saved["draftId"], _manager(118508))
    assert approve.get("blocked", {}).get("code") == "APPROVAL_FORBIDDEN"
    other = service.approve(saved["draftId"], _manager(5555))
    assert other.get("blocked", {}).get("code") == "UNIT_FORBIDDEN_FOR_USER"


def test_http_expense_draft_roundtrip(tmp_path) -> None:
    db = str(tmp_path / "hub.sqlite")
    service = ExpenseDraftService(db_path=db)
    configure_expense_drafts(service)
    app = FastAPI()
    app.include_router(drafts_router)

    async def _user():
        return _director()

    app.dependency_overrides[get_current_user] = _user
    client = TestClient(app)
    created = client.post(
        "/api/v1/executive-copilot/action-drafts/expenses",
        json={
            "pergunta": "Lance uma despesa de R$ 120 de gelo na Conveniência 24 Horas.",
            "unitPublicName": "Conveniência 24 Horas",
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert body["actionType"] == "CREATE_EXPENSE_DRAFT"
    assert body["unitPublicName"] == "Conveniência 24 Horas"
    assert "empresaCodigo" not in body["filledFields"]
    draft_id = body["draftId"]
    got = client.get(f"/api/v1/executive-copilot/action-drafts/{draft_id}")
    assert got.status_code == 200
    confirmed = client.post(f"/api/v1/executive-copilot/action-drafts/{draft_id}/confirm")
    assert confirmed.json()["status"] == "CONFIRMED"
    approved = client.post(f"/api/v1/executive-copilot/action-drafts/{draft_id}/approve")
    assert approved.json()["status"] == "APPROVED_LOCAL"
    executed = client.post(f"/api/v1/executive-copilot/action-drafts/{draft_id}/execute")
    assert executed.json()["executionCode"] == ACTION_EXECUTION_NOT_ENABLED
    assert executed.json()["webpostoWrites"] == 0


def test_http_without_auth_is_401(tmp_path) -> None:
    configure_expense_drafts(ExpenseDraftService(db_path=str(tmp_path / "hub.sqlite")))
    app = FastAPI()
    app.include_router(drafts_router)

    async def _anon():
        raise HTTPException(status_code=401, detail="Not authenticated")

    app.dependency_overrides[get_current_user] = _anon
    client = TestClient(app)
    resp = client.post("/api/v1/executive-copilot/action-drafts/expenses", json={"descricao": "gelo"})
    assert resp.status_code == 401
