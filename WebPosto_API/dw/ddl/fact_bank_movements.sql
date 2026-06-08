-- fact_bank_movements — LOGOS SPACE DW (F01.4-B)
-- Granularidade: 1 linha por movimento bancário (MOVIMENTO_CONTA)

CREATE TABLE IF NOT EXISTS fact_bank_movements (
    bank_movement_sk          INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_movement_id          TEXT NOT NULL,
    date_sk                   INTEGER NOT NULL,
    company_sk                INTEGER NOT NULL,
    account_sk                INTEGER,
    cost_center_sk            INTEGER,
    valor                     REAL NOT NULL,
    plano_conta_gerencial_id  INTEGER,
    descricao                 TEXT,
    loaded_at                 TEXT NOT NULL DEFAULT (datetime('now')),
    source_system             TEXT NOT NULL DEFAULT 'WEBPOSTO',
    FOREIGN KEY (date_sk) REFERENCES dim_date (date_sk),
    FOREIGN KEY (company_sk) REFERENCES dim_company (company_sk),
    FOREIGN KEY (account_sk) REFERENCES dim_account (account_sk),
    FOREIGN KEY (cost_center_sk) REFERENCES dim_cost_center (cost_center_sk)
);

CREATE INDEX IF NOT EXISTS idx_fact_bank_company ON fact_bank_movements (company_sk);
