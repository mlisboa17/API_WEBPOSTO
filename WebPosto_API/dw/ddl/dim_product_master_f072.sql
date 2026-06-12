-- F07.2 — Product Master corporate layer

CREATE TABLE IF NOT EXISTS dim_product_master (
    product_master_id SERIAL PRIMARY KEY,
    produto_codigo BIGINT NOT NULL,
    nome VARCHAR(256),
    ncm VARCHAR(16),
    grupo_codigo BIGINT,
    sub_grupo1_codigo BIGINT,
    sub_grupo2_codigo BIGINT,
    sub_grupo3_codigo BIGINT,
    departamento VARCHAR(32) NOT NULL,
    match_tier VARCHAR(32),
    sources JSONB NOT NULL DEFAULT '[]',
    empresas JSONB NOT NULL DEFAULT '[]',
    empresa_codigo BIGINT,
    empresa_nome VARCHAR(128),
    filial VARCHAR(128),
    confidence_level VARCHAR(16) NOT NULL DEFAULT 'MEDIA',
    evidence JSONB NOT NULL DEFAULT '[]',
    lineage JSONB NOT NULL DEFAULT '[]',
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (produto_codigo)
);

CREATE TABLE IF NOT EXISTS fact_product_mix (
    mix_id SERIAL PRIMARY KEY,
    empresa_codigo BIGINT NOT NULL,
    empresa_nome VARCHAR(128),
    filial VARCHAR(128),
    mix_combustivel_pct NUMERIC(8, 2),
    mix_produtos_vendidos_pct NUMERIC(8, 2),
    mix_lubrificantes_pct NUMERIC(8, 2),
    mix_servicos_pct NUMERIC(8, 2),
    mix_acessorios_pct NUMERIC(8, 2),
    mix_outros_departamentos JSONB NOT NULL DEFAULT '{}',
    dependencia_combustivel_pct NUMERIC(8, 2),
    mix_saudavel_score NUMERIC(8, 2),
    lineage JSONB NOT NULL DEFAULT '[]',
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_product_revenue (
    revenue_id SERIAL PRIMARY KEY,
    produto_codigo BIGINT NOT NULL,
    nome VARCHAR(256),
    valor NUMERIC(14, 2),
    quantidade NUMERIC(14, 3),
    rank_pos INT,
    cum_pct NUMERIC(8, 2),
    pareto80 BOOLEAN NOT NULL DEFAULT FALSE,
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
