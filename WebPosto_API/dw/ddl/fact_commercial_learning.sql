-- F07.8 — Commercial Learning DW

CREATE TABLE IF NOT EXISTS fact_commercial_learning (
    learning_id SERIAL PRIMARY KEY,
    action_id VARCHAR(64) NOT NULL,
    execution_id VARCHAR(96),
    outcome_id VARCHAR(96),
    empresa_codigo BIGINT NOT NULL,
    tipo_acao VARCHAR(64) NOT NULL,
    responsavel_nome VARCHAR(128),
    roi_previsto NUMERIC(14, 2),
    roi_real NUMERIC(14, 2),
    erro_pct NUMERIC(8, 2),
    confidence_level VARCHAR(16),
    taxa_acerto_pct NUMERIC(8, 2),
    receita_prevista NUMERIC(14, 2),
    receita_realizada NUMERIC(14, 2),
    margem_prevista NUMERIC(14, 2),
    margem_realizada NUMERIC(14, 2),
    lineage JSONB NOT NULL DEFAULT '[]',
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fact_commercial_learning_empresa
    ON fact_commercial_learning (empresa_codigo);

CREATE INDEX IF NOT EXISTS idx_fact_commercial_learning_tipo
    ON fact_commercial_learning (tipo_acao);
