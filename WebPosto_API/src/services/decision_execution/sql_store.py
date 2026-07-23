"""EXEC-03 — persistência real (SQL) de ExecutionRecord.

Substitui `ExecutionRecordStore` (JSON file) por uma tabela SQL única com
payload JSON completo — mesma fidelidade do JSON store, mas com uma base de
dados real por trás. Funciona com SQLite (padrão, sem dependências externas —
útil para dev/test) e com PostgreSQL (setando `EXECUTION_DB_URL` para uma
URL síncrona, ex.: `postgresql+psycopg2://user:pass@host:5432/webposto`) —
usa `JSON().with_variant(JSONB, "postgresql")` para armazenar o payload como
JSONB de verdade quando o backend for Postgres.

Interface idêntica a `ExecutionRecordStore` (save/get/update/list_all), então
é um drop-in replacement para `ExecutionService(repository=...)` sem precisar
alterar `ExecutionService` nem as rotas HTTP.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Callable

from sqlalchemy import Column, DateTime, MetaData, String, Table, create_engine, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import JSON

from src.services.decision_execution.models import ExecutionRecord

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SQLITE_PATH = ROOT / "snapshots" / "decision_execution" / "store.db"

_metadata = MetaData()

execution_records_table = Table(
    "execution_records",
    _metadata,
    Column("decision_id", String, primary_key=True),
    Column("tenant_id", String, index=True, nullable=False),
    Column("empresa_codigo", String, index=True, nullable=False),
    Column("current_status", String, index=True, nullable=False),
    Column("decision_category", String, index=True, nullable=True),
    Column("updated_at", DateTime, server_default=func.now(), onupdate=func.now()),
    Column("payload", JSON().with_variant(JSONB, "postgresql"), nullable=False),
)


def _default_db_url() -> str:
    env_url = os.environ.get("EXECUTION_DB_URL")
    if env_url:
        return env_url
    DEFAULT_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DEFAULT_SQLITE_PATH}"


def _is_sqlite_url(db_url: str) -> bool:
    return db_url.startswith("sqlite") or db_url == "sqlite"


def _engine_kwargs(db_url: str) -> dict:
    """Retorna kwargs de pool apropriados para SQLite (dev) ou Postgres (prod)."""
    if _is_sqlite_url(db_url):
        # StaticPool + check_same_thread=False permitem acesso reentrante/thread-safe
        # ao arquivo SQLite sem as limitações do QueuePool padrão.
        return {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
            "pool_pre_ping": True,
        }
    return {
        "pool_pre_ping": True,
        "pool_recycle": 3600,
        "pool_size": 5,
        "max_overflow": 10,
    }


class SQLExecutionRecordStore:
    """Repository SQL (SQLite ou PostgreSQL) para ExecutionRecord."""

    def __init__(self, db_url: str | None = None) -> None:
        resolved_url = db_url or _default_db_url()
        self._engine = create_engine(resolved_url, future=True, **_engine_kwargs(resolved_url))
        self._lock = threading.RLock()
        _metadata.create_all(self._engine, tables=[execution_records_table])

    def dispose(self) -> None:
        """Encerra o pool de conexões. Deve ser chamado no shutdown da aplicação."""
        self._engine.dispose()

    def save(self, record: ExecutionRecord) -> ExecutionRecord:
        payload = record.model_dump(mode="json")
        row = {
            "decision_id": record.decision_id,
            "tenant_id": record.tenant_id,
            "empresa_codigo": record.empresa_codigo,
            "current_status": record.current_status.value,
            "decision_category": record.decision_category,
            "payload": payload,
        }
        with self._lock, self._engine.begin() as conn:
            existing = conn.execute(
                select(execution_records_table.c.decision_id).where(
                    execution_records_table.c.decision_id == record.decision_id
                )
            ).first()
            if existing:
                conn.execute(
                    execution_records_table.update()
                    .where(execution_records_table.c.decision_id == record.decision_id)
                    .values(**row)
                )
            else:
                conn.execute(execution_records_table.insert().values(**row))
        return record

    def get(self, decision_id: str) -> ExecutionRecord | None:
        with self._engine.connect() as conn:
            result = conn.execute(
                select(execution_records_table.c.payload).where(
                    execution_records_table.c.decision_id == decision_id
                )
            ).first()
        if not result:
            return None
        return ExecutionRecord.model_validate(result.payload)

    def update(
        self,
        decision_id: str,
        mutator: Callable[[ExecutionRecord], ExecutionRecord],
    ) -> ExecutionRecord:
        with self._lock:
            record = self.get(decision_id)
            if record is None:
                raise KeyError(decision_id)
            record = mutator(record)
            self.save(record)
            return record

    def list_all(self) -> list[ExecutionRecord]:
        with self._engine.connect() as conn:
            rows = conn.execute(select(execution_records_table.c.payload)).all()
        return [ExecutionRecord.model_validate(row.payload) for row in rows]
