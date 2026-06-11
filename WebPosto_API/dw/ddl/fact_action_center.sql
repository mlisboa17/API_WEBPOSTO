-- F05.2 — Action Center DW model

CREATE TABLE IF NOT EXISTS fact_action (
    action_id SERIAL PRIMARY KEY,
    action_code VARCHAR(64) NOT NULL UNIQUE,
    decision_id VARCHAR(64),
    dominio VARCHAR(32) NOT NULL,
    acao TEXT NOT NULL,
    prioridade INTEGER NOT NULL DEFAULT 3,
    lifecycle_status VARCHAR(32) NOT NULL,
    owner_id INTEGER NOT NULL,
    owner_name VARCHAR(256) NOT NULL,
    owner_role VARCHAR(64) NOT NULL,
    confidence_level VARCHAR(16),
    decision_evidence_type VARCHAR(16),
    roi_confidence VARCHAR(16),
    prazo VARCHAR(16),
    due_date DATE,
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_action_status (
    status_id SERIAL PRIMARY KEY,
    action_code VARCHAR(64) NOT NULL,
    lifecycle_status VARCHAR(32) NOT NULL,
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_action_evidence (
    evidence_id VARCHAR(64) PRIMARY KEY,
    action_code VARCHAR(64) NOT NULL,
    owner_id INTEGER,
    responsavel VARCHAR(256),
    evidence_type VARCHAR(32) NOT NULL,
    resultado TEXT,
    anexo TEXT,
    observacao TEXT,
    recorded_at TIMESTAMP NOT NULL,
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_action_roi (
    roi_id SERIAL PRIMARY KEY,
    action_code VARCHAR(64) NOT NULL,
    roi_esperado NUMERIC(14, 2) NOT NULL DEFAULT 0,
    roi_realizado NUMERIC(14, 2) NOT NULL DEFAULT 0,
    roi_delta NUMERIC(14, 2) NOT NULL DEFAULT 0,
    roi_outcome VARCHAR(16) NOT NULL,
    roi_confidence VARCHAR(16),
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fact_action_status ON fact_action (lifecycle_status, prioridade);
CREATE INDEX IF NOT EXISTS idx_fact_action_owner ON fact_action (owner_id, owner_name);
CREATE INDEX IF NOT EXISTS idx_fact_action_evidence_action ON fact_action_evidence (action_code);
