"""Tarefas locais do Action Hub. Persistência SQLite — API writes = 0."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from src.services.catalog.models import connect_catalog_db, init_catalog_schema
from src.services.proposals.db.connection import default_db_path

ACTION_HUB_SCHEMA = """
CREATE TABLE IF NOT EXISTS webposto_action_hub_tasks (
    id TEXT PRIMARY KEY,
    empresa_codigo INTEGER NOT NULL,
    agente_origem TEXT NOT NULL,
    codigo_diagnostico TEXT NOT NULL,
    identificador_referencia TEXT NOT NULL,
    descricao TEXT,
    impacto_financeiro_reais REAL NOT NULL DEFAULT 0,
    ganho_estimado_reais REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'PENDENTE',
    responsavel_setor TEXT,
    justificativa TEXT,
    resolvido_em TEXT,
    resolvido_por TEXT,
    criado_em TEXT NOT NULL,
    atualizado_em TEXT NOT NULL,
    UNIQUE (empresa_codigo, agente_origem, codigo_diagnostico, identificador_referencia)
);
CREATE INDEX IF NOT EXISTS idx_action_hub_empresa_status
    ON webposto_action_hub_tasks(empresa_codigo, status, atualizado_em);
CREATE INDEX IF NOT EXISTS idx_action_hub_agente
    ON webposto_action_hub_tasks(agente_origem, status);
CREATE INDEX IF NOT EXISTS idx_action_hub_setor
    ON webposto_action_hub_tasks(responsavel_setor, status);
CREATE TABLE IF NOT EXISTS webposto_action_hub_copilot_drafts (
    id TEXT PRIMARY KEY,
    action_type TEXT NOT NULL,
    status TEXT NOT NULL,
    empresa_codigo INTEGER NOT NULL,
    requester TEXT NOT NULL,
    role TEXT NOT NULL,
    valor REAL,
    descricao TEXT,
    filled_json TEXT NOT NULL,
    missing_json TEXT NOT NULL,
    auto_classified_json TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    plan_hash TEXT NOT NULL,
    contract_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_action_hub_copilot_drafts_unit_status
    ON webposto_action_hub_copilot_drafts(empresa_codigo, status, updated_at);
CREATE TABLE IF NOT EXISTS webposto_action_hub_copilot_events (
    id TEXT PRIMARY KEY,
    draft_id TEXT NOT NULL,
    event TEXT NOT NULL,
    actor TEXT,
    role TEXT,
    detail_json TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_action_hub_copilot_events_draft
    ON webposto_action_hub_copilot_events(draft_id, created_at);
"""


def init_action_hub_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(ACTION_HUB_SCHEMA)
    conn.commit()


def connect_action_hub_db(path: Path | str | None = None) -> sqlite3.Connection:
    conn = connect_catalog_db(path or default_db_path())
    init_catalog_schema(conn)
    init_action_hub_schema(conn)
    return conn
