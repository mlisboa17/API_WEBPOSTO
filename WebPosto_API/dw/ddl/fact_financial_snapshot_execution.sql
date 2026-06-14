-- F08.2 — Audit trail de execuções de snapshot financeiro
CREATE TABLE IF NOT EXISTS fact_financial_snapshot_execution (
    execution_id     UUID         NOT NULL,
    snapshot_type    VARCHAR(64)  NOT NULL,
    trigger_type     VARCHAR(32)  NOT NULL DEFAULT 'scheduler',
    started_at       TIMESTAMP    NOT NULL,
    finished_at      TIMESTAMP,
    success          BOOLEAN,
    duration_ms      INTEGER,
    record_count     INTEGER,
    source           VARCHAR(64),
    error_type       VARCHAR(64),
    lineage          BOOLEAN,
    created_at       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (execution_id, snapshot_type, started_at)
);

CREATE INDEX IF NOT EXISTS idx_fact_fin_snap_exec_started
    ON fact_financial_snapshot_execution (started_at DESC);

CREATE INDEX IF NOT EXISTS idx_fact_fin_snap_exec_type
    ON fact_financial_snapshot_execution (snapshot_type, success);

COMMENT ON TABLE fact_financial_snapshot_execution IS
    'F08.2 — auditoria de refresh automático de snapshots financeiros';
