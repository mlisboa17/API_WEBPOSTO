-- dim_supplier — LOGOS SPACE DW (F01.4-C MDM)
-- SCD Type 1 · deduplicação canônica via supplier_canonical_name

CREATE TABLE IF NOT EXISTS dim_supplier (
    supplier_sk                 INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id                 TEXT NOT NULL,
    supplier_code               TEXT,
    supplier_name               TEXT NOT NULL,
    supplier_canonical_name     TEXT NOT NULL,
    supplier_alias              TEXT,
    supplier_group              TEXT,
    supplier_document           TEXT,
    supplier_type               TEXT,
    ativo                       INTEGER NOT NULL DEFAULT 1,
    primeira_compra             TEXT,
    ultima_compra               TEXT,
    empresa_origem              TEXT,
    supplier_coverage_score     INTEGER CHECK (supplier_coverage_score >= 0 AND supplier_coverage_score <= 100),
    valid_from                  TEXT NOT NULL DEFAULT (datetime('now')),
    valid_to                    TEXT,
    is_current                  INTEGER NOT NULL DEFAULT 1,
    UNIQUE (supplier_canonical_name, is_current)
);

CREATE INDEX IF NOT EXISTS idx_dim_supplier_canonical ON dim_supplier (supplier_canonical_name);
CREATE INDEX IF NOT EXISTS idx_dim_supplier_code ON dim_supplier (supplier_code);
CREATE INDEX IF NOT EXISTS idx_dim_supplier_document ON dim_supplier (supplier_document);
