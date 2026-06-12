-- F07.7 — Commercial Outcome DW

CREATE TABLE IF NOT EXISTS fact_commercial_outcome (
    outcome_id SERIAL PRIMARY KEY,
    empresa_codigo BIGINT,
    periodo_inicio DATE NOT NULL,
    periodo_fim DATE NOT NULL,
    receita_antes NUMERIC(14, 2),
    receita_depois NUMERIC(14, 2),
    delta_receita NUMERIC(14, 2),
    margem_antes NUMERIC(14, 2),
    margem_depois NUMERIC(14, 2),
    delta_margem NUMERIC(14, 2),
    mix_produtos_vendidos_antes_pct NUMERIC(8, 2),
    mix_produtos_vendidos_depois_pct NUMERIC(8, 2),
    delta_mix_pct NUMERIC(8, 2),
    dependencia_combustivel_antes_pct NUMERIC(8, 2),
    dependencia_combustivel_depois_pct NUMERIC(8, 2),
    delta_dependencia_pct NUMERIC(8, 2),
    margem_prevista NUMERIC(14, 2),
    margem_realizada NUMERIC(14, 2),
    produtos_impactados INT,
    acuracia_receita_pct NUMERIC(8, 2),
    lineage JSONB NOT NULL DEFAULT '[]',
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fact_commercial_outcome_periodo
    ON fact_commercial_outcome (periodo_inicio, periodo_fim);
