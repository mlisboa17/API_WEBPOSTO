-- F07.9 — Commercial Copilot DW

CREATE TABLE IF NOT EXISTS fact_commercial_copilot (
    copilot_id SERIAL PRIMARY KEY,
    recommendation_id VARCHAR(64),
    action_id VARCHAR(64),
    execution_id VARCHAR(96),
    outcome_id VARCHAR(96),
    empresa_codigo BIGINT,
    question_id VARCHAR(64),
    classificacao VARCHAR(16),
    tipo_acao VARCHAR(64),
    roi_estimado NUMERIC(14, 2),
    roi_realizado NUMERIC(14, 2),
    confidence_level VARCHAR(16) NOT NULL,
    evidence_source JSONB NOT NULL DEFAULT '[]',
    lineage JSONB NOT NULL DEFAULT '[]',
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fact_commercial_copilot_empresa
    ON fact_commercial_copilot (empresa_codigo);

CREATE INDEX IF NOT EXISTS idx_fact_commercial_copilot_action
    ON fact_commercial_copilot (action_id);
