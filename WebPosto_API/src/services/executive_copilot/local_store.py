"""Leitura local de checkpoints e fatos SDS. Somente SELECT. Sem rede."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import date
from typing import Any

from src.infrastructure.config.settings import settings
from src.services.executive_copilot.coverage import DayCheckpoint
from src.services.executive_copilot.metrics import LocalSourceError, UnitDayFacts
from src.services.sds_identity import COMPLETE_STATUSES, STATUS_SEM_MOVIMENTO
from src.services.sds_sanitize import sanitize_text

ConnectFn = Callable[[], sqlite3.Connection]


def _sqlite_file() -> str:
    raw = str(getattr(settings, "database_url", "") or "")
    if "sqlite" not in raw.lower():
        raise LocalSourceError("fonte local indisponivel")
    if ":///" in raw:
        path = raw.split(":///", 1)[1]
    elif "://" in raw:
        path = raw.split("://", 1)[1]
    else:
        path = raw
    path = path.split("?")[0].strip()
    if not path:
        raise LocalSourceError("fonte local indisponivel")
    return path


def _parse_day(value: Any) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _nullable_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


class _SqliteReader:
    def __init__(
        self,
        db_path: str | None = None,
        *,
        connect: ConnectFn | None = None,
        readonly: bool = True,
    ) -> None:
        self._db_path = db_path
        self._connect_fn = connect
        self._readonly = readonly

    def _open(self) -> sqlite3.Connection:
        if self._connect_fn is not None:
            conn = self._connect_fn()
        else:
            path = self._db_path or _sqlite_file()
            try:
                if self._readonly:
                    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
                else:
                    conn = sqlite3.connect(path, timeout=5)
            except sqlite3.Error as exc:
                raise LocalSourceError(sanitize_text("falha ao abrir fonte local")) from exc
        conn.row_factory = sqlite3.Row
        return conn

    def fetchall(self, sql: str, params: list[Any]) -> list[sqlite3.Row]:
        conn = self._open()
        try:
            return list(conn.execute(sql, params).fetchall())
        except sqlite3.Error as exc:
            raise LocalSourceError(sanitize_text("falha ao ler fonte local")) from exc
        finally:
            conn.close()


class SqliteCheckpointStore:
    def __init__(
        self,
        db_path: str | None = None,
        *,
        connect: ConnectFn | None = None,
        readonly: bool = True,
    ) -> None:
        self._reader = _SqliteReader(db_path, connect=connect, readonly=readonly)

    def list_days(self, units: list[int], start: date, end: date) -> list[DayCheckpoint]:
        if not units:
            return []
        placeholders = ",".join("?" for _ in units)
        sql = (
            "SELECT empresa_codigo, data_referencia, status, quantidade_abastecimentos, "
            "registros_sem_identidade "
            f"FROM sds_day_status WHERE empresa_codigo IN ({placeholders}) "
            "AND data_referencia >= ? AND data_referencia <= ?"
        )
        rows = self._reader.fetchall(sql, [*units, start.isoformat(), end.isoformat()])
        return [
            DayCheckpoint(
                empresa_codigo=int(row["empresa_codigo"]),
                data_referencia=_parse_day(row["data_referencia"]),
                status=str(row["status"] or ""),
                quantidade_abastecimentos=row["quantidade_abastecimentos"],
                registros_sem_identidade=int(row["registros_sem_identidade"] or 0),
            )
            for row in rows
        ]

    def list_available(self, units: list[int]) -> list[DayCheckpoint]:
        if not units:
            return []
        placeholders = ",".join("?" for _ in units)
        sql = (
            "SELECT empresa_codigo, data_referencia, status, quantidade_abastecimentos, "
            "registros_sem_identidade "
            f"FROM sds_day_status WHERE empresa_codigo IN ({placeholders})"
        )
        rows = self._reader.fetchall(sql, list(units))
        return [
            DayCheckpoint(
                empresa_codigo=int(row["empresa_codigo"]),
                data_referencia=_parse_day(row["data_referencia"]),
                status=str(row["status"] or ""),
                quantidade_abastecimentos=row["quantidade_abastecimentos"],
                registros_sem_identidade=int(row["registros_sem_identidade"] or 0),
            )
            for row in rows
        ]


class SqliteFuelFactsStore:
    def __init__(
        self,
        db_path: str | None = None,
        *,
        connect: ConnectFn | None = None,
        readonly: bool = True,
    ) -> None:
        self._reader = _SqliteReader(db_path, connect=connect, readonly=readonly)

    def list_facts(self, units: list[int], start: date, end: date) -> list[UnitDayFacts]:
        if not units:
            return []
        placeholders = ",".join("?" for _ in units)
        params = [*units, start.isoformat(), end.isoformat()]
        checks = self._reader.fetchall(
            "SELECT empresa_codigo, data_referencia, status, quantidade_abastecimentos, "
            "registros_sem_identidade "
            f"FROM sds_day_status WHERE empresa_codigo IN ({placeholders}) "
            "AND data_referencia >= ? AND data_referencia <= ?",
            params,
        )
        sales = self._reader.fetchall(
            "SELECT empresa_codigo, data_referencia, "
            "SUM(litros_vendidos) AS litros, SUM(faturamento_bruto) AS faturamento "
            f"FROM sales_daily_summary WHERE empresa_codigo IN ({placeholders}) "
            "AND data_referencia >= ? AND data_referencia <= ? "
            "GROUP BY empresa_codigo, data_referencia",
            params,
        )
        sales_map = {
            (int(row["empresa_codigo"]), _parse_day(row["data_referencia"])): row
            for row in sales
        }
        facts: list[UnitDayFacts] = []
        for row in checks:
            day = _parse_day(row["data_referencia"])
            unit = int(row["empresa_codigo"])
            status = str(row["status"] or "")
            if status not in COMPLETE_STATUSES:
                continue
            sale = sales_map.get((unit, day))
            litros = _nullable_float(sale["litros"]) if sale is not None else None
            faturamento = _nullable_float(sale["faturamento"]) if sale is not None else None
            if status == STATUS_SEM_MOVIMENTO and sale is None:
                litros = 0.0
                faturamento = 0.0
            facts.append(
                UnitDayFacts(
                    empresa_codigo=unit,
                    data_referencia=day,
                    status=status,
                    litros=litros,
                    faturamento=faturamento,
                    quantidade=row["quantidade_abastecimentos"],
                    registros_sem_identidade=int(row["registros_sem_identidade"] or 0),
                )
            )
        return facts
