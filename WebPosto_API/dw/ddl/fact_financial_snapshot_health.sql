-- F08.0 / F08.1 — Saúde de snapshots financeiros homologados
CREATE TABLE IF NOT EXISTS fact_financial_snapshot_health (
    snapshot_key           VARCHAR(128) NOT NULL,
    snapshot_type          VARCHAR(64)  NOT NULL,
    period_start           DATE         NOT NULL,
    period_end             DATE         NOT NULL,
    source                 VARCHAR(64)  NOT NULL,
    generated_at           TIMESTAMP,
    health_score           SMALLINT,
    confidence_level       VARCHAR(8),
    age_hours              NUMERIC(10, 2),
    health_status          VARCHAR(16),
    record_count           INTEGER,
    lineage_preserved      BOOLEAN      NOT NULL DEFAULT TRUE,
    homologated            BOOLEAN      NOT NULL DEFAULT TRUE,
    circuit_status         VARCHAR(16)  NOT NULL DEFAULT 'CLOSED',
    resilience_source      VARCHAR(16),
    created_at             TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (snapshot_key, snapshot_type)
);

-- Compatibilidade F08.0 → F08.1 (colunas legadas renomeadas/adicionadas)
ALTER TABLE fact_financial_snapshot_health
    ADD COLUMN IF NOT EXISTS snapshot_type VARCHAR(64);
ALTER TABLE fact_financial_snapshot_health
    ADD COLUMN IF NOT EXISTS generated_at TIMESTAMP;
ALTER TABLE fact_financial_snapshot_health
    ADD COLUMN IF NOT EXISTS health_score SMALLINT;
ALTER TABLE fact_financial_snapshot_health
    ADD COLUMN IF NOT EXISTS confidence_level VARCHAR(8);
ALTER TABLE fact_financial_snapshot_health
    ADD COLUMN IF NOT EXISTS age_hours NUMERIC(10, 2);
ALTER TABLE fact_financial_snapshot_health
    ADD COLUMN IF NOT EXISTS health_status VARCHAR(16);
ALTER TABLE fact_financial_snapshot_health
    ADD COLUMN IF NOT EXISTS record_count INTEGER;

CREATE INDEX IF NOT EXISTS idx_fact_fin_snap_health_period
    ON fact_financial_snapshot_health (period_start, period_end);

CREATE INDEX IF NOT EXISTS idx_fact_fin_snap_health_status
    ON fact_financial_snapshot_health (health_status, confidence_level);

CREATE INDEX IF NOT EXISTS idx_fact_fin_snap_health_freshness
    ON fact_financial_snapshot_health (generated_at DESC, age_hours);

COMMENT ON TABLE fact_financial_snapshot_health IS
    'F08.1 — telemetria de saúde, freshness, cobertura e confiança dos snapshots financeiros';
