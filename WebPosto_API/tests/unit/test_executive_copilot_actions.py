"""Camada segura de intenção e proposta. Sem rede e sem escrita."""

from __future__ import annotations

from datetime import date

import httpx
import pytest

from src.services.executive_copilot.action_proposals import ACTION_EXECUTION_NOT_ENABLED
from src.services.executive_copilot.contracts import WEBPOSTO_WRITES
from src.services.executive_copilot.coverage import DayCheckpoint, MemoryCheckpointStore
from src.services.executive_copilot.http_models import AskRequest
from src.services.executive_copilot.intent import ActionIntent, QuestionIntent, interpret_question
from src.services.executive_copilot.metrics import MemoryFuelFactsStore, UnitDayFacts
from src.services.executive_copilot.orchestrator import ExecutiveCopilotOrchestrator
from src.services.sds_identity import STATUS_SUCESSO

DAY = date(2026, 8, 27)
PERIOD = {"inicio": "2026-08-27", "fim": "2026-08-27"}


@pytest.fixture(autouse=True)
def block_external_http(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("chamada externa proibida")

    monkeypatch.setattr(httpx, "Client", boom)
    monkeypatch.setattr(httpx, "AsyncClient", boom)


def _orch() -> ExecutiveCopilotOrchestrator:
    return ExecutiveCopilotOrchestrator(
        checkpoint_store=MemoryCheckpointStore(
            [DayCheckpoint(5555, DAY, STATUS_SUCESSO, 10)]
        ),
        facts_store=MemoryFuelFactsStore(
            [UnitDayFacts(5555, DAY, STATUS_SUCESSO, 100.0, 500.0, 10)]
        ),
    )


def _ask(pergunta: str, unidades=None) -> AskRequest:
    return AskRequest.model_validate(
        {
            "pergunta": pergunta,
            "especialista": "OPERACIONAL",
            "unidades": unidades if unidades is not None else [5555],
            "periodo": PERIOD,
        }
    )


def _director() -> dict:
    return {"role": "director"}


def test_action_intents_are_recognized() -> None:
    assert interpret_question("Cadastre o produto Água Mineral 500 ml", "OPERACIONAL").intent == (
        QuestionIntent.CREATE_PRODUCT_DRAFT
    )
    assert interpret_question("Cadastre o produto Água Mineral 500 ml", "OPERACIONAL").action == (
        ActionIntent.CREATE_PRODUCT_DRAFT
    )
    assert interpret_question("Lance uma despesa de R$ 120 de gelo na unidade 5555", "FINANCEIRO").intent == (
        QuestionIntent.CREATE_EXPENSE_DRAFT
    )
    assert interpret_question("Reclassifique o lançamento ABC para plano 3.1", "FINANCEIRO").intent == (
        QuestionIntent.RECLASSIFY_EXPENSE_DRAFT
    )
    assert interpret_question("Crie uma tarefa de auditoria na unidade 5555", "PRESIDENTE").intent == (
        QuestionIntent.CREATE_AUDIT_TASK
    )
    query = interpret_question("Compare o faturamento entre as unidades", "PRESIDENTE")
    assert query.action == ActionIntent.EXECUTIVE_QUERY
    assert query.intent == QuestionIntent.SALES
    assert interpret_question("Quais despesas cresceram sem justificativa?", "FINANCEIRO").intent == (
        QuestionIntent.EXPENSE
    )


def test_product_draft_preview_asks_missing_fields() -> None:
    answer = _orch().ask(_ask("Cadastre o produto Água Mineral 500 ml"), _director())
    action = answer.suggested_action or {}
    assert action["actionType"] == "CREATE_PRODUCT_DRAFT"
    assert action["status"] == "DRAFT"
    assert action["requiresConfirmation"] is True
    assert action["requiresApproval"] is True
    assert action["webpostoWrites"] == 0 == WEBPOSTO_WRITES
    assert action["camposPreenchidos"]["descricaoPadronizada"] == "Água Mineral 500 ml"
    assert "ean" in action["camposObrigatoriosAusentes"]
    assert answer.impact.status.value == "UNAVAILABLE"
    assert "Informe" in answer.fact


def test_expense_draft_preview_does_not_write() -> None:
    answer = _orch().ask(
        _ask("Lance uma despesa de R$ 120 de gelo na unidade 5555"),
        _director(),
    )
    action = answer.suggested_action or {}
    assert action["actionType"] == "CREATE_EXPENSE_DRAFT"
    assert action["status"] == "DRAFT"
    assert action["unidade"] == 5555
    assert action["unitPublicName"] == "AP Casa Caiada"
    assert action["camposPreenchidos"]["valor"] == 120.0
    assert action["camposPreenchidos"]["descricao"] == "gelo"
    assert "empresaCodigo" not in action["camposPreenchidos"]
    assert "empresaCodigo" not in (action.get("filledFields") or {})
    assert action["persisted"] is False
    assert action["autoClassifiedFields"][0]["status"] == "AUTO_CLASSIFIED"
    assert action["camposObrigatoriosAusentes"] == []
    assert action["webpostoWrites"] == 0
    assert action["engine"] == "deterministic"
    assert action["llm"] is False
    assert "nenhuma escrita" in answer.fact.casefold() or "DRAFT" in answer.fact


def test_unauthorized_unit_in_action_is_blocked() -> None:
    answer = _orch().ask(
        _ask("Lance uma despesa de R$ 120 de gelo na unidade 5333", unidades=[5555]),
        _director(),
    )
    assert answer.impact.status.value == "BLOCKED"
    assert answer.blocked is not None


def test_invalid_expense_amount_is_not_invented() -> None:
    answer = _orch().ask(
        _ask("Lance uma despesa de R$ -120 de gelo na unidade 5555"),
        _director(),
    )
    action = answer.suggested_action or {}
    assert "valor" in action["camposObrigatoriosAusentes"]
    assert "valor" not in action["camposPreenchidos"]
    assert action["camposPreenchidos"].get("valorInvalido") is True


def test_duplicate_preview_is_flagged() -> None:
    orch = _orch()
    first = orch.ask(_ask("Cadastre o produto Água Mineral 500 ml"), _director())
    second = orch.ask(_ask("Cadastre o produto Água Mineral 500 ml"), _director())
    assert first.suggested_action["duplicate"] is False
    assert second.suggested_action["duplicate"] is True
    assert "duplicidade" in second.suggested_action["risco"].casefold()


def test_confirm_does_not_execute() -> None:
    answer = _orch().ask(_ask("confirme o cadastro do produto"), _director())
    action = answer.suggested_action or {}
    assert action["actionType"] == "CONFIRM_ACTION"
    assert action["executionCode"] == ACTION_EXECUTION_NOT_ENABLED
    assert action["webpostoWrites"] == 0
    assert ACTION_EXECUTION_NOT_ENABLED in answer.fact
    assert answer.impact.status.value == "UNAVAILABLE"


def test_action_layer_has_zero_external_calls_and_writes() -> None:
    orch = _orch()
    orch.ask(_ask("Cadastre o produto Água Mineral 500 ml"), _director())
    orch.ask(_ask("Lance uma despesa de R$ 120 de gelo na unidade 5555"), _director())
    orch.ask(_ask("confirme"), _director())
    assert WEBPOSTO_WRITES == 0
