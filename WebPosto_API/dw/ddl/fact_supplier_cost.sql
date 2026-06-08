-- fact_supplier_cost — LOGOS SPACE DW (F01.4-D)
-- Granularidade: Fornecedor × Plano × Centro × Filial × Valor

CREATE TABLE IF NOT EXISTS fact_supplier_cost (
    supplier_cost_sk        INTEGER PRIMARY KEY AUTOINCREMENT,
    date_sk                 INTEGER NOT NULL,
    company_sk              INTEGER NOT NULL,
    supplier_sk             INTEGER NOT NULL,
    account_sk              INTEGER,
    cost_center_sk          INTEGER,
    supplier_category_sk    INTEGER,
    data_ano_mes            TEXT NOT NULL,
    valor                   REAL NOT NULL,
    evidence                TEXT NOT NULL,
    loaded_at               TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (supplier_sk) REFERENCES dim_supplier (supplier_sk),
    FOREIGN KEY (supplier_category_sk) REFERENCES dim_supplier_category (supplier_category_sk)
);

CREATE INDEX IF NOT EXISTS idx_fact_supplier_cost_ym ON fact_supplier_cost (data_ano_mes);
CREATE INDEX IF NOT EXISTS idx_fact_supplier_cost_company ON fact_supplier_cost (company_sk);
