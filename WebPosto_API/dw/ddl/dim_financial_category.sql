-- dim_financial_category — LOGOS SPACE DW (F01.4-B)

CREATE TABLE IF NOT EXISTS dim_financial_category (
    financial_category_sk   INTEGER PRIMARY KEY AUTOINCREMENT,
    category_code           TEXT NOT NULL UNIQUE,
    category_name           TEXT NOT NULL,
    dre_line                TEXT,
    version                 TEXT NOT NULL DEFAULT 'V3',
    ativo                   INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_dim_fin_cat_dre ON dim_financial_category (dre_line);
