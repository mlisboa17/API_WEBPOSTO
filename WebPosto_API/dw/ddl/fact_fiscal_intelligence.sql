-- F06.3 — Fiscal Intelligence DW model

CREATE TABLE IF NOT EXISTS fact_fiscal_product (
    fiscal_product_id VARCHAR(64) PRIMARY KEY,
    produto_codigo BIGINT NOT NULL,
    nome VARCHAR(256),
    ncm VARCHAR(16),
    cest VARCHAR(16),
    segmento VARCHAR(32),
    tipo_produto VARCHAR(8),
    combustivel BOOLEAN NOT NULL DEFAULT FALSE,
    ativo BOOLEAN,
    cst_estatico VARCHAR(8),
    monofasico BOOLEAN,
    confidence_level VARCHAR(16) NOT NULL DEFAULT 'ALTA',
    homologado BOOLEAN NOT NULL DEFAULT TRUE,
    lineage JSONB NOT NULL DEFAULT '[]',
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_fiscal_ncm (
    ncm_id SERIAL PRIMARY KEY,
    ncm VARCHAR(16),
    produto_codigo BIGINT,
    status VARCHAR(32) NOT NULL,
    duplicado BOOLEAN NOT NULL DEFAULT FALSE,
    inconsistente BOOLEAN NOT NULL DEFAULT FALSE,
    lineage JSONB NOT NULL DEFAULT '[]',
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_fiscal_risk (
    risk_id SERIAL PRIMARY KEY,
    produto_codigo BIGINT,
    tipo VARCHAR(64),
    risco VARCHAR(16) NOT NULL,
    sem_ncm BOOLEAN NOT NULL DEFAULT FALSE,
    sem_classificacao BOOLEAN NOT NULL DEFAULT FALSE,
    descricao TEXT,
    lineage JSONB NOT NULL DEFAULT '[]',
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_fiscal_classification (
    classification_id SERIAL PRIMARY KEY,
    tributo VARCHAR(16) NOT NULL,
    classificacao VARCHAR(16) NOT NULL,
    evidencia VARCHAR(128),
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fact_fiscal_product_segmento ON fact_fiscal_product (segmento);
CREATE INDEX IF NOT EXISTS idx_fact_fiscal_risk_level ON fact_fiscal_risk (risco);
