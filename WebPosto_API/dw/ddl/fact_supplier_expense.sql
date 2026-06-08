-- fact_supplier_expense — LOGOS SPACE DW (F01.4-C)
-- Granularidade: 1 despesa com fornecedor identificado (DESPESAS_REDE desc ou TITULO_PAGAR)

CREATE TABLE IF NOT EXISTS fact_supplier_expense (
    supplier_expense_sk     INTEGER PRIMARY KEY AUTOINCREMENT,
    expense_id              TEXT,
    date_sk                 INTEGER NOT NULL,
    company_sk              INTEGER NOT NULL,
    supplier_sk             INTEGER NOT NULL,
    account_sk              INTEGER,
    valor                   REAL NOT NULL,
    source_system           TEXT NOT NULL,
    evidence                TEXT NOT NULL,
    loaded_at               TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (date_sk) REFERENCES dim_date (date_sk),
    FOREIGN KEY (company_sk) REFERENCES dim_company (company_sk),
    FOREIGN KEY (supplier_sk) REFERENCES dim_supplier (supplier_sk)
);

CREATE INDEX IF NOT EXISTS idx_fact_supplier_expense_supplier ON fact_supplier_expense (supplier_sk);
