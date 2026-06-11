-- fact_cash_risk — LOGOS SPACE DW F03
-- Grain: snapshot diário por entidade (rede / operador / pdv / turno)

CREATE TABLE IF NOT EXISTS fact_cash_risk (
    cash_risk_sk          INTEGER PRIMARY KEY AUTOINCREMENT,
    cash_date_sk          INTEGER NOT NULL,
    entity_type           TEXT NOT NULL,
    entity_id             TEXT NOT NULL,
    risk_score            REAL NOT NULL,
    risk_band             TEXT NOT NULL,
    peso_operador         REAL NOT NULL DEFAULT 0.40,
    peso_pdv              REAL NOT NULL DEFAULT 0.25,
    peso_turno            REAL NOT NULL DEFAULT 0.20,
    peso_historico        REAL NOT NULL DEFAULT 0.15,
    loaded_at             TEXT NOT NULL DEFAULT (datetime('now')),
    source_system         TEXT NOT NULL DEFAULT 'LOGOS_F03',
    FOREIGN KEY (cash_date_sk) REFERENCES dim_cash_date (cash_date_sk)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_fact_cash_risk_nk
    ON fact_cash_risk (cash_date_sk, entity_type, entity_id);
