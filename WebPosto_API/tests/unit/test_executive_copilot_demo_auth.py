"""Auth oficial no demo_app isolado. Fixtures locais; sem rede, jobs ou credenciais reais."""

from __future__ import annotations

import threading
from datetime import date

import httpx
import pytest
from fastapi.testclient import TestClient

from src.infrastructure.config.settings import settings
from src.infrastructure.security.jwt_utils import create_access_token
from src.interfaces.http.routes.executive_copilot_ask import configure_orchestrator
from src.services.executive_copilot.coverage import DayCheckpoint, MemoryCheckpointStore
from src.services.executive_copilot.demo_app import create_demo_app
from src.services.executive_copilot.metrics import MemoryFuelFactsStore, UnitDayFacts
from src.services.executive_copilot.orchestrator import ExecutiveCopilotOrchestrator
from src.services.sds_identity import STATUS_SUCESSO

DAY = "2026-08-27"
_FIXTURE_EMAIL = "qa.demo.auth@logos.test"
_FIXTURE_PASSWORD = "FixtureLocalPassword-NotUsedInProd"
_PROBE_EMAIL = "sonda-nao-configurada@exemplo.local"
_PROBE_PASSWORD = "sonda-senha-nao-configurada"
_WRONG_PASSWORD = "senha_incorreta"


@pytest.fixture(autouse=True)
def block_external_http(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("chamada externa proibida")

    monkeypatch.setattr(httpx, "Client", boom)
    monkeypatch.setattr(httpx, "AsyncClient", boom)


def _orch() -> ExecutiveCopilotOrchestrator:
    day = date(2026, 8, 27)
    return ExecutiveCopilotOrchestrator(
        checkpoint_store=MemoryCheckpointStore(
            [
                DayCheckpoint(5555, day, STATUS_SUCESSO, 10),
                DayCheckpoint(11495, day, STATUS_SUCESSO, 10),
            ]
        ),
        facts_store=MemoryFuelFactsStore(
            [
                UnitDayFacts(5555, day, STATUS_SUCESSO, litros=100.0, faturamento=500.0, quantidade=10),
                UnitDayFacts(11495, day, STATUS_SUCESSO, litros=80.0, faturamento=400.0, quantidade=10),
            ]
        ),
    )


def _ask_body(*, unidades: list[int] | None = None) -> dict:
    return {
        "pergunta": "Qual o faturamento de combustível?",
        "especialista": "FINANCEIRO",
        "unidades": unidades or [5555],
        "periodo": {"inicio": DAY, "fim": DAY},
    }


def _client() -> TestClient:
    configure_orchestrator(_orch())
    return TestClient(create_demo_app())


def _configure_fixture_auth(monkeypatch, *, role: str = "director") -> None:
    monkeypatch.setattr(settings, "auth_user_email", _FIXTURE_EMAIL)
    monkeypatch.setattr(settings, "auth_user_password", _FIXTURE_PASSWORD)
    monkeypatch.setattr(settings, "auth_user_password_hash", "")
    monkeypatch.setattr(settings, "auth_user_role", role)
    monkeypatch.setattr(settings, "auth_user_company_id", 5555)
    monkeypatch.setattr(settings, "auth_cookie_secure", False)


def _bearer(role: str, **extra) -> dict[str, str]:
    token = create_access_token(_FIXTURE_EMAIL, extra={"role": role, **extra})
    return {"Authorization": f"Bearer {token}"}


def _assert_no_secrets(response, caplog=None, *extras: str) -> None:
    blob = response.text
    forbidden = [
        _FIXTURE_PASSWORD,
        _PROBE_PASSWORD,
        _PROBE_EMAIL,
        _WRONG_PASSWORD,
        settings.secret_key,
        settings.auth_user_password_hash,
        *extras,
    ]
    for item in forbidden:
        if item:
            assert item not in blob
    lowered = blob.casefold()
    assert "pbkdf2_sha256" not in lowered
    assert "auth_user_password" not in lowered
    if caplog is not None:
        for item in forbidden:
            if item:
                assert item not in caplog.text


def test_ask_and_me_without_token_are_401() -> None:
    client = _client()
    ask = client.post("/api/v1/executive-copilot/ask", json=_ask_body())
    me = client.get("/auth/me")
    assert ask.status_code == 401
    assert me.status_code == 401
    assert ask.json()["detail"] == "Not authenticated"
    assert me.json()["detail"] == "Not authenticated"


def test_invalid_role_is_403() -> None:
    client = _client()
    resp = client.post(
        "/api/v1/executive-copilot/ask",
        json=_ask_body(),
        headers=_bearer("cashier"),
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Perfil sem permissão para esta ação"


def test_authorized_role_can_ask_and_identify() -> None:
    client = _client()
    headers = _bearer("director")
    ask = client.post("/api/v1/executive-copilot/ask", json=_ask_body(), headers=headers)
    me = client.get("/auth/me", headers=headers)
    assert ask.status_code == 200
    assert ask.json()["impact"]["status"] == "FACT"
    assert ask.json()["webpostoWrites"] == 0
    assert me.status_code == 200
    assert me.json()["sub"] == _FIXTURE_EMAIL
    assert me.json()["role"] == "director"
    assert "access_token" not in me.json()


def test_unit_scope_is_respected() -> None:
    client = _client()
    headers = _bearer("manager", company_id=5555)
    forbidden = client.post(
        "/api/v1/executive-copilot/ask",
        json=_ask_body(unidades=[11495]),
        headers=headers,
    )
    allowed = client.post(
        "/api/v1/executive-copilot/ask",
        json=_ask_body(unidades=[5555]),
        headers=headers,
    )
    assert forbidden.status_code == 200
    assert forbidden.json()["blocked"]["code"] == "UNIT_FORBIDDEN_FOR_USER"
    assert forbidden.json()["impact"]["status"] == "BLOCKED"
    assert allowed.status_code == 200
    assert allowed.json()["impact"]["status"] == "FACT"
    assert allowed.json()["units"] == [5555]


def test_invalid_login_does_not_reveal_details(monkeypatch, caplog) -> None:
    _configure_fixture_auth(monkeypatch)
    client = _client()
    resp = client.post(
        "/auth/login",
        json={"email": _FIXTURE_EMAIL, "password": _WRONG_PASSWORD},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"
    assert "access_token" not in resp.cookies
    assert _FIXTURE_EMAIL not in resp.text
    _assert_no_secrets(resp, caplog)


def test_official_login_cookie_unlocks_ask_and_me(monkeypatch, caplog) -> None:
    _configure_fixture_auth(monkeypatch)
    client = _client()
    login = client.post(
        "/auth/login",
        json={"email": _FIXTURE_EMAIL, "password": _FIXTURE_PASSWORD},
    )
    assert login.status_code == 200
    assert "access_token" in login.cookies
    _assert_no_secrets(login, caplog)
    assert login.json()["user"]["role"] == "director"
    assert _FIXTURE_PASSWORD not in login.text

    me = client.get("/auth/me")
    ask = client.post("/api/v1/executive-copilot/ask", json=_ask_body())
    assert me.status_code == 200
    assert me.json()["role"] == "director"
    assert ask.status_code == 200
    assert ask.json()["impact"]["status"] == "FACT"


def test_demo_auth_starts_no_jobs_or_network() -> None:
    before = {t.name for t in threading.enumerate()}
    _client()
    after = {t.name for t in threading.enumerate()}
    assert after == before
    from src.services.executive_copilot import demo_app as module

    assert module.DEMO_SAFETY["scheduler"] is False
    assert module.DEMO_SAFETY["jobs"] is False
    assert module.DEMO_SAFETY["authBypass"] is False
    assert module.DEMO_SAFETY["webposto"] is False
