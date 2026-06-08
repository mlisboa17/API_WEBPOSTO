-- fact_supplier_bank — LOGOS SPACE DW (F01.4-C)
-- Granularidade: 1 movimento bancário com tipoPessoa fornecedor

CREATE TABLE IF NOT EXISTS fact_supplier_bank (
    supplier_bank_sk        INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_movement_id        TEXT NOT NULL,
    date_sk                 INTEGER NOT NULL,
    company_sk              INTEGER NOT NULL,
    supplier_sk             INTEGER,
    valor                   REAL NOT NULL,
    codigo_pessoa           TEXT,
    evidence                TEXT NOT NULL DEFAULT 'MOVIMENTO_CONTA',
    loaded_at               TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (supplier_sk) REFERENCES dim_supplier (supplier_sk)
);
