-- F07.7 — Commercial Execution DW

CREATE TABLE IF NOT EXISTS fact_commercial_execution (
    execution_id SERIAL PRIMARY KEY,
    action_id VARCHAR(64) NOT NULL,
    action_code VARCHAR(32),
    tipo VARCHAR(64) NOT NULL,
    titulo VARCHAR(256),
    empresa_codigo BIGINT NOT NULL,
    responsavel_id BIGINT,
    responsavel_nome VARCHAR(128),
    prioridade VARCHAR(16) NOT NULL,
    lifecycle_status VARCHAR(32) NOT NULL,
    data_criacao DATE,
    data_execucao DATE,
    receita_prevista NUMERIC(14, 2),
    receita_realizada NUMERIC(14, 2),
    receita_delta NUMERIC(14, 2),
    margem_prevista NUMERIC(14, 2),
    margem_realizada NUMERIC(14, 2),
    margem_delta NUMERIC(14, 2),
    acuracia_receita_pct NUMERIC(8, 2),
    roi_real NUMERIC(14, 2),
    roi_real_calculavel BOOLEAN NOT NULL DEFAULT FALSE,
    has_execution_evidence BOOLEAN NOT NULL DEFAULT FALSE,
    execution_evidence JSONB NOT NULL DEFAULT '{}',
    lineage JSONB NOT NULL DEFAULT '[]',
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fact_commercial_execution_empresa
    ON fact_commercial_execution (empresa_codigo);

CREATE INDEX IF NOT EXISTS idx_fact_commercial_execution_status
    ON fact_commercial_execution (lifecycle_status);

CREATE TABLE IF NOT EXISTS fact_commercial_execution_summary (
    summary_id SERIAL PRIMARY KEY,
    total_acoes INT NOT NULL DEFAULT 0,
    acoes_executadas INT NOT NULL DEFAULT 0,
    acoes_validadas INT NOT NULL DEFAULT 0,
    acoes_canceladas INT NOT NULL DEFAULT 0,
    taxa_execucao_pct NUMERIC(8, 2),
    taxa_validacao_pct NUMERIC(8, 2),
    receita_prevista NUMERIC(14, 2),
    receita_realizada NUMERIC(14, 2),
    delta_receita NUMERIC(14, 2),
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
