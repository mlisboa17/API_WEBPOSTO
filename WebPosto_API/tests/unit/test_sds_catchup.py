import asyncio
import logging
from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.interfaces.http.dependencies import get_current_user
from src.services.sds_catchup_service import InMemoryDayStatusStore, SdsCatchupService
from src.services.sds_identity import (
    LICENSED_SDS_CODES,
    STATUS_FALHA,
    STATUS_SEM_MOVIMENTO,
    STATUS_SUCESSO,
    abastecimento_identity,
    summarize_abastecimentos,
)
from src.services.sds_sanitize import sanitize_value
from src.services.webposto.schemas import WEBPOSTO_WRITES
from src.services.webposto.write_policy import is_webposto_write_path


def test_nao_usa_venda_item_codigo():
    rows = [
        {"vendaItemCodigo": 1, "quantidade": 10, "valorTotal": 70, "codigoProduto": "100"},
        {"vendaItemCodigo": 2, "quantidade": 10, "valorTotal": 70, "codigoProduto": "100"},
        {"abastecimentoCodigo": 9, "quantidade": 20, "valorTotal": 140, "codigoProduto": "100"},
    ]
    assert abastecimento_identity(rows[0]) is None
    agg = summarize_abastecimentos(rows)
    assert agg["quantidadeAbastecimentos"] == 1
    assert agg["registrosSemIdentidade"] == 2
    assert agg["status"] == "PARCIAL"
    assert agg["ticketMedioLitros"] is None
    assert agg["ticketMedioReais"] is None
    assert agg["litrosVendidos"] == 40


def test_codigo_como_identidade_do_abastecimento():
    rows = [
        {"codigo": 88, "quantidade": 15, "valorTotal": 90, "codigoProduto": "200"},
        {"codigo": 88, "quantidade": 15, "valorTotal": 90, "codigoProduto": "200"},
    ]
    agg = summarize_abastecimentos(rows)
    assert agg["quantidadeAbastecimentos"] == 1
    assert agg["contagemConfiavel"] is True
    assert agg["ticketMedioLitros"] == 15


def test_sem_identidade_nao_conta():
    rows = [{"codigoProduto": "1", "quantidade": 8, "valorTotal": 40}]
    agg = summarize_abastecimentos(rows)
    assert agg["quantidadeAbastecimentos"] is None
    assert agg["registrosSemIdentidade"] == 1
    assert agg["ticketMedioLitros"] is None


@pytest.mark.asyncio
async def test_descoberta_lacunas_tres_unidades_sem_6666():
    store = InMemoryDayStatusStore()
    svc = SdsCatchupService(
        store=store,
        last_sds_date=lambda _c: _coro(date(2026, 8, 12)),
        today_fn=lambda: date(2026, 8, 16),
        sync_day=_ok_sync,
    )
    assert svc.resolve_units([6666]) == [11495]
    gaps = await svc.discover_gaps()
    codes = {emp for emp, _d in gaps}
    assert codes == set(LICENSED_SDS_CODES)
    assert 6666 not in codes
    assert 118508 not in codes
    assert all(dia >= date(2026, 8, 13) for _e, dia in gaps)


@pytest.mark.asyncio
async def test_upsert_idempotente_e_retomada():
    calls: list[tuple[int, date]] = []

    async def sync(emp, dia, force=False):
        calls.append((emp, dia))
        return {"status": STATUS_SUCESSO, "quantidadeAbastecimentos": 1, "registrosSemIdentidade": 0}

    store = InMemoryDayStatusStore()
    svc = SdsCatchupService(
        store=store,
        sync_day=sync,
        last_sds_date=lambda _c: _coro(date(2026, 8, 12)),
        today_fn=lambda: date(2026, 8, 15),
        max_days=10,
    )
    first = await svc.run(inicio=date(2026, 8, 13), fim=date(2026, 8, 13), empresas=[5555])
    assert first["contadores"][STATUS_SUCESSO] == 1
    second = await svc.run(inicio=date(2026, 8, 13), fim=date(2026, 8, 13), empresas=[5555])
    assert second["paresUnidadeDia"] == 0
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_fail_fast_global_interrompe_onda():
    seen: list[int] = []

    async def sync(emp, dia, force=False):
        seen.append(emp)
        if emp == 11495:
            raise RuntimeError("GET ABASTECIMENTO falhou")
        return {"status": STATUS_SUCESSO, "quantidadeAbastecimentos": 2}

    svc = SdsCatchupService(
        sync_day=sync,
        last_sds_date=lambda _c: _coro(date(2026, 8, 12)),
        today_fn=lambda: date(2026, 8, 14),
        max_days=1,
        retries=0,
        sleep_fn=_no_sleep,
    )
    result = await svc.run(
        inicio=date(2026, 8, 13),
        fim=date(2026, 8, 13),
        fail_fast=True,
    )
    statuses = {item["empresaCodigo"]: item["status"] for item in result["detalhes"]}
    assert statuses[5555] == STATUS_SUCESSO
    assert statuses[11495] == STATUS_FALHA
    assert 74014 not in statuses
    assert 74014 not in seen
    assert result["ondaInterrompida"] is True
    assert result["failFast"] is True


@pytest.mark.asyncio
async def test_falha_de_uma_unidade_nao_interrompe():
    async def sync(emp, dia, force=False):
        if emp == 11495:
            raise RuntimeError("GET ABASTECIMENTO falhou")
        return {"status": STATUS_SUCESSO, "quantidadeAbastecimentos": 2}

    svc = SdsCatchupService(
        sync_day=sync,
        last_sds_date=lambda _c: _coro(date(2026, 8, 12)),
        today_fn=lambda: date(2026, 8, 14),
        max_days=1,
        retries=0,
        sleep_fn=_no_sleep,
    )
    result = await svc.run(inicio=date(2026, 8, 13), fim=date(2026, 8, 13))
    statuses = {item["empresaCodigo"]: item["status"] for item in result["detalhes"]}
    assert statuses[5555] == STATUS_SUCESSO
    assert statuses[11495] == STATUS_FALHA
    assert statuses[74014] == STATUS_SUCESSO


@pytest.mark.asyncio
async def test_limite_dias_por_execucao():
    svc = SdsCatchupService(
        sync_day=_ok_sync,
        last_sds_date=lambda _c: _coro(date(2026, 8, 12)),
        today_fn=lambda: date(2026, 8, 20),
        max_days=2,
    )
    result = await svc.run(inicio=date(2026, 8, 13), fim=date(2026, 8, 18))
    assert result["diasPlanejados"] == 2
    assert result["diasRestantes"] == 4


@pytest.mark.asyncio
async def test_lock_concorrencia():
    entered = asyncio.Event()
    release = asyncio.Event()

    async def slow(emp, dia, force=False):
        entered.set()
        await release.wait()
        return {"status": STATUS_SUCESSO}

    svc = SdsCatchupService(
        sync_day=slow,
        last_sds_date=lambda _c: _coro(date(2026, 8, 12)),
        today_fn=lambda: date(2026, 8, 14),
        max_days=1,
        retries=0,
        sleep_fn=_no_sleep,
    )
    task = asyncio.create_task(
        svc.run(inicio=date(2026, 8, 13), fim=date(2026, 8, 13), empresas=[5555])
    )
    await asyncio.wait_for(entered.wait(), timeout=2)
    locked = await svc.run(inicio=date(2026, 8, 13), fim=date(2026, 8, 13), empresas=[5555])
    assert locked["status"] == "LOCKED"
    release.set()
    await task


@pytest.mark.asyncio
async def test_d1_depois_do_catchup():
    seen: list[date] = []

    async def sync(emp, dia, force=False):
        seen.append(dia)
        return {"status": STATUS_SUCESSO}

    svc = SdsCatchupService(
        sync_day=sync,
        last_sds_date=lambda _c: _coro(date(2026, 8, 12)),
        today_fn=lambda: date(2026, 8, 20),
        max_days=1,
    )
    await svc.run(inicio=date(2026, 8, 13), include_d1=True, empresas=[5555])
    assert date(2026, 8, 13) in seen
    assert date(2026, 8, 19) in seen


@pytest.mark.asyncio
async def test_sem_movimento_diferente_de_falha():
    async def empty(emp, dia, force=False):
        return {"status": STATUS_SEM_MOVIMENTO}

    async def boom(emp, dia, force=False):
        raise RuntimeError("timeout")

    ok = SdsCatchupService(
        sync_day=empty,
        last_sds_date=lambda _c: _coro(date(2026, 8, 12)),
        today_fn=lambda: date(2026, 8, 14),
        retries=0,
    )
    good = await ok.run(inicio=date(2026, 8, 13), fim=date(2026, 8, 13), empresas=[5555])
    assert good["contadores"][STATUS_SEM_MOVIMENTO] == 1
    assert good["contadores"][STATUS_FALHA] == 0

    bad = SdsCatchupService(
        sync_day=boom,
        last_sds_date=lambda _c: _coro(date(2026, 8, 12)),
        today_fn=lambda: date(2026, 8, 14),
        retries=0,
        sleep_fn=_no_sleep,
    )
    fail = await bad.run(inicio=date(2026, 8, 13), fim=date(2026, 8, 13), empresas=[5555])
    assert fail["contadores"][STATUS_FALHA] == 1
    assert fail["contadores"][STATUS_SEM_MOVIMENTO] == 0


def test_log_structured_redige_fingerprint():
    from src.core.logger import get_logger, log_structured

    records: list[str] = []

    class _Handler(logging.Handler):
        def emit(self, record):
            records.append(record.getMessage())

    logger = get_logger("sds.canary.logtest")
    logger.handlers = [_Handler()]
    log_structured(logger, {"token": "773bf5b0b95f", "endpoint": "/INTEGRACAO/ABASTECIMENTO"})
    assert records
    assert "773bf5b0b95f" not in records[0]
    assert "[redacted]" in records[0]


def test_sanitize_e_writes():
    dirty = sanitize_value(
        {
            "token": "abc",
            "url": "https://host/INTEGRACAO/ABASTECIMENTO?CHAVE=secreto",
            "erro": "falhou CHAVE=secreto",
        }
    )
    assert dirty["token"] == "[redacted]"
    assert "secreto" not in str(dirty)
    assert WEBPOSTO_WRITES == 0
    assert is_webposto_write_path("/api/v1/ops/data-sync/status") is False


def test_endpoint_status_papeis():
    from src.interfaces.http.routes import data_sync as route

    app = FastAPI()
    app.include_router(route.router)
    app.dependency_overrides[get_current_user] = lambda: {"role": "director"}
    client = TestClient(app)
    response = client.get("/api/v1/ops/data-sync/status")
    assert response.status_code == 200
    body = response.json()
    assert body["webpostoWrites"] == 0
    assert "token" not in str(body).lower() or "[redacted]" in str(body)
    for role in ("owner", "admin", "audit"):
        app.dependency_overrides[get_current_user] = lambda role=role: {"role": role}
        assert client.get("/api/v1/ops/data-sync/status").status_code == 200
    app.dependency_overrides[get_current_user] = lambda: {"role": "manager"}
    assert client.get("/api/v1/ops/data-sync/status").status_code == 403


@pytest.mark.asyncio
async def test_get_periodo_pagina_zero_falha_nao_vira_vazio():
    from src.models.error_model import WebPostoError
    from src.models.response_model import WebPostoResponse
    from src.services.abastecimento_service import AbastecimentoService

    class _Client:
        async def call_endpoint(self, endpoint_key, params=None):
            return WebPostoResponse.fail(
                WebPostoError(
                    endpoint="abastecimento",
                    status=401,
                    type="AUTHORIZATION_ERROR",
                    message="sem chave",
                )
            )

    svc = AbastecimentoService(_Client())
    svc._client_for = lambda _empresa: _Client()
    resp = await svc.get_periodo("2026-08-13", "2026-08-13", empresa_codigo=5555)
    assert resp.success is False
    assert resp.data is None


@pytest.mark.asyncio
async def test_get_periodo_pagina_posterior_propaga_falha():
    from src.models.error_model import WebPostoError
    from src.models.response_model import WebPostoResponse
    from src.services.abastecimento_service import AbastecimentoService

    class _Client:
        async def call_endpoint(self, endpoint_key, params=None):
            if not (params or {}).get("ultimoCodigo"):
                return WebPostoResponse.ok(
                    {"dados": [{"empresaCodigo": 74014, "codigo": 7}] * 200, "ultimoCodigo": 70}
                )
            return WebPostoResponse.fail(
                WebPostoError(
                    endpoint="abastecimento",
                    status=500,
                    type="NETWORK_ERROR",
                    message="pagina posterior",
                )
            )

    svc = AbastecimentoService(_Client())
    svc._client_for = lambda _empresa: _Client()
    resp = await svc.get_periodo("2026-08-13", "2026-08-13", empresa_codigo=74014)
    assert resp.success is False
    assert resp.data is None


async def _ok_sync(emp, dia, force=False):
    return {"status": STATUS_SUCESSO, "quantidadeAbastecimentos": 1, "registrosSemIdentidade": 0}


async def _coro(value):
    return value


async def _no_sleep(_delay):
    return None
