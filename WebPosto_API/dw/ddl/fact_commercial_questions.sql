-- F07.9 — Commercial Copilot Questions DW

CREATE TABLE IF NOT EXISTS fact_commercial_questions (
    question_id VARCHAR(64) PRIMARY KEY,
    domain VARCHAR(32) NOT NULL,
    question_text TEXT NOT NULL,
    homologada BOOLEAN NOT NULL DEFAULT TRUE,
    answer_text TEXT,
    confidence_level VARCHAR(16),
    evidence_source JSONB NOT NULL DEFAULT '[]',
    lineage JSONB NOT NULL DEFAULT '[]',
    empresa_codigo BIGINT,
    action_id VARCHAR(64),
    execution_id VARCHAR(96),
    outcome_id VARCHAR(96),
    data_inicial DATE,
    data_final DATE,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fact_commercial_questions_domain
    ON fact_commercial_questions (domain);
