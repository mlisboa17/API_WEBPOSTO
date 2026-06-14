-- F08.3 — Consolidado operacional do Financial Operations Center
CREATE TABLE IF NOT EXISTS fact_financial_operations_center (
    execution_id        UUID         NOT NULL,
    generated_at        TIMESTAMP    NOT NULL,
    health_score        SMALLINT,
    health_classification VARCHAR(16),
    scheduler_status    VARCHAR(16),
    recovery_status     VARCHAR(16),
    alert_count         INTEGER,
    critical_alerts     INTEGER,
    snapshot_count      INTEGER,
    empresa_codigo      VARCHAR(64),
    period_start        DATE,
    period_end          DATE,
    lineage             BOOLEAN      NOT NULL DEFAULT TRUE,
    source              VARCHAR(64)  NOT NULL DEFAULT 'operations_center',
    created_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (execution_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_fin_ops_center_generated
    ON fact_financial_operations_center (generated_at DESC);

CREATE INDEX IF NOT EXISTS idx_fact_fin_ops_center_health
    ON fact_financial_operations_center (health_score, critical_alerts);

COMMENT ON TABLE fact_financial_operations_center IS
    'F08.3 — telemetria consolidada do Financial Operations Center (snapshot-first)';
