-- fact_receivables — LOGOS SPACE DW (F01.4-B)
-- Granularidade: 1 linha por título a receber (TITULO_RECEBER)

CREATE TABLE IF NOT EXISTS fact_receivables (
    receivable_sk         INTEGER PRIMARY KEY AUTOINCREMENT,
    receivable_id         TEXT NOT NULL,
    date_sk               INTEGER NOT NULL,
    due_date_sk           INTEGER,
    company_sk            INTEGER NOT NULL,
    customer_sk           INTEGER,
    valor                 REAL NOT NULL,
    saldo                 REAL,
    situacao              TEXT,
    vencimento            TEXT,
    loaded_at             TEXT NOT NULL DEFAULT (datetime('now')),
    source_system         TEXT NOT NULL DEFAULT 'WEBPOSTO',
    FOREIGN KEY (date_sk) REFERENCES dim_date (date_sk),
    FOREIGN KEY (company_sk) REFERENCES dim_company (company_sk)
);

CREATE INDEX IF NOT EXISTS idx_fact_receivables_company ON fact_receivables (company_sk);
