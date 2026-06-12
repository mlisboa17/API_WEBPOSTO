-- F07.5 — Product Opportunity & Assortment Intelligence DW

CREATE TABLE IF NOT EXISTS fact_product_assortment_rollup (
    rollup_id SERIAL PRIMARY KEY,
    produto_codigo BIGINT NOT NULL,
    nome VARCHAR(256),
    departamento VARCHAR(32),
    quantidade NUMERIC(14, 4) NOT NULL DEFAULT 0,
    receita NUMERIC(14, 2) NOT NULL DEFAULT 0,
    margem_bruta NUMERIC(14, 2) NOT NULL DEFAULT 0,
    margem_pct NUMERIC(8, 2) NOT NULL DEFAULT 0,
    qtd_filiais INT NOT NULL DEFAULT 0,
    filiais_ativas JSONB NOT NULL DEFAULT '[]',
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_commercial_focus (
    focus_id SERIAL PRIMARY KEY,
    produto_codigo BIGINT NOT NULL,
    foco_comercial_score NUMERIC(8, 2) NOT NULL DEFAULT 0,
    acoes_recomendadas JSONB NOT NULL DEFAULT '[]',
    margem_pct NUMERIC(8, 2),
    receita NUMERIC(14, 2),
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_branch_benchmark_gap (
    gap_id SERIAL PRIMARY KEY,
    empresa_codigo BIGINT NOT NULL,
    mix_produtos_vendidos_pct NUMERIC(8, 2),
    benchmark_mix_pv_pct NUMERIC(8, 2),
    gap_benchmark_pct NUMERIC(8, 2),
    status VARCHAR(32) NOT NULL DEFAULT 'ABAIXO_BENCHMARK',
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_fuel_dependency_risk (
    risk_id SERIAL PRIMARY KEY,
    empresa_codigo BIGINT NOT NULL,
    dependencia_combustivel_pct NUMERIC(8, 2),
    mix_produtos_vendidos_pct NUMERIC(8, 2),
    risco VARCHAR(64) NOT NULL DEFAULT 'DEPENDENCIA_COMBUSTIVEL_ALTA',
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
