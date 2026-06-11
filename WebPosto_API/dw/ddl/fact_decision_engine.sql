-- F05.1 — Executive Decision Engine DW model

CREATE TABLE IF NOT EXISTS dim_decision (
    decision_sk SERIAL PRIMARY KEY,
    decision_code VARCHAR(64) NOT NULL UNIQUE,
    decision_name VARCHAR(256) NOT NULL,
    dominio VARCHAR(32) NOT NULL,
    sprint VARCHAR(16) DEFAULT 'F05.1'
);

CREATE TABLE IF NOT EXISTS dim_action (
    action_sk SERIAL PRIMARY KEY,
    action_code VARCHAR(64) NOT NULL UNIQUE,
    action_name VARCHAR(256) NOT NULL,
    dominio VARCHAR(32) NOT NULL,
    sprint VARCHAR(16) DEFAULT 'F05.1'
);

CREATE TABLE IF NOT EXISTS dim_priority (
    priority_sk SERIAL PRIMARY KEY,
    priority_code VARCHAR(16) NOT NULL UNIQUE,
    priority_name VARCHAR(64) NOT NULL,
    priority_rank INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_owner (
    owner_sk SERIAL PRIMARY KEY,
    owner_code VARCHAR(64) NOT NULL UNIQUE,
    owner_name VARCHAR(128) NOT NULL,
    owner_type VARCHAR(32) NOT NULL
);

INSERT INTO dim_priority (priority_code, priority_name, priority_rank) VALUES
    ('P1', 'Prioridade 1', 1),
    ('P2', 'Prioridade 2', 2),
    ('P3', 'Prioridade 3', 3)
ON CONFLICT (priority_code) DO NOTHING;

INSERT INTO dim_owner (owner_code, owner_name, owner_type) VALUES
    ('DIRETORIA', 'Diretoria Executiva', 'EXECUTIVO'),
    ('TESOURARIA', 'Tesouraria', 'FINANCEIRO'),
    ('CONTROLADORIA', 'Controladoria', 'FINANCEIRO'),
    ('PESSOAS', 'Gestão de Pessoas', 'PESSOAS'),
    ('OPERACOES', 'Gerente de Loja', 'OPERACIONAL'),
    ('RISCO', 'Comitê Executivo', 'RISCO')
ON CONFLICT (owner_code) DO NOTHING;

CREATE TABLE IF NOT EXISTS fact_decision (
    decision_id SERIAL PRIMARY KEY,
    decision_code VARCHAR(64) NOT NULL,
    decision_type VARCHAR(32) NOT NULL,
    prioridade INTEGER NOT NULL DEFAULT 3,
    impacto_estimado NUMERIC(14, 2) NOT NULL DEFAULT 0,
    roi_esperado NUMERIC(14, 2) NOT NULL DEFAULT 0,
    trust_executivo NUMERIC(6, 2),
    owner_code VARCHAR(64),
    prazo VARCHAR(16),
    origem VARCHAR(128),
    evidence_json JSONB,
    lineage_json JSONB,
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    empresa_codigo INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_action (
    action_id SERIAL PRIMARY KEY,
    action_code VARCHAR(64) NOT NULL,
    dominio VARCHAR(32) NOT NULL,
    acao TEXT NOT NULL,
    prioridade INTEGER NOT NULL DEFAULT 3,
    impacto NUMERIC(14, 2) NOT NULL DEFAULT 0,
    roi NUMERIC(14, 2) NOT NULL DEFAULT 0,
    complexidade VARCHAR(16),
    prazo VARCHAR(16),
    responsavel_json JSONB,
    origem VARCHAR(128),
    evidence_json JSONB,
    calculo_roi_json JSONB,
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_roi_priority (
    priority_id SERIAL PRIMARY KEY,
    action_code VARCHAR(64) NOT NULL,
    priority_rank INTEGER NOT NULL,
    priority_score NUMERIC(10, 2) NOT NULL DEFAULT 0,
    roi NUMERIC(14, 2) NOT NULL DEFAULT 0,
    impacto NUMERIC(14, 2) NOT NULL DEFAULT 0,
    risco_nivel VARCHAR(16),
    complexidade VARCHAR(16),
    prazo VARCHAR(16),
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_decision_snapshot (
    snapshot_id SERIAL PRIMARY KEY,
    payload_json JSONB NOT NULL,
    trust_executivo NUMERIC(6, 2),
    corporate_score NUMERIC(6, 2),
    executive_score NUMERIC(6, 2),
    total_acoes INTEGER NOT NULL DEFAULT 0,
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    empresa_codigo INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fact_decision_period ON fact_decision (data_inicial, data_final);
CREATE INDEX IF NOT EXISTS idx_fact_action_dominio ON fact_action (dominio, prioridade);
CREATE INDEX IF NOT EXISTS idx_fact_roi_priority_rank ON fact_roi_priority (priority_rank, priority_score DESC);
