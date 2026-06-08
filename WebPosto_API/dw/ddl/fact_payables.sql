-- fact_payables — LOGOS SPACE DW (F01.4-B)
-- Granularidade: 1 linha por título a pagar (TITULO_PAGAR)

CREATE TABLE IF NOT EXISTS fact_payables (
    payable_sk            INTEGER PRIMARY KEY AUTOINCREMENT,
    payable_id            TEXT NOT NULL,
    date_sk               INTEGER NOT NULL,
    due_date_sk           INTEGER,
    company_sk            INTEGER NOT NULL,
    cost_center_sk        INTEGER,
    supplier_sk           INTEGER,
    valor                 REAL NOT NULL,
    saldo                 REAL,
    situacao              TEXT,
    vencimento            TEXT,
    loaded_at             TEXT NOT NULL DEFAULT (datetime('now')),
    source_system         TEXT NOT NULL DEFAULT 'WEBPOSTO',
    FOREIGN KEY (date_sk) REFERENCES dim_date (date_sk),
    FOREIGN KEY (company_sk) REFERENCES dim_company (company_sk),
    FOREIGN KEY (cost_center_sk) REFERENCES dim_cost_center (cost_center_sk),
    FOREIGN KEY (supplier_sk) REFERENCES dim_supplier (supplier_sk)
);

CREATE INDEX IF NOT EXISTS idx_fact_payables_company ON fact_payables (company_sk);
CREATE INDEX IF NOT EXISTS idx_fact_payables_due ON fact_payables (vencimento);
