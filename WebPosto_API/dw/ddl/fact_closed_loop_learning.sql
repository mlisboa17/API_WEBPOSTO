-- F05.5 — Closed Loop Learning Engine DW model

CREATE TABLE IF NOT EXISTS fact_learning_event (
    learning_event_id VARCHAR(64) PRIMARY KEY,
    recommendation_id VARCHAR(64),
    effectiveness VARCHAR(32) NOT NULL,
    learning_score NUMERIC(8, 2) NOT NULL DEFAULT 0,
    confidence_adjustment NUMERIC(8, 2) NOT NULL DEFAULT 0,
    historical_accuracy NUMERIC(8, 2),
    confidence_level VARCHAR(16) NOT NULL,
    has_execution_evidence BOOLEAN NOT NULL DEFAULT FALSE,
    lineage JSONB NOT NULL DEFAULT '[]',
    evidence_source JSONB NOT NULL DEFAULT '{}',
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    empresa_codigo INTEGER,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_recommendation_accuracy (
    recommendation_id VARCHAR(64) PRIMARY KEY,
    acuracia_roi NUMERIC(8, 2),
    effectiveness VARCHAR(32) NOT NULL,
    roi_previsto NUMERIC(14, 2),
    roi_realizado NUMERIC(14, 2),
    delta_roi NUMERIC(14, 2),
    has_execution_evidence BOOLEAN NOT NULL DEFAULT FALSE,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_roi_accuracy (
    recommendation_id VARCHAR(64) PRIMARY KEY,
    roi_previsto NUMERIC(14, 2) NOT NULL DEFAULT 0,
    roi_realizado NUMERIC(14, 2),
    delta_roi NUMERIC(14, 2),
    acuracia_roi NUMERIC(8, 2),
    erro_percentual NUMERIC(8, 2),
    has_execution_evidence BOOLEAN NOT NULL DEFAULT FALSE,
    roi_outcome VARCHAR(32),
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_learning_score (
    recommendation_id VARCHAR(64) PRIMARY KEY,
    historical_score NUMERIC(8, 2) NOT NULL DEFAULT 0,
    learning_score NUMERIC(8, 2),
    confidence_adjustment NUMERIC(8, 2),
    score_roi NUMERIC(8, 2),
    score_efetividade NUMERIC(8, 2),
    score_execucao NUMERIC(8, 2),
    score_precisao NUMERIC(8, 2),
    lineage JSONB NOT NULL DEFAULT '[]',
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fact_learning_event_effectiveness ON fact_learning_event (effectiveness);
CREATE INDEX IF NOT EXISTS idx_fact_learning_score_historical ON fact_learning_score (historical_score);
