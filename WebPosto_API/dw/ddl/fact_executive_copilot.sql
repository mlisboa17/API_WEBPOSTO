-- F05.3 — Executive AI Copilot DW model

CREATE TABLE IF NOT EXISTS fact_copilot_question (
    question_id VARCHAR(64) PRIMARY KEY,
    texto TEXT NOT NULL,
    dominio VARCHAR(32),
    homologada BOOLEAN NOT NULL DEFAULT TRUE,
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    empresa_codigo INTEGER,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_copilot_answer (
    answer_id VARCHAR(64) PRIMARY KEY,
    question_id VARCHAR(64) NOT NULL REFERENCES fact_copilot_question(question_id),
    resposta TEXT NOT NULL,
    confidence_level VARCHAR(16) NOT NULL,
    evidence_source JSONB NOT NULL DEFAULT '[]',
    lineage JSONB NOT NULL DEFAULT '[]',
    blocked BOOLEAN NOT NULL DEFAULT FALSE,
    labels JSONB NOT NULL DEFAULT '[]',
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_copilot_recommendation (
    recommendation_id VARCHAR(64) PRIMARY KEY,
    decision_id VARCHAR(64),
    classificacao VARCHAR(16) NOT NULL,
    acao TEXT NOT NULL,
    responsavel VARCHAR(256),
    impacto NUMERIC(14, 2) NOT NULL DEFAULT 0,
    roi_estimado NUMERIC(14, 2),
    roi_realizado NUMERIC(14, 2),
    roi_label VARCHAR(32) NOT NULL,
    confidence_level VARCHAR(16) NOT NULL,
    evidence_source JSONB NOT NULL DEFAULT '{}',
    lineage JSONB NOT NULL DEFAULT '[]',
    labels JSONB NOT NULL DEFAULT '[]',
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_copilot_answer_question ON fact_copilot_answer (question_id);
CREATE INDEX IF NOT EXISTS idx_copilot_recommendation_class ON fact_copilot_recommendation (classificacao);
