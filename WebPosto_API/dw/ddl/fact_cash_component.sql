-- fact_cash_component — LOGOS SPACE DW F03
-- Grain: cash_closing_sk + component_code

CREATE TABLE IF NOT EXISTS fact_cash_component (
    cash_component_sk     INTEGER PRIMARY KEY AUTOINCREMENT,
    cash_closing_sk       INTEGER NOT NULL,
    component_code        TEXT NOT NULL,
    component_label       TEXT,
    apresentado           REAL NOT NULL DEFAULT 0,
    apurado               REAL NOT NULL DEFAULT 0,
    diferenca             REAL NOT NULL DEFAULT 0,
    loaded_at             TEXT NOT NULL DEFAULT (datetime('now')),
    source_system         TEXT NOT NULL DEFAULT 'WEBPOSTO',
    FOREIGN KEY (cash_closing_sk) REFERENCES fact_cash_closing (cash_closing_sk)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_fact_cash_component_nk
    ON fact_cash_component (cash_closing_sk, component_code);
