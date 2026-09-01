"""Adaptador SQLite temporário da Frente B. Sem rede e sem banco real de produção."""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

import httpx
import pytest

from src.services.executive_copilot.local_store import SqliteCheckpointStore, SqliteFuelFactsStore
from src.services.executive_copilot.metrics import LocalSourceError, aggregate_network
from src.services.executive_copilot.orchestrator import ExecutiveCopilotOrchestrator
from src.services.executive_copilot.http_models import AskRequest
from src.services.sds_identity import STATUS_SUCESSO

DAY = date(2026, 8, 27)


@pytest.fixture(autouse=True)
def block_external_http(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("chamada externa proibida")

    monkeypatch.setattr(httpx, "Client", boom)
    monkeypatch.setattr(httpx, "AsyncClient", boom)


class _TrackedConn:
    def __init__(self, raw: sqlite3.Connection, spy: "_ConnSpy") -> None:
        object.__setattr__(self, "_raw", raw)
        object.__setattr__(self, "_spy", spy)
        object.__setattr__(self, "_closed", False)

    def close(self) -> None:
        if self._closed:
            return
        object.__setattr__(self, "_closed", True)
        self._spy.closed += 1
        self._spy.live -= 1
        self._raw.close()

    def __getattr__(self, name: str):
        return getattr(self._raw, name)

    def __setattr__(self, name: str, value) -> None:
        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return
        setattr(self._raw, name, value)


class _ConnSpy:
    def __init__(self, path: str) -> None:
        self.path = path
        self.opened = 0
        self.closed = 0
        self.live = 0

    def __call__(self):
        self.opened += 1
        self.live += 1
        return _TrackedConn(sqlite3.connect(self.path), self)


def _build_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE sds_day_status (
                empresa_codigo INTEGER,
                data_referencia TEXT,
                status TEXT,
                quantidade_abastecimentos INTEGER,
                registros_sem_identidade INTEGER
            );
            CREATE TABLE sales_daily_summary (
                empresa_codigo INTEGER,
                data_referencia TEXT,
                codigo_produto_webposto TEXT,
                litros_vendidos REAL,
                faturamento_bruto REAL
            );
            """
        )
        conn.execute(
            "INSERT INTO sds_day_status VALUES (5555, '2026-08-27', 'SUCESSO', 10, 2)"
        )
        conn.execute(
            "INSERT INTO sds_day_status VALUES (11495, '2026-08-27', 'SUCESSO', 8, 0)"
        )
        conn.execute(
            "INSERT INTO sds_day_status VALUES (74014, '2026-08-27', 'SEM_MOVIMENTO_CONFIRMADO', 0, 0)"
        )
        conn.execute(
            "INSERT INTO sales_daily_summary VALUES (5555, '2026-08-27', '1', 100.0, 500.0)"
        )
        conn.execute(
            "INSERT INTO sales_daily_summary VALUES (11495, '2026-08-27', '1', NULL, NULL)"
        )
        conn.commit()
    finally:
        conn.close()


def test_sqlite_adapter_identity_ticket_null_and_closed_connections(tmp_path: Path) -> None:
    db = tmp_path / "sds.sqlite"
    _build_db(db)
    spy = _ConnSpy(str(db))
    checks = SqliteCheckpointStore(connect=spy, readonly=False)
    facts = SqliteFuelFactsStore(connect=spy, readonly=False)
    days = checks.list_days([5555, 11495, 74014], DAY, DAY)
    available = checks.list_available([5555])
    assert {row.data_referencia for row in available} == {DAY}
    by_unit = {row.empresa_codigo: row for row in days}
    assert by_unit[5555].registros_sem_identidade == 2
    assert by_unit[5555].quantidade_abastecimentos == 10
    rows = facts.list_facts([5555, 11495, 74014], DAY, DAY)
    mapped = {row.empresa_codigo: row for row in rows}
    assert mapped[5555].registros_sem_identidade == 2
    assert mapped[11495].litros is None
    assert mapped[11495].faturamento is None
    assert mapped[74014].litros == 0.0
    assert spy.live == 0
    assert spy.closed == spy.opened
    assert spy.opened >= 3


def test_sqlite_null_is_not_proven_zero(tmp_path: Path) -> None:
    db = tmp_path / "sds.sqlite"
    _build_db(db)
    facts = SqliteFuelFactsStore(db_path=str(db), readonly=False)
    rows = facts.list_facts([11495], DAY, DAY)
    assert rows[0].litros is None
    with pytest.raises(LocalSourceError, match="incompletos"):
        aggregate_network(rows, [11495], DAY, DAY)


def test_sqlite_facts_required_for_all_units_days_before_fact(tmp_path: Path) -> None:
    db = tmp_path / "sds.sqlite"
    _build_db(db)
    orch = ExecutiveCopilotOrchestrator(
        checkpoint_store=SqliteCheckpointStore(db_path=str(db), readonly=False),
        facts_store=SqliteFuelFactsStore(db_path=str(db), readonly=False),
    )
    request = AskRequest.model_validate(
        {
            "pergunta": "Qual o faturamento?",
            "especialista": "FINANCEIRO",
            "unidades": [5555, 11495],
            "periodo": {"inicio": "2026-08-27", "fim": "2026-08-27"},
        }
    )
    answer = orch.ask(request, {"role": "director"})
    assert answer.impact.status.value == "UNAVAILABLE"
    assert answer.suggested_action["code"] == "LOCAL_SOURCE_FAILED"
    assert answer.impact.amount is None


def test_sqlite_unreliable_count_nulls_ticket(tmp_path: Path) -> None:
    db = tmp_path / "sds.sqlite"
    _build_db(db)
    facts = SqliteFuelFactsStore(db_path=str(db), readonly=False)
    rows = facts.list_facts([5555], DAY, DAY)
    metric = aggregate_network(rows, [5555], DAY, DAY)[5555]
    assert metric.contagem_confiavel is False
    assert metric.ticket_reais is None
    assert metric.quantidade is None
