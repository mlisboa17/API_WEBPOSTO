"""Frente B — orquestração e POST /ask. Sem rede e sem servidor real."""

from __future__ import annotations

from datetime import date

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.interfaces.http.dependencies import get_current_user
from src.interfaces.http.routes.executive_copilot_ask import (
    configure_orchestrator,
    router,
)
from src.services.executive_copilot.coverage import DayCheckpoint, MemoryCheckpointStore
from src.services.executive_copilot.http_models import AskRequest
from src.services.executive_copilot.intent import QuestionIntent, interpret_question, is_comparative
from src.services.executive_copilot.metrics import MemoryFuelFactsStore, UnitDayFacts
from src.services.executive_copilot.orchestrator import (
    COMPARISON_BLOCKED_MESSAGE,
    COMPARISON_REQUIRES_MULTIPLE_UNITS,
    ExecutiveCopilotOrchestrator,
)
from src.services.sds_identity import LICENSED_SDS_CODES, STATUS_SEM_MOVIMENTO, STATUS_SUCESSO

DAY = date(2026, 8, 27)
PERIOD = {"inicio": "2026-08-27", "fim": "2026-08-27"}


@pytest.fixture(autouse=True)
def block_external_http(monkeypatch):
    def boom(*_args, **_kwargs):
        raise AssertionError("chamada externa proibida")

    monkeypatch.setattr(httpx, "Client", boom)
    monkeypatch.setattr(httpx, "AsyncClient", boom)


def _checks(*units: int, day: date = DAY, status: str = STATUS_SUCESSO) -> list[DayCheckpoint]:
    return [
        DayCheckpoint(empresa_codigo=unit, data_referencia=day, status=status, quantidade_abastecimentos=10)
        for unit in units
    ]


def _facts(*units: int, day: date = DAY, litros: float = 100.0, fat: float = 500.0, qty: int | None = 10) -> list[UnitDayFacts]:
    return [
        UnitDayFacts(
            empresa_codigo=unit,
            data_referencia=day,
            status=STATUS_SUCESSO,
            litros=litros * (1 if unit == 5555 else 0.5),
            faturamento=fat * (1 if unit == 5555 else 0.5),
            quantidade=qty,
        )
        for unit in units
    ]


def _orch(units=(5555,), day: date = DAY) -> ExecutiveCopilotOrchestrator:
    return ExecutiveCopilotOrchestrator(
        checkpoint_store=MemoryCheckpointStore(_checks(*units, day=day)),
        facts_store=MemoryFuelFactsStore(_facts(*units, day=day)),
    )


def _ask(**overrides) -> AskRequest:
    payload = {
        "pergunta": "Qual o faturamento de combustível?",
        "especialista": "FINANCEIRO",
        "unidades": [5555],
        "periodo": PERIOD,
    }
    payload.update(overrides)
    return AskRequest.model_validate(payload)


def _director() -> dict:
    return {"role": "director", "email": "qa@logos.test", "sub": "qa@logos.test"}


def test_specialist_routing() -> None:
    assert interpret_question("resumo", "OPERACIONAL").intent == QuestionIntent.LITERS
    assert interpret_question("resumo", "FINANCEIRO").intent == QuestionIntent.SALES
    assert interpret_question("compare as unidades", "PRESIDENTE").intent == QuestionIntent.COMPARE
    compared = interpret_question("Compare o faturamento entre as unidades", "PRESIDENTE")
    assert compared.intent == QuestionIntent.SALES
    assert compared.compare is True
    assert is_comparative(compared) is True
    single = interpret_question("Qual o faturamento de combustível?", "FINANCEIRO")
    assert single.compare is False
    assert is_comparative(single) is False
    assert interpret_question("qual o lucro?", "FINANCEIRO").intent == QuestionIntent.PROFIT
    assert interpret_question("Quantos litros e abastecimentos tivemos?", "OPERACIONAL").intent == QuestionIntent.VOLUME_COUNT


def test_unsupported_question_is_not_invented() -> None:
    answer = _orch().ask(_ask(pergunta="Qual o clima amanhã?"), _director())
    assert answer.impact.status.value == "UNAVAILABLE"
    assert "não suport" in answer.fact.casefold()
    assert answer.suggested_action["llm"] is False


def test_sales_fact_for_covered_day() -> None:
    answer = _orch().ask(_ask(), _director())
    assert answer.impact.status.value == "FACT"
    assert answer.impact.amount == 500.0
    assert "não é lucro" in answer.fact.casefold() or "nao e lucro" in answer.fact.casefold()
    assert answer.units == [5555]
    assert answer.evidence[0].empresa_codigo == 5555
    assert answer.lineage[0].source_nature.value == "CHECKPOINT"
    assert answer.webposto_writes == 0
    assert answer.to_public_payload()["webpostoWrites"] == 0


def test_compare_units_uses_coherent_evidence() -> None:
    orch = _orch(units=(5555, 11495, 74014))
    answer = orch.ask(
        _ask(
            pergunta="Compare o faturamento entre as unidades",
            especialista="PRESIDENTE",
            unidades=[5555, 11495, 74014],
        ),
        _director(),
    )
    assert answer.impact.status.value == "FACT"
    assert set(answer.units) == set(LICENSED_SDS_CODES)
    assert {item.empresa_codigo for item in answer.evidence} == set(LICENSED_SDS_CODES)
    assert "economia comprovada" in answer.inference.casefold()


def _assert_comparison_blocked(answer, current_units: list[int]) -> None:
    assert answer.impact.status.value == "BLOCKED"
    assert answer.blocked is not None
    assert answer.blocked.code == COMPARISON_REQUIRES_MULTIPLE_UNITS
    assert answer.blocked.message == COMPARISON_BLOCKED_MESSAGE
    assert answer.answer == COMPARISON_BLOCKED_MESSAGE
    assert answer.units == current_units
    action = answer.suggested_action or {}
    assert action["requiredMinimumUnits"] == 2
    assert action["currentUnits"] == current_units
    assert action["webpostoWrites"] == 0
    assert action["code"] == COMPARISON_REQUIRES_MULTIPLE_UNITS
    assert action["llm"] is False


def test_comparison_with_one_unit_is_blocked() -> None:
    orch = _orch(units=(5555, 11495, 74014))
    answer = orch.ask(
        _ask(
            pergunta="Compare o faturamento entre as unidades",
            especialista="PRESIDENTE",
            unidades=[5555],
        ),
        _director(),
    )
    _assert_comparison_blocked(answer, [5555])
    assert set(answer.units) != set(LICENSED_SDS_CODES)


def test_comparison_with_zero_explicit_units_does_not_expand_scope() -> None:
    orch = _orch(units=(5555, 11495, 74014))
    for unidades in (None, []):
        answer = orch.ask(
            _ask(
                pergunta="Compare o faturamento entre as unidades",
                especialista="PRESIDENTE",
                unidades=unidades,
            ),
            _director(),
        )
        _assert_comparison_blocked(answer, [])
        assert set(answer.units) != set(LICENSED_SDS_CODES)


def test_comparison_with_two_units_is_fact() -> None:
    orch = _orch(units=(5555, 11495))
    answer = orch.ask(
        _ask(
            pergunta="Compare o faturamento entre as unidades",
            especialista="PRESIDENTE",
            unidades=[5555, 11495],
        ),
        _director(),
    )
    assert answer.impact.status.value == "FACT"
    assert set(answer.units) == {5555, 11495}
    assert answer.blocked is None


def test_comparison_consolidated_authorized_is_fact() -> None:
    orch = _orch(units=(5555, 11495, 74014))
    answer = orch.ask(
        _ask(
            pergunta="Compare o faturamento entre as unidades",
            especialista="PRESIDENTE",
            unidades=list(LICENSED_SDS_CODES),
        ),
        _director(),
    )
    assert answer.impact.status.value == "FACT"
    assert set(answer.units) == set(LICENSED_SDS_CODES)


def test_manager_comparison_with_one_unit_does_not_expand() -> None:
    orch = _orch(units=(5555, 11495, 74014))
    user = {"role": "manager", "company_id": 5555}
    answer = orch.ask(
        _ask(
            pergunta="Compare o faturamento entre as unidades",
            especialista="PRESIDENTE",
            unidades=[5555],
        ),
        user,
    )
    _assert_comparison_blocked(answer, [5555])
    assert 11495 not in answer.units
    assert 74014 not in answer.units

    empty = orch.ask(
        _ask(
            pergunta="Compare o faturamento entre as unidades",
            especialista="PRESIDENTE",
            unidades=None,
        ),
        user,
    )
    _assert_comparison_blocked(empty, [])
    assert set(empty.units) != set(LICENSED_SDS_CODES)


def test_non_comparative_single_unit_remains_fact() -> None:
    answer = _orch().ask(_ask(), _director())
    assert answer.impact.status.value == "FACT"
    assert answer.units == [5555]
    assert answer.impact.amount == 500.0


def test_non_comparative_ticket_liters_and_draft_unchanged() -> None:
    orch = _orch()
    user = _director()
    ticket = orch.ask(_ask(pergunta="Qual o ticket médio?", especialista="OPERACIONAL"), user)
    assert ticket.impact.status.value == "FACT"
    assert ticket.units == [5555]
    liters = orch.ask(_ask(pergunta="Quantos litros?", especialista="OPERACIONAL"), user)
    assert liters.impact.status.value == "FACT"
    assert liters.units == [5555]
    draft = orch.ask(
        _ask(pergunta="Cadastre o produto Água Mineral 500 ml", especialista="OPERACIONAL"),
        user,
    )
    action = draft.suggested_action or {}
    assert action["status"] == "DRAFT"
    assert action["webpostoWrites"] == 0
    assert draft.blocked is None or draft.blocked.code != COMPARISON_REQUIRES_MULTIPLE_UNITS


def test_period_gap_is_blocked_even_if_max_date_is_complete() -> None:
    start = date(2026, 8, 26)
    end = date(2026, 8, 28)
    rows = [
        *_checks(5555, day=start),
        *_checks(5555, day=end),
    ]
    facts = [
        *_facts(5555, day=start),
        *_facts(5555, day=end),
    ]
    orch = ExecutiveCopilotOrchestrator(
        checkpoint_store=MemoryCheckpointStore(rows),
        facts_store=MemoryFuelFactsStore(facts),
    )
    answer = orch.ask(
        _ask(periodo={"inicio": start.isoformat(), "fim": end.isoformat()}),
        _director(),
    )
    assert answer.impact.status.value == "BLOCKED"
    assert answer.blocked is not None
    assert answer.blocked.code == "PERIOD_BLOCKED"


def test_invalid_period_rejected() -> None:
    with pytest.raises(ValidationError):
        _ask(periodo={"inicio": "2026-08-28", "fim": "2026-08-27"})
    with pytest.raises(ValidationError):
        _ask(periodo={"inicio": "nao-e-data", "fim": "2026-08-27"})


def test_forbidden_units_blocked() -> None:
    for code in (5333, 15880):
        answer = _orch().ask(_ask(unidades=[code]), _director())
        assert answer.impact.status.value == "BLOCKED"
        assert answer.units == []
    fuel = _orch().ask(_ask(unidades=[118508]), _director())
    assert fuel.impact.status.value == "BLOCKED"
    assert fuel.blocked is not None
    assert fuel.blocked.code == "UNIT_SOURCE_NOT_APPLICABLE"
    assert fuel.impact.amount is None


def test_6666_normalized_before_contract() -> None:
    orch = _orch(units=(11495,))
    answer = orch.ask(_ask(unidades=[6666], pergunta="Quantos litros?"), _director())
    assert 6666 not in answer.units
    assert answer.units == [11495]


def test_user_cannot_read_unauthorized_unit() -> None:
    user = {"role": "manager", "company_id": 5555}
    answer = _orch(units=(5555, 11495)).ask(_ask(unidades=[11495]), user)
    assert answer.impact.status.value == "BLOCKED"
    assert answer.blocked is not None
    assert answer.blocked.code == "UNIT_FORBIDDEN_FOR_USER"


def test_profit_without_cmv_is_unavailable() -> None:
    answer = _orch().ask(_ask(pergunta="Qual o lucro líquido?"), _director())
    assert answer.impact.status.value == "UNAVAILABLE"
    assert answer.impact.amount is None
    assert "faturamento não é lucro" in answer.fact.casefold() or "faturamento nao e lucro" in answer.fact.casefold()


def test_unreliable_count_nulls_ticket() -> None:
    facts = [
        UnitDayFacts(
            empresa_codigo=5555,
            data_referencia=DAY,
            status=STATUS_SUCESSO,
            litros=100.0,
            faturamento=500.0,
            quantidade=None,
            rows=(
                {"quantidade": 10, "valorTotal": 50, "codigoProduto": "1"},
            ),
        )
    ]
    orch = ExecutiveCopilotOrchestrator(
        checkpoint_store=MemoryCheckpointStore(_checks(5555)),
        facts_store=MemoryFuelFactsStore(facts),
    )
    answer = orch.ask(_ask(pergunta="Qual o ticket médio?", especialista="OPERACIONAL"), _director())
    assert answer.impact.amount is None
    assert answer.impact.status.value == "UNAVAILABLE"


def test_reliable_ticket_is_fact() -> None:
    rows = (
        {
            "abastecimentoCodigo": "A1",
            "codigo": "A1",
            "quantidade": 10,
            "valorTotal": 50,
            "codigoProduto": "1",
        },
        {
            "abastecimentoCodigo": "A1",
            "codigo": "A1",
            "quantidade": 10,
            "valorTotal": 50,
            "codigoProduto": "1",
        },
    )
    facts = [
        UnitDayFacts(
            empresa_codigo=5555,
            data_referencia=DAY,
            status=STATUS_SUCESSO,
            litros=10.0,
            faturamento=50.0,
            quantidade=1,
            rows=rows,
        )
    ]
    orch = ExecutiveCopilotOrchestrator(
        checkpoint_store=MemoryCheckpointStore(_checks(5555)),
        facts_store=MemoryFuelFactsStore(facts),
    )
    answer = orch.ask(_ask(pergunta="Qual o ticket médio?", especialista="OPERACIONAL"), _director())
    assert answer.impact.status.value == "FACT"
    assert answer.impact.amount == 50.0


def test_local_source_failure() -> None:
    class Boom:
        def list_facts(self, *_a, **_k):
            raise RuntimeError("C:\\secret\\db.sqlite token=abc")

    orch = ExecutiveCopilotOrchestrator(
        checkpoint_store=MemoryCheckpointStore(_checks(5555)),
        facts_store=Boom(),
    )
    answer = orch.ask(_ask(), _director())
    blob = str(answer.to_public_payload())
    assert answer.impact.status.value == "UNAVAILABLE"
    assert "token=abc" not in blob
    assert "C:\\secret" not in blob


def test_sem_movimento_is_zero_fact() -> None:
    orch = ExecutiveCopilotOrchestrator(
        checkpoint_store=MemoryCheckpointStore(_checks(5555, status=STATUS_SEM_MOVIMENTO)),
        facts_store=MemoryFuelFactsStore(
            [
                UnitDayFacts(
                    empresa_codigo=5555,
                    data_referencia=DAY,
                    status=STATUS_SEM_MOVIMENTO,
                    litros=0.0,
                    faturamento=0.0,
                    quantidade=0,
                )
            ]
        ),
    )
    answer = orch.ask(_ask(pergunta="Quantos litros?", especialista="OPERACIONAL"), _director())
    assert answer.impact.status.value == "FACT"


def _client(orch: ExecutiveCopilotOrchestrator, user: dict | None) -> TestClient:
    configure_orchestrator(orch)
    app = FastAPI()
    app.include_router(router)

    async def _user():
        if user is None:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return user

    app.dependency_overrides[get_current_user] = _user
    return TestClient(app)


def test_http_requires_auth() -> None:
    client = _client(_orch(), None)
    resp = client.post("/api/v1/executive-copilot/ask", json=_ask().model_dump(by_alias=True, mode="json"))
    assert resp.status_code == 401


def test_http_forbids_wrong_role() -> None:
    client = _client(_orch(), {"role": "cashier"})
    resp = client.post("/api/v1/executive-copilot/ask", json=_ask().model_dump(by_alias=True, mode="json"))
    assert resp.status_code == 403


def test_http_ask_returns_copilot_contract() -> None:
    client = _client(_orch(), _director())
    resp = client.post("/api/v1/executive-copilot/ask", json=_ask().model_dump(by_alias=True, mode="json"))
    assert resp.status_code == 200
    body = resp.json()
    assert body["specialist"] == "FINANCEIRO"
    assert body["impact"]["status"] == "FACT"
    assert body["webpostoWrites"] == 0
    assert body["suggestedAction"]["llm"] is False
    assert body["suggestedAction"]["engine"] == "deterministic"
    assert "C:\\" not in resp.text


def test_http_rejects_extra_fields() -> None:
    client = _client(_orch(), _director())
    payload = _ask().model_dump(by_alias=True, mode="json")
    payload["campoInesperado"] = True
    resp = client.post("/api/v1/executive-copilot/ask", json=payload)
    assert resp.status_code == 422


def test_no_writes_constant() -> None:
    from src.services.executive_copilot.contracts import WEBPOSTO_WRITES

    assert WEBPOSTO_WRITES == 0


def test_director_invalid_units_do_not_expand_to_network() -> None:
    from src.services.executive_copilot.access import user_accessible_units

    invalid = user_accessible_units({"role": "director", "units": ["invalid"]})
    assert invalid.blocked is not None
    assert invalid.blocked["code"] == "UNIT_SCOPE_INVALID"
    assert invalid.units == []
    empty = user_accessible_units({"role": "director", "units": []})
    assert empty.blocked is not None
    assert empty.units == []
    answer = _orch(units=(5555, 11495, 74014)).ask(_ask(), {"role": "director", "units": ["invalid"]})
    assert answer.impact.status.value == "BLOCKED"
    assert set(answer.units) != set(LICENSED_SDS_CODES)
    assert answer.units == []


def test_checkpoint_read_failure_is_unavailable() -> None:
    class BoomCheckpoints:
        def list_days(self, *_a, **_k):
            raise RuntimeError("C:\\secret\\sds.db token=super-secret")

    orch = ExecutiveCopilotOrchestrator(
        checkpoint_store=BoomCheckpoints(),
        facts_store=MemoryFuelFactsStore(_facts(5555)),
    )
    answer = orch.ask(_ask(), _director())
    payload = answer.to_public_payload()
    assert answer.impact.status.value == "UNAVAILABLE"
    assert payload["suggestedAction"]["code"] == "LOCAL_SOURCE_FAILED"
    blob = str(payload)
    assert "super-secret" not in blob
    assert "C:\\secret" not in blob


def test_compare_uses_asked_metric_and_handles_tie() -> None:
    facts = [
        UnitDayFacts(5555, DAY, STATUS_SUCESSO, litros=200.0, faturamento=100.0, quantidade=20),
        UnitDayFacts(11495, DAY, STATUS_SUCESSO, litros=80.0, faturamento=400.0, quantidade=20),
    ]
    orch = ExecutiveCopilotOrchestrator(
        checkpoint_store=MemoryCheckpointStore(_checks(5555, 11495)),
        facts_store=MemoryFuelFactsStore(facts),
    )
    liters = orch.ask(
        _ask(pergunta="Compare os litros entre as unidades", especialista="OPERACIONAL", unidades=[5555, 11495]),
        _director(),
    )
    assert "em litros" in liters.inference
    assert "AP Casa Caiada" in liters.inference and "Posto VIP" in liters.inference
    assert "400" not in liters.inference
    ticket = orch.ask(
        _ask(pergunta="Compare o ticket entre as unidades", especialista="OPERACIONAL", unidades=[5555, 11495]),
        _director(),
    )
    assert ticket.impact.status.value == "FACT"
    assert "em ticket" in ticket.inference
    qty = orch.ask(
        _ask(
            pergunta="Compare os abastecimentos entre as unidades",
            especialista="OPERACIONAL",
            unidades=[5555, 11495],
        ),
        _director(),
    )
    assert "empate" in qty.inference.casefold()
    assert "abastecimentos" in qty.inference.casefold()


def test_compare_unavailable_when_ticket_missing() -> None:
    facts = [
        UnitDayFacts(5555, DAY, STATUS_SUCESSO, litros=100.0, faturamento=500.0, quantidade=10),
        UnitDayFacts(
            11495,
            DAY,
            STATUS_SUCESSO,
            litros=80.0,
            faturamento=400.0,
            quantidade=None,
            registros_sem_identidade=3,
        ),
    ]
    orch = ExecutiveCopilotOrchestrator(
        checkpoint_store=MemoryCheckpointStore(_checks(5555, 11495)),
        facts_store=MemoryFuelFactsStore(facts),
    )
    answer = orch.ask(
        _ask(pergunta="Compare o ticket entre as unidades", especialista="OPERACIONAL", unidades=[5555, 11495]),
        _director(),
    )
    assert "indisponível" in answer.inference.casefold() or "indisponivel" in answer.inference.casefold()
    assert "Posto VIP" in answer.inference
