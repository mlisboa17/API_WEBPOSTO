"""Narrativa LLM injetável e entrypoint isolado. Sem rede."""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from src.services.executive_copilot.coverage import DayCheckpoint, MemoryCheckpointStore
from src.services.executive_copilot.demo_app import (
    DEMO_BIND,
    DEMO_PORT,
    create_demo_app,
    demo_cli_error,
    demo_safety_report,
)
from src.services.executive_copilot.http_models import AskRequest
from src.services.executive_copilot.intent import interpret_question
from src.services.executive_copilot.llm_port import DeterministicNarrator, InjectableLlmNarrator, narrative_payload
from src.services.executive_copilot.metrics import MemoryFuelFactsStore, UnitDayFacts
from src.services.executive_copilot.orchestrator import ExecutiveCopilotOrchestrator
from src.services.sds_identity import STATUS_SUCESSO

DAY = "2026-08-27"


@pytest.fixture(autouse=True)
def block_external_http(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("chamada externa proibida")

    monkeypatch.setattr(httpx, "Client", boom)
    monkeypatch.setattr(httpx, "AsyncClient", boom)


def _orch(narrator) -> ExecutiveCopilotOrchestrator:
    return ExecutiveCopilotOrchestrator(
        checkpoint_store=MemoryCheckpointStore(
            [DayCheckpoint(5555, __import__("datetime").date(2026, 8, 27), STATUS_SUCESSO, 10)]
        ),
        facts_store=MemoryFuelFactsStore(
            [
                UnitDayFacts(
                    5555,
                    __import__("datetime").date(2026, 8, 27),
                    STATUS_SUCESSO,
                    litros=100.0,
                    faturamento=500.0,
                    quantidade=10,
                )
            ]
        ),
        narrator=narrator,
    )


def _ask() -> AskRequest:
    return AskRequest.model_validate(
        {
            "pergunta": "Qual o faturamento de combustível?",
            "especialista": "FINANCEIRO",
            "unidades": [5555],
            "periodo": {"inicio": DAY, "fim": DAY},
        }
    )


def test_llm_rewrites_answer_but_keeps_deterministic_fact() -> None:
    def fake_complete(payload: dict) -> str:
        assert payload["series"][0]["faturamento"] == 500.0
        assert "token" not in str(payload).casefold()
        return "Narrativa mockada sem inventar lucro."

    narrator = InjectableLlmNarrator(complete=fake_complete, enabled=True)
    answer = _orch(narrator).ask(_ask(), {"role": "director"})
    assert answer.impact.status.value == "FACT"
    assert answer.impact.amount == 500.0
    assert "500" in answer.fact or "500,00" in answer.fact or "500.0" in answer.fact
    assert answer.answer == "Narrativa mockada sem inventar lucro."
    assert answer.suggested_action["llm"] is True
    assert answer.webposto_writes == 0


def test_llm_error_falls_back_to_deterministic() -> None:
    def boom(_payload: dict) -> str:
        raise RuntimeError("provider down")

    narrator = InjectableLlmNarrator(complete=boom, enabled=True)
    answer = _orch(narrator).ask(_ask(), {"role": "director"})
    assert answer.suggested_action["engine"] == "deterministic"
    assert answer.suggested_action["llm"] is False
    assert answer.impact.amount == 500.0
    assert "não é lucro" in answer.fact.casefold() or "nao e lucro" in answer.fact.casefold()


def test_disabled_llm_does_not_call_complete() -> None:
    called = {"n": 0}

    def fake_complete(_payload: dict) -> str:
        called["n"] += 1
        return "nao deveria"

    narrator = InjectableLlmNarrator(complete=fake_complete, enabled=False)
    answer = _orch(narrator).ask(_ask(), {"role": "director"})
    assert called["n"] == 0
    assert answer.suggested_action["llm"] is False


def test_narrative_payload_is_aggregates_only() -> None:
    interpreted = interpret_question("Qual o faturamento?", "FINANCEIRO")
    payload = narrative_payload(interpreted, None, start=DAY, end=DAY)
    assert payload["series"] == []
    assert "regra" in payload


def test_demo_entrypoint_safety_and_auth() -> None:
    report = demo_safety_report()
    assert report["bind"] == DEMO_BIND == "127.0.0.1"
    assert report["defaultPort"] == DEMO_PORT != 8040
    assert report["scheduler"] is False
    assert report["migrations"] is False
    assert report["webposto"] is False
    assert report["authBypass"] is False
    assert report["officialAuth"] is True
    assert report["jobs"] is False
    assert report["dataOnDemandFake"] is True
    assert report["executorMode"] == "FAKE_LOCAL"
    assert report["webpostoWrites"] == 0
    client = TestClient(create_demo_app())
    resp = client.post(
        "/api/v1/executive-copilot/ask",
        json={
            "pergunta": "Qual o faturamento?",
            "especialista": "FINANCEIRO",
            "unidades": [5555],
            "periodo": {"inicio": DAY, "fim": DAY},
        },
    )
    assert resp.status_code == 401
    assert demo_cli_error(bind=False, host="127.0.0.1", port=8095)
    assert demo_cli_error(bind=True, host="0.0.0.0", port=8095)
    assert demo_cli_error(bind=True, host="127.0.0.1", port=8040)
    assert demo_cli_error(bind=True, host="127.0.0.1", port=8095) is None
    import ast
    from pathlib import Path

    tree = ast.parse(Path("src/services/executive_copilot/demo_app.py").read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    joined = " ".join(imported)
    assert "src.jobs" not in joined
    assert "sds_catchup" not in joined
    assert "sds_canary" not in joined
    assert "webposto_client" not in joined
    assert "alembic" not in joined


def test_deterministic_narrator_still_default() -> None:
    answer = _orch(DeterministicNarrator()).ask(_ask(), {"role": "director"})
    assert answer.suggested_action["engine"] == "deterministic"
    assert answer.suggested_action["llm"] is False
