-- F07.1 — Product Sales & Department DW model

CREATE TABLE IF NOT EXISTS dim_product (
    product_id SERIAL PRIMARY KEY,
    produto_codigo BIGINT NOT NULL UNIQUE,
    nome VARCHAR(256),
    ncm VARCHAR(16),
    grupo_codigo BIGINT,
    departamento VARCHAR(32) NOT NULL,
    combustivel BOOLEAN NOT NULL DEFAULT FALSE,
    confidence_level VARCHAR(16) NOT NULL DEFAULT 'MEDIA',
    evidence JSONB NOT NULL DEFAULT '[]',
    lineage JSONB NOT NULL DEFAULT '[]',
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dim_product_department (
    department_id SERIAL PRIMARY KEY,
    departamento VARCHAR(32) NOT NULL UNIQUE,
    label_visual VARCHAR(64) NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_product_sales (
    sale_item_id VARCHAR(64) PRIMARY KEY,
    empresa_codigo BIGINT NOT NULL,
    empresa_nome VARCHAR(128),
    venda_codigo BIGINT,
    venda_item_codigo BIGINT,
    produto_codigo BIGINT NOT NULL,
    departamento VARCHAR(32) NOT NULL,
    quantidade NUMERIC(14, 3) NOT NULL,
    valor_total NUMERIC(14, 2) NOT NULL,
    confidence_level VARCHAR(16) NOT NULL DEFAULT 'MEDIA',
    evidence JSONB NOT NULL DEFAULT '[]',
    lineage JSONB NOT NULL DEFAULT '[]',
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_product_department_sales (
    dept_sales_id SERIAL PRIMARY KEY,
    empresa_codigo BIGINT NOT NULL,
    nome_filial VARCHAR(128),
    valor_combustivel NUMERIC(14, 2),
    valor_produtos_vendidos NUMERIC(14, 2),
    participacao_produtos_vendidos_pct NUMERIC(8, 2),
    departamento_dominante VARCHAR(32),
    mix_departamentos JSONB NOT NULL DEFAULT '{}',
    lineage JSONB NOT NULL DEFAULT '[]',
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_product_coverage (
    coverage_id SERIAL PRIMARY KEY,
    produtos_no_catalogo INT,
    produtos_vendidos INT,
    produtos_sem_cadastro INT,
    produtos_sem_descricao INT,
    cobertura_cadastro_pct NUMERIC(8, 2),
    nfce_coverage_pct NUMERIC(8, 2),
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_product_ranking (
    ranking_id SERIAL PRIMARY KEY,
    produto_codigo BIGINT NOT NULL,
    nome VARCHAR(256),
    quantidade NUMERIC(14, 3),
    valor NUMERIC(14, 2),
    rank_pos INT,
    departamento VARCHAR(32),
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
