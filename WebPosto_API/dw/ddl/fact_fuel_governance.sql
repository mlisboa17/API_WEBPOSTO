-- F06.5 — Fuel Governance DW model

CREATE TABLE IF NOT EXISTS fact_lmc_compliance (
    compliance_id VARCHAR(64) PRIMARY KEY,
    data DATE NOT NULL,
    empresa_codigo BIGINT NOT NULL,
    nome_filial VARCHAR(128),
    registros_lmc INT NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL,
    preenchido_por VARCHAR(128),
    lineage JSONB NOT NULL DEFAULT '[]',
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_lmc_delay (
    delay_id SERIAL PRIMARY KEY,
    empresa_codigo BIGINT,
    data_movimento DATE,
    tipo VARCHAR(32) NOT NULL,
    atraso_dias INT,
    preenchido_por VARCHAR(128),
    lineage JSONB NOT NULL DEFAULT '[]',
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_fuel_governance (
    governance_id SERIAL PRIMARY KEY,
    problema_principal VARCHAR(256),
    tecnologia_vs_rotina VARCHAR(32),
    sem_fraude_presumida BOOLEAN NOT NULL DEFAULT TRUE,
    sem_perda_presumida BOOLEAN NOT NULL DEFAULT TRUE,
    causas JSONB NOT NULL DEFAULT '[]',
    lineage JSONB NOT NULL DEFAULT '[]',
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_branch_compliance (
    branch_id SERIAL PRIMARY KEY,
    empresa_codigo BIGINT NOT NULL,
    nome_filial VARCHAR(128),
    dias_com_lmc INT NOT NULL,
    dias_esperados INT NOT NULL,
    conformidade_pct NUMERIC(8, 2) NOT NULL,
    disciplina VARCHAR(32) NOT NULL,
    preenchido_por JSONB NOT NULL DEFAULT '[]',
    lineage JSONB NOT NULL DEFAULT '[]',
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
