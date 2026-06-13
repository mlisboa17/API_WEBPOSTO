-- F07.8 — Recommendation Calibration DW

CREATE TABLE IF NOT EXISTS fact_recommendation_calibration (
    calibration_id SERIAL PRIMARY KEY,
    action_id VARCHAR(64) NOT NULL,
    execution_id VARCHAR(96),
    outcome_id VARCHAR(96),
    empresa_codigo BIGINT NOT NULL,
    tipo_acao VARCHAR(64) NOT NULL,
    roi_previsto NUMERIC(14, 2) NOT NULL,
    roi_real NUMERIC(14, 2) NOT NULL,
    erro_pct NUMERIC(8, 2) NOT NULL,
    confidence_level VARCHAR(16) NOT NULL,
    acuracia_receita_pct NUMERIC(8, 2),
    lineage JSONB NOT NULL DEFAULT '[]',
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fact_recommendation_calibration_confidence
    ON fact_recommendation_calibration (confidence_level);

CREATE INDEX IF NOT EXISTS idx_fact_recommendation_calibration_empresa
    ON fact_recommendation_calibration (empresa_codigo);
