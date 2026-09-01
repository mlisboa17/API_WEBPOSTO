"""Roteiro da demonstração contra a fonte local SDS. Sem rede e sem servidor."""

from __future__ import annotations

from datetime import date

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from src.interfaces.http.dependencies import get_current_user
from src.interfaces.http.routes.executive_copilot_ask import configure_orchestrator, router
from src.services.executive_copilot.coverage import DayCheckpoint, MemoryCheckpointStore
from src.services.executive_copilot.http_models import AskRequest
from src.services.executive_copilot.intent import QuestionIntent, interpret_question
from src.services.executive_copilot.llm_port import _brl, _liters, _qty
from src.services.executive_copilot.local_store import SqliteCheckpointStore, SqliteFuelFactsStore
from src.services.executive_copilot.metrics import MemoryFuelFactsStore, UnitDayFacts, aggregate_network
from src.services.executive_copilot.orchestrator import ExecutiveCopilotOrchestrator
from src.services.executive_copilot.unit_capabilities import public_name
from src.services.sds_identity import LICENSED_SDS_CODES, STATUS_SUCESSO

PERIOD = {"inicio": "2026-08-13", "fim": "2026-08-28"}
START = date(2026, 8, 13)
END = date(2026, 8, 28)


@pytest.fixture(autouse=True)
def block_external_http(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("chamada externa proibida")

    monkeypatch.setattr(httpx, "Client", boom)
    monkeypatch.setattr(httpx, "AsyncClient", boom)


def _director() -> dict:
    return {"role": "director"}


def _local_orch() -> ExecutiveCopilotOrchestrator:
    return ExecutiveCopilotOrchestrator(
        checkpoint_store=SqliteCheckpointStore(),
        facts_store=SqliteFuelFactsStore(),
    )


def _ask(pergunta: str, especialista: str = "OPERACIONAL") -> AskRequest:
    return AskRequest.model_validate(
        {
            "pergunta": pergunta,
            "especialista": especialista,
            "unidades": list(LICENSED_SDS_CODES),
            "periodo": PERIOD,
        }
    )


def test_demo_script_four_questions_match_local_source() -> None:
    facts = SqliteFuelFactsStore().list_facts(list(LICENSED_SDS_CODES), START, END)
    metrics = aggregate_network(facts, list(LICENSED_SDS_CODES), START, END)
    orch = _local_orch()
    user = _director()

    sales = orch.ask(_ask("Compare o faturamento entre as unidades.", "PRESIDENTE"), user)
    total_fat = round(sum(item.faturamento for item in metrics.values()), 2)
    assert sales.impact.status.value == "FACT"
    assert sales.impact.amount == total_fat
    assert sales.suggested_action["engine"] == "deterministic"
    assert sales.suggested_action["llm"] is False
    for unit, metric in metrics.items():
        assert public_name(unit) in sales.fact
        assert _brl(metric.faturamento) in sales.fact

    ticket = orch.ask(_ask("Qual o ticket médio de cada unidade?"), user)
    assert ticket.impact.status.value == "FACT"
    assert ticket.impact.amount is None
    for unit, metric in metrics.items():
        assert metric.contagem_confiavel
        assert metric.ticket_reais is not None
        assert public_name(unit) in ticket.fact
        assert _brl(metric.ticket_reais) in ticket.fact

    volume = orch.ask(_ask("Quantos litros e abastecimentos tivemos?"), user)
    assert interpret_question("Quantos litros e abastecimentos tivemos?", "OPERACIONAL").intent == QuestionIntent.VOLUME_COUNT
    assert volume.impact.status.value == "FACT"
    total_l = round(sum(item.litros for item in metrics.values()), 3)
    total_q = sum(int(item.quantidade or 0) for item in metrics.values())
    assert all(item.contagem_confiavel and item.quantidade is not None for item in metrics.values())
    assert "abastecimento" in volume.fact.casefold()
    assert "total consolidado" in volume.fact.casefold()
    assert _liters(total_l) in volume.fact
    assert _qty(total_q) in volume.fact
    for unit, metric in metrics.items():
        assert public_name(unit) in volume.fact
        assert _liters(metric.litros) in volume.fact
        assert _qty(int(metric.quantidade or 0)) in volume.fact
        assert _brl(metric.ticket_reais or 0) in volume.fact
    assert volume.evidence
    assert {item.empresa_codigo for item in volume.evidence} == set(LICENSED_SDS_CODES)
    assert all("abastecimento" in item.summary.casefold() for item in volume.evidence)

    profit = orch.ask(_ask("Podemos afirmar qual foi o lucro?", "FINANCEIRO"), user)
    assert profit.impact.status.value == "UNAVAILABLE"
    assert profit.impact.amount is None
    assert "não é lucro" in profit.fact.casefold() or "nao e lucro" in profit.fact.casefold()
    assert profit.suggested_action["engine"] == "deterministic"
    assert profit.suggested_action["llm"] is False


def test_volume_count_omits_unreliable_totals() -> None:
    day = date(2026, 8, 27)
    orch = ExecutiveCopilotOrchestrator(
        checkpoint_store=MemoryCheckpointStore(
            [
                DayCheckpoint(5555, day, STATUS_SUCESSO, 10),
                DayCheckpoint(11495, day, STATUS_SUCESSO, None),
            ]
        ),
        facts_store=MemoryFuelFactsStore(
            [
                UnitDayFacts(5555, day, STATUS_SUCESSO, litros=100.0, faturamento=500.0, quantidade=10),
                UnitDayFacts(
                    11495,
                    day,
                    STATUS_SUCESSO,
                    litros=80.0,
                    faturamento=400.0,
                    quantidade=None,
                    registros_sem_identidade=2,
                ),
            ]
        ),
    )
    answer = orch.ask(
        AskRequest.model_validate(
            {
                "pergunta": "Quantos litros e abastecimentos tivemos?",
                "especialista": "OPERACIONAL",
                "unidades": [5555, 11495],
                "periodo": {"inicio": "2026-08-27", "fim": "2026-08-27"},
            }
        ),
        _director(),
    )
    assert answer.impact.status.value == "FACT"
    assert "100" in answer.fact or "100,0" in answer.fact
    assert "não confiável" in answer.fact.casefold() or "nao confiavel" in answer.fact.casefold()
    assert "total de abastecimentos" in answer.fact.casefold()
    assert "ticket consolidado não publicados" in answer.fact.casefold() or "ticket consolidado nao publicados" in answer.fact.casefold()
    assert "10" in answer.fact
    assert answer.suggested_action["engine"] == "deterministic"
    assert answer.suggested_action["llm"] is False


def test_unauthorized_unit_is_blocked() -> None:
    answer = _local_orch().ask(_ask("Qual o faturamento?", "FINANCEIRO"), {"role": "manager", "company_id": 5555})
    # request asks all three units
    assert answer.impact.status.value == "BLOCKED"
    assert answer.blocked is not None


def test_period_gap_is_blocked() -> None:
    orch = ExecutiveCopilotOrchestrator(
        checkpoint_store=MemoryCheckpointStore(
            [
                DayCheckpoint(5555, date(2026, 8, 13), STATUS_SUCESSO, 10),
                DayCheckpoint(5555, date(2026, 8, 28), STATUS_SUCESSO, 10),
            ]
        ),
        facts_store=MemoryFuelFactsStore(
            [
                UnitDayFacts(5555, date(2026, 8, 13), STATUS_SUCESSO, 10.0, 50.0, 1),
                UnitDayFacts(5555, date(2026, 8, 28), STATUS_SUCESSO, 10.0, 50.0, 1),
            ]
        ),
    )
    answer = orch.ask(
        AskRequest.model_validate(
            {
                "pergunta": "Qual o faturamento?",
                "especialista": "FINANCEIRO",
                "unidades": [5555],
                "periodo": PERIOD,
            }
        ),
        _director(),
    )
    assert answer.impact.status.value == "BLOCKED"
    assert answer.blocked is not None
    assert answer.blocked.code == "PERIOD_BLOCKED"


def test_local_failure_is_unavailable() -> None:
    class Boom:
        def list_days(self, *_a, **_k):
            raise RuntimeError("falha local")

    orch = ExecutiveCopilotOrchestrator(checkpoint_store=Boom(), facts_store=MemoryFuelFactsStore())
    answer = orch.ask(_ask("Qual o faturamento?", "FINANCEIRO"), _director())
    assert answer.impact.status.value == "UNAVAILABLE"
    assert answer.suggested_action["engine"] == "deterministic"
    assert answer.suggested_action["llm"] is False
    assert answer.suggested_action["code"] == "LOCAL_SOURCE_FAILED"


def test_http_without_auth_is_401() -> None:
    configure_orchestrator(_local_orch())
    app = FastAPI()
    app.include_router(router)

    async def _anon():
        raise HTTPException(status_code=401, detail="Not authenticated")

    app.dependency_overrides[get_current_user] = _anon
    client = TestClient(app)
    resp = client.post(
        "/api/v1/executive-copilot/ask",
        json=_ask("Compare o faturamento entre as unidades.", "PRESIDENTE").model_dump(by_alias=True, mode="json"),
    )
    assert resp.status_code == 401
