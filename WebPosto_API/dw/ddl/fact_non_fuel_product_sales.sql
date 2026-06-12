-- F07.0 — Non-Fuel Product Sales DW model

CREATE TABLE IF NOT EXISTS dim_product_department (
    department_id SERIAL PRIMARY KEY,
    produto_codigo BIGINT NOT NULL,
    nome VARCHAR(256),
    departamento VARCHAR(32) NOT NULL,
    categoria VARCHAR(64),
    combustivel BOOLEAN NOT NULL DEFAULT FALSE,
    confidence_level VARCHAR(16) NOT NULL DEFAULT 'MEDIA',
    lineage JSONB NOT NULL DEFAULT '[]',
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dim_product_category (
    category_id SERIAL PRIMARY KEY,
    categoria VARCHAR(64) NOT NULL UNIQUE,
    departamento VARCHAR(32) NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_non_fuel_sales (
    sale_item_id VARCHAR(64) PRIMARY KEY,
    empresa_codigo BIGINT NOT NULL,
    empresa_nome VARCHAR(128),
    venda_codigo BIGINT,
    venda_item_codigo BIGINT,
    produto_codigo BIGINT NOT NULL,
    departamento VARCHAR(32) NOT NULL,
    categoria VARCHAR(64),
    quantidade NUMERIC(14, 3) NOT NULL,
    valor_total NUMERIC(14, 2) NOT NULL,
    nfce_codigo BIGINT,
    confidence_level VARCHAR(16) NOT NULL DEFAULT 'MEDIA',
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
    valor_nao_combustivel NUMERIC(14, 2),
    participacao_nao_combustivel_pct NUMERIC(8, 2),
    dependencia_combustivel_pct NUMERIC(8, 2),
    lineage JSONB NOT NULL DEFAULT '[]',
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
