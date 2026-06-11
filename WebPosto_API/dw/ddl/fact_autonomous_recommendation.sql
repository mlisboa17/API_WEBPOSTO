-- F05.4 — Autonomous Recommendation Engine DW model

CREATE TABLE IF NOT EXISTS fact_recommendation (
    recommendation_id VARCHAR(64) PRIMARY KEY,
    tipo VARCHAR(32) NOT NULL,
    titulo TEXT NOT NULL,
    descricao TEXT,
    classificacao VARCHAR(16) NOT NULL,
    impacto NUMERIC(14, 2) NOT NULL DEFAULT 0,
    decision_id VARCHAR(64),
    confidence_level VARCHAR(16) NOT NULL,
    evidence_source JSONB NOT NULL DEFAULT '{}',
    lineage JSONB NOT NULL DEFAULT '[]',
    labels JSONB NOT NULL DEFAULT '[]',
    justificativa TEXT,
    execucao_automatica BOOLEAN NOT NULL DEFAULT FALSE,
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    empresa_codigo INTEGER,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_recommendation_roi (
    recommendation_id VARCHAR(64) PRIMARY KEY REFERENCES fact_recommendation(recommendation_id),
    roi_esperado NUMERIC(14, 2) NOT NULL DEFAULT 0,
    roi_pessimista NUMERIC(14, 2) NOT NULL DEFAULT 0,
    roi_otimista NUMERIC(14, 2) NOT NULL DEFAULT 0,
    roi_medio NUMERIC(14, 2) NOT NULL DEFAULT 0,
    roi_realizado NUMERIC(14, 2),
    roi_label VARCHAR(32) NOT NULL DEFAULT 'ROI_PREVISTO',
    confidence_level VARCHAR(16) NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_recommendation_status (
    recommendation_id VARCHAR(64) PRIMARY KEY REFERENCES fact_recommendation(recommendation_id),
    lifecycle_status VARCHAR(32) NOT NULL,
    action_center_ref VARCHAR(64),
    due_date DATE,
    execucao_automatica BOOLEAN NOT NULL DEFAULT FALSE,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_recommendation_priority (
    recommendation_id VARCHAR(64) PRIMARY KEY REFERENCES fact_recommendation(recommendation_id),
    priority VARCHAR(4) NOT NULL,
    impact_score NUMERIC(8, 2) NOT NULL DEFAULT 0,
    roi_score NUMERIC(8, 2) NOT NULL DEFAULT 0,
    urgency_score NUMERIC(8, 2) NOT NULL DEFAULT 0,
    composite_score NUMERIC(8, 2) NOT NULL DEFAULT 0,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fact_recommendation_tipo ON fact_recommendation (tipo);
CREATE INDEX IF NOT EXISTS idx_fact_recommendation_priority ON fact_recommendation_priority (priority);
