-- fact_supplier_payable — LOGOS SPACE DW (F01.4-C)
-- Granularidade: 1 título a pagar (TITULO_PAGAR)

CREATE TABLE IF NOT EXISTS fact_supplier_payable (
    supplier_payable_sk     INTEGER PRIMARY KEY AUTOINCREMENT,
    payable_id              TEXT NOT NULL,
    date_sk                 INTEGER NOT NULL,
    due_date_sk             INTEGER,
    company_sk              INTEGER NOT NULL,
    supplier_sk             INTEGER NOT NULL,
    cost_center_sk          INTEGER,
    valor                   REAL NOT NULL,
    fornecedor_codigo       TEXT,
    cpf_cnpj_fornecedor     TEXT,
    evidence                TEXT NOT NULL DEFAULT 'TITULO_PAGAR',
    loaded_at               TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (supplier_sk) REFERENCES dim_supplier (supplier_sk),
    FOREIGN KEY (company_sk) REFERENCES dim_company (company_sk)
);

CREATE INDEX IF NOT EXISTS idx_fact_supplier_payable_supplier ON fact_supplier_payable (supplier_sk);
