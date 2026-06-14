-- F08.4 — Telemetria do Financial Intelligence Center
CREATE TABLE IF NOT EXISTS fact_financial_intelligence (
    execution_id        UUID         NOT NULL,
    generated_at        TIMESTAMP    NOT NULL,
    empresa_codigo      VARCHAR(64),
    financial_score     SMALLINT,
    risk_level          VARCHAR(16),
    trend               VARCHAR(16),
    opportunity_count   INTEGER,
    cash_flow_health    VARCHAR(16),
    period_start        DATE,
    period_end          DATE,
    lineage             BOOLEAN      NOT NULL DEFAULT TRUE,
    source              VARCHAR(64)  NOT NULL DEFAULT 'financial_intelligence_center',
    created_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (execution_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_fin_intelligence_generated
    ON fact_financial_intelligence (generated_at DESC);

CREATE INDEX IF NOT EXISTS idx_fact_fin_intelligence_score
    ON fact_financial_intelligence (financial_score, risk_level);

COMMENT ON TABLE fact_financial_intelligence IS
    'F08.4 — inteligência financeira executiva auditável (snapshot-first)';
