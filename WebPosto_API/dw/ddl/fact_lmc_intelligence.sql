-- F06.2 — LMC Intelligence DW model

CREATE TABLE IF NOT EXISTS fact_lmc (
    lmc_id VARCHAR(64) PRIMARY KEY,
    lmc_codigo BIGINT,
    empresa_codigo INTEGER NOT NULL,
    produto_codigo BIGINT,
    data_movimento DATE,
    abertura NUMERIC(14, 3),
    entrada NUMERIC(14, 3) NOT NULL DEFAULT 0,
    saida NUMERIC(14, 3) NOT NULL DEFAULT 0,
    perda_sobra NUMERIC(14, 3) NOT NULL DEFAULT 0,
    escritural NUMERIC(14, 3),
    fechamento NUMERIC(14, 3),
    preco_custo NUMERIC(14, 4),
    confidence_level VARCHAR(16) NOT NULL DEFAULT 'ALTA',
    homologado BOOLEAN NOT NULL DEFAULT TRUE,
    lineage JSONB NOT NULL DEFAULT '[]',
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_lmc_loss (
    loss_id SERIAL PRIMARY KEY,
    empresa_codigo INTEGER NOT NULL,
    perda_operacional NUMERIC(14, 3) NOT NULL DEFAULT 0,
    indice_perda NUMERIC(8, 2),
    banda VARCHAR(16) NOT NULL,
    lineage JSONB NOT NULL DEFAULT '[]',
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_lmc_surplus (
    surplus_id SERIAL PRIMARY KEY,
    empresa_codigo INTEGER,
    sobra_operacional NUMERIC(14, 3) NOT NULL DEFAULT 0,
    sobra_total NUMERIC(14, 3) NOT NULL DEFAULT 0,
    banda VARCHAR(16),
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_lmc_reconciliation (
    reconciliation_id SERIAL PRIMARY KEY,
    abastecimento_total INTEGER NOT NULL DEFAULT 0,
    abastecimento_matched INTEGER NOT NULL DEFAULT 0,
    lmc_registros INTEGER NOT NULL DEFAULT 0,
    venda_litros NUMERIC(14, 3) NOT NULL DEFAULT 0,
    lmc_saida_litros NUMERIC(14, 3) NOT NULL DEFAULT 0,
    coverage_abast_venda_item_pct NUMERIC(8, 2),
    divergentes INTEGER NOT NULL DEFAULT 0,
    confiavel BOOLEAN NOT NULL DEFAULT FALSE,
    lineage JSONB NOT NULL DEFAULT '[]',
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fact_lmc_empresa ON fact_lmc (empresa_codigo);
CREATE INDEX IF NOT EXISTS idx_fact_lmc_loss_banda ON fact_lmc_loss (banda);
