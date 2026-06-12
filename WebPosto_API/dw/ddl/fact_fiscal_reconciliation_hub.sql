-- F06.4 — Fiscal Reconciliation Hub DW model

CREATE TABLE IF NOT EXISTS fact_fiscal_reconciliation (
    reconciliation_id SERIAL PRIMARY KEY,
    dominio VARCHAR(32) NOT NULL,
    vendas_total INT,
    matched INT,
    coverage_pct NUMERIC(8, 2),
    divergentes INT,
    cancelamentos INT,
    litros_vendidos NUMERIC(14, 3),
    litros_lmc NUMERIC(14, 3),
    litros_sem_lmc NUMERIC(14, 3),
    lineage JSONB NOT NULL DEFAULT '[]',
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_fiscal_lineage (
    lineage_id VARCHAR(64) PRIMARY KEY,
    empresa_codigo BIGINT,
    venda_codigo BIGINT,
    venda_item_codigo BIGINT,
    produto_codigo BIGINT,
    nfce_codigo BIGINT,
    lmc_codigo BIGINT,
    conta_codigo BIGINT,
    plano_conta_gerencial_codigo BIGINT,
    lineage JSONB NOT NULL DEFAULT '[]',
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_fiscal_risk_consolidated (
    risk_id SERIAL PRIMARY KEY,
    dominio VARCHAR(32) NOT NULL,
    empresa_codigo BIGINT,
    produto_codigo BIGINT,
    risco VARCHAR(16) NOT NULL,
    quantidade NUMERIC(14, 3),
    litros_sem_lmc NUMERIC(14, 3),
    lineage JSONB NOT NULL DEFAULT '[]',
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_fiscal_financial_bridge (
    bridge_id SERIAL PRIMARY KEY,
    dre_fiscal_viavel BOOLEAN,
    classificacao_gerencial_viavel BOOLEAN,
    centro_custo_disponivel BOOLEAN,
    centro_custo_blocked_401 BOOLEAN,
    conta_registros INT,
    plano_conta_registros INT,
    lineage JSONB NOT NULL DEFAULT '[]',
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
