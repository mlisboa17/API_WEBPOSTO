-- fact_cash_alert — LOGOS SPACE DW F03
-- Grain: alerta por fechamento (cash_closing_sk)

CREATE TABLE IF NOT EXISTS fact_cash_alert (
    cash_alert_sk         INTEGER PRIMARY KEY AUTOINCREMENT,
    cash_closing_sk       INTEGER NOT NULL,
    alert_level           TEXT NOT NULL,
    diferenca_absoluta    REAL NOT NULL DEFAULT 0,
    consecutivas_operador INTEGER NOT NULL DEFAULT 0,
    quebras_pdv_30d       INTEGER NOT NULL DEFAULT 0,
    motivo                TEXT,
    ativo                 INTEGER NOT NULL DEFAULT 1,
    generated_at          TEXT NOT NULL DEFAULT (datetime('now')),
    loaded_at             TEXT NOT NULL DEFAULT (datetime('now')),
    source_system         TEXT NOT NULL DEFAULT 'LOGOS_F03',
    FOREIGN KEY (cash_closing_sk) REFERENCES fact_cash_closing (cash_closing_sk)
);

CREATE INDEX IF NOT EXISTS idx_fact_cash_alert_level ON fact_cash_alert (alert_level, ativo);
