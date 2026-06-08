-- fact_cash — LOGOS SPACE DW (F01.4-B)
-- Granularidade: 1 linha por movimento de caixa (CAIXA)

CREATE TABLE IF NOT EXISTS fact_cash (
    cash_sk               INTEGER PRIMARY KEY AUTOINCREMENT,
    cash_id               TEXT NOT NULL,
    date_sk               INTEGER NOT NULL,
    company_sk            INTEGER NOT NULL,
    valor                 REAL NOT NULL,
    tipo_movimento        TEXT,
    descricao             TEXT,
    loaded_at             TEXT NOT NULL DEFAULT (datetime('now')),
    source_system         TEXT NOT NULL DEFAULT 'WEBPOSTO',
    FOREIGN KEY (date_sk) REFERENCES dim_date (date_sk),
    FOREIGN KEY (company_sk) REFERENCES dim_company (company_sk)
);

CREATE INDEX IF NOT EXISTS idx_fact_cash_date ON fact_cash (date_sk);
