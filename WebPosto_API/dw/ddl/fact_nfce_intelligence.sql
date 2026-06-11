-- F06.1 — NFCE Intelligence DW model

CREATE TABLE IF NOT EXISTS fact_nfce_catalog (
    nfce_id VARCHAR(64) PRIMARY KEY,
    nfce_codigo BIGINT,
    venda_codigo BIGINT,
    empresa_codigo INTEGER NOT NULL,
    situacao_fiscal VARCHAR(32) NOT NULL,
    situacao_original VARCHAR(32),
    data_emissao DATE,
    protocolo_cancelamento VARCHAR(64),
    protocolo_inutilizacao VARCHAR(64),
    confidence_level VARCHAR(16) NOT NULL DEFAULT 'ALTA',
    homologado BOOLEAN NOT NULL DEFAULT TRUE,
    lineage JSONB NOT NULL DEFAULT '[]',
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_nfce_lineage (
    lineage_id SERIAL PRIMARY KEY,
    venda_codigo BIGINT,
    nfce_codigo BIGINT,
    situacao_fiscal VARCHAR(32),
    join_coverage_pct NUMERIC(8, 2),
    join_confidence VARCHAR(16),
    join_keys JSONB NOT NULL DEFAULT '[]',
    lineage JSONB NOT NULL DEFAULT '[]',
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_nfce_risk (
    risk_id SERIAL PRIMARY KEY,
    empresa_codigo INTEGER NOT NULL,
    risco VARCHAR(16) NOT NULL,
    cancelamentos INTEGER NOT NULL DEFAULT 0,
    ausencias INTEGER NOT NULL DEFAULT 0,
    divergencias INTEGER NOT NULL DEFAULT 0,
    lineage JSONB NOT NULL DEFAULT '[]',
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_nfce_reconciliation (
    reconciliation_id SERIAL PRIMARY KEY,
    vendas_total INTEGER NOT NULL DEFAULT 0,
    nfce_emitidas_total INTEGER NOT NULL DEFAULT 0,
    matched INTEGER NOT NULL DEFAULT 0,
    coverage_pct NUMERIC(8, 2),
    sem_nota INTEGER NOT NULL DEFAULT 0,
    duplicadas INTEGER NOT NULL DEFAULT 0,
    canceladas INTEGER NOT NULL DEFAULT 0,
    divergentes INTEGER NOT NULL DEFAULT 0,
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fact_nfce_catalog_empresa ON fact_nfce_catalog (empresa_codigo);
CREATE INDEX IF NOT EXISTS idx_fact_nfce_risk_level ON fact_nfce_risk (risco);
