-- fact_expense_v2 — LOGOS SPACE DW (F01.4-B)
-- Granularidade: 1 linha por lançamento de despesa gerencial (DESPESAS_REDE)
-- Particionamento sugerido: data_lancamento (mensal) na A04

CREATE TABLE IF NOT EXISTS fact_expense_v2 (
    expense_sk                INTEGER PRIMARY KEY AUTOINCREMENT,
    expense_id                TEXT NOT NULL,
    date_sk                   INTEGER NOT NULL,
    company_sk                INTEGER NOT NULL,
    account_sk                INTEGER,
    cost_center_sk            INTEGER,
    supplier_sk               INTEGER,
    financial_category_sk     INTEGER,
    data_lancamento           TEXT NOT NULL,
    valor                     REAL NOT NULL,
    descricao                 TEXT,
    plano_conta_gerencial_id  INTEGER,
    centro_custo_codigo       TEXT,
    categoria_logos_v3        TEXT,
    classification_source     TEXT,
    confidence_score_v3       REAL CHECK (confidence_score_v3 >= 0.0 AND confidence_score_v3 <= 1.0),
    apura_dre                 TEXT,
    loaded_at                 TEXT NOT NULL DEFAULT (datetime('now')),
    source_system             TEXT NOT NULL DEFAULT 'WEBPOSTO',
    FOREIGN KEY (date_sk) REFERENCES dim_date (date_sk),
    FOREIGN KEY (company_sk) REFERENCES dim_company (company_sk),
    FOREIGN KEY (account_sk) REFERENCES dim_account (account_sk),
    FOREIGN KEY (cost_center_sk) REFERENCES dim_cost_center (cost_center_sk),
    FOREIGN KEY (supplier_sk) REFERENCES dim_supplier (supplier_sk),
    FOREIGN KEY (financial_category_sk) REFERENCES dim_financial_category (financial_category_sk)
);

CREATE INDEX IF NOT EXISTS idx_fact_expense_v2_date ON fact_expense_v2 (data_lancamento);
CREATE INDEX IF NOT EXISTS idx_fact_expense_v2_company ON fact_expense_v2 (company_sk);
CREATE INDEX IF NOT EXISTS idx_fact_expense_v2_account ON fact_expense_v2 (account_sk);
CREATE INDEX IF NOT EXISTS idx_fact_expense_v2_category ON fact_expense_v2 (categoria_logos_v3);
