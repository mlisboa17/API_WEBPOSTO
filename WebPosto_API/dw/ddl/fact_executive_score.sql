-- fact_executive_score — F04.7
CREATE TABLE IF NOT EXISTS fact_executive_score (
    score_id SERIAL PRIMARY KEY,
    executive_score NUMERIC(6, 2) NOT NULL,
    financial_score NUMERIC(6, 2),
    people_score NUMERIC(6, 2),
    operations_score NUMERIC(6, 2),
    growth_score NUMERIC(6, 2),
    risk_score NUMERIC(6, 2),
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    empresa_codigo INTEGER,
    evidence_json JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- fact_executive_alert — F04.7
CREATE TABLE IF NOT EXISTS fact_executive_alert (
    alert_id SERIAL PRIMARY KEY,
    severity VARCHAR(16) NOT NULL,
    category VARCHAR(32) NOT NULL,
    message TEXT,
    reference_json JSONB,
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- fact_executive_trend — F04.7
CREATE TABLE IF NOT EXISTS fact_executive_trend (
    trend_id SERIAL PRIMARY KEY,
    trend_type VARCHAR(32) NOT NULL,
    classification VARCHAR(16) NOT NULL,
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- fact_executive_snapshot — F04.7
CREATE TABLE IF NOT EXISTS fact_executive_snapshot (
    snapshot_id SERIAL PRIMARY KEY,
    payload_json JSONB NOT NULL,
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    empresa_codigo INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- dim_score_type — F04.7
CREATE TABLE IF NOT EXISTS dim_score_type (
    score_type_code VARCHAR(32) PRIMARY KEY,
    score_type_name VARCHAR(128) NOT NULL,
    weight NUMERIC(4, 2),
    sprint VARCHAR(16) DEFAULT 'F04.7'
);

INSERT INTO dim_score_type (score_type_code, score_type_name, weight) VALUES
    ('EXECUTIVE', 'Executive Score', 1.00),
    ('FINANCIAL', 'Financial Score', 0.30),
    ('PEOPLE', 'People Score', 0.25),
    ('OPERATIONS', 'Operations Score', 0.20),
    ('GROWTH', 'Growth Score', 0.15),
    ('RISK', 'Risk Score', 0.10)
ON CONFLICT (score_type_code) DO NOTHING;

-- dim_alert_type — F04.7
CREATE TABLE IF NOT EXISTS dim_alert_type (
    alert_type_code VARCHAR(32) PRIMARY KEY,
    alert_type_name VARCHAR(128) NOT NULL,
    default_severity VARCHAR(16)
);

INSERT INTO dim_alert_type (alert_type_code, alert_type_name, default_severity) VALUES
    ('FILIAL', 'Filial Crítica', 'CRITICO'),
    ('PDV', 'PDV Crítico', 'ALTO'),
    ('TURNO', 'Turno Crítico', 'ALTO'),
    ('OPERADOR', 'Operador Crítico', 'ATENCAO'),
    ('META', 'Meta Crítica', 'ATENCAO'),
    ('ROI', 'ROI Crítico', 'CRITICO'),
    ('RISCO', 'Risco Consolidado', 'CRITICO')
ON CONFLICT (alert_type_code) DO NOTHING;

-- dim_trend_type — F04.7
CREATE TABLE IF NOT EXISTS dim_trend_type (
    trend_type_code VARCHAR(32) PRIMARY KEY,
    trend_type_name VARCHAR(128) NOT NULL
);

INSERT INTO dim_trend_type (trend_type_code, trend_type_name) VALUES
    ('RECEITA', 'Tendência Receita'),
    ('ROI', 'Tendência ROI'),
    ('PERDAS', 'Tendência Perdas'),
    ('ACCOUNTABILITY', 'Tendência Accountability'),
    ('METAS', 'Tendência Metas')
ON CONFLICT (trend_type_code) DO NOTHING;
