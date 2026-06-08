-- dim_supplier_category — LOGOS SPACE DW (F01.4-D)

CREATE TABLE IF NOT EXISTS dim_supplier_category (
    supplier_category_sk    INTEGER PRIMARY KEY AUTOINCREMENT,
    category_code           TEXT NOT NULL UNIQUE,
    category_name           TEXT NOT NULL,
    subcategory_code        TEXT,
    subcategory_name        TEXT,
    strategic_default       INTEGER NOT NULL DEFAULT 0,
    ativo                   INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_dim_supplier_cat_sub ON dim_supplier_category (subcategory_code);
