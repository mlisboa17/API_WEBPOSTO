-- fact_corporate_score — F05.0
CREATE TABLE IF NOT EXISTS fact_corporate_score (
    score_id SERIAL PRIMARY KEY,
    corporate_score NUMERIC(6, 2) NOT NULL,
    executive_score NUMERIC(6, 2),
    financial_score NUMERIC(6, 2),
    people_score NUMERIC(6, 2),
    operations_score NUMERIC(6, 2),
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    empresa_codigo INTEGER,
    evidence_json JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- fact_corporate_risk — F05.0
CREATE TABLE IF NOT EXISTS fact_corporate_risk (
    risk_id SERIAL PRIMARY KEY,
    risk_type VARCHAR(32) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    message TEXT,
    reference_json JSONB,
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- fact_corporate_opportunity — F05.0
CREATE TABLE IF NOT EXISTS fact_corporate_opportunity (
    opportunity_id SERIAL PRIMARY KEY,
    opportunity_type VARCHAR(32) NOT NULL,
    prioridade VARCHAR(16) NOT NULL,
    impacto_estimado NUMERIC(14, 2),
    roi_esperado NUMERIC(14, 2),
    potencial_capturavel NUMERIC(14, 2),
    reference_json JSONB,
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- fact_corporate_snapshot — F05.0
CREATE TABLE IF NOT EXISTS fact_corporate_snapshot (
    snapshot_id SERIAL PRIMARY KEY,
    payload_json JSONB NOT NULL,
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    empresa_codigo INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- dim_risk_type — F05.0
CREATE TABLE IF NOT EXISTS dim_risk_type (
    risk_type_code VARCHAR(32) PRIMARY KEY,
    risk_type_name VARCHAR(128) NOT NULL,
    default_severity VARCHAR(16)
);

INSERT INTO dim_risk_type (risk_type_code, risk_type_name, default_severity) VALUES
    ('FINANCEIRO', 'Risco Financeiro', 'ALTO'),
    ('OPERACIONAL', 'Risco Operacional', 'ALTO'),
    ('PESSOAS', 'Risco Pessoas', 'ATENCAO'),
    ('FILIAL', 'Risco Filial', 'CRITICO'),
    ('PDV', 'Risco PDV', 'ALTO'),
    ('TURNO', 'Risco Turno', 'ALTO')
ON CONFLICT (risk_type_code) DO NOTHING;

-- dim_opportunity_type — F05.0
CREATE TABLE IF NOT EXISTS dim_opportunity_type (
    opportunity_type_code VARCHAR(32) PRIMARY KEY,
    opportunity_type_name VARCHAR(128) NOT NULL
);

INSERT INTO dim_opportunity_type (opportunity_type_code, opportunity_type_name) VALUES
    ('FINANCEIRA', 'Oportunidade Financeira'),
    ('OPERACIONAL', 'Oportunidade Operacional'),
    ('PESSOAS', 'Oportunidade Pessoas'),
    ('COMERCIAL', 'Oportunidade Comercial')
ON CONFLICT (opportunity_type_code) DO NOTHING;

-- dim_corporate_metric — F05.0
CREATE TABLE IF NOT EXISTS dim_corporate_metric (
    metric_code VARCHAR(32) PRIMARY KEY,
    metric_name VARCHAR(128) NOT NULL,
    sprint VARCHAR(16) DEFAULT 'F05.0'
);

INSERT INTO dim_corporate_metric (metric_code, metric_name) VALUES
    ('CORPORATE_SCORE', 'Corporate Score'),
    ('EXECUTIVE_SCORE', 'Executive Score'),
    ('FINANCIAL_SCORE', 'Financial Score'),
    ('PEOPLE_SCORE', 'People Score'),
    ('OPERATIONS_SCORE', 'Operations Score')
ON CONFLICT (metric_code) DO NOTHING;
