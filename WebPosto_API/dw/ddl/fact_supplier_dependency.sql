-- fact_supplier_dependency — LOGOS SPACE DW (F01.4-D)

CREATE TABLE IF NOT EXISTS fact_supplier_dependency (
    dependency_sk           INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_sk             INTEGER NOT NULL,
    company_sk              INTEGER,
    data_ano_mes            TEXT NOT NULL,
    supplier_share_pct      REAL NOT NULL,
    dependency_index        REAL NOT NULL,
    strategic_homologated   INTEGER NOT NULL DEFAULT 0,
    alert_suppressed        INTEGER NOT NULL DEFAULT 0,
    loaded_at               TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (supplier_sk) REFERENCES dim_supplier (supplier_sk)
);

CREATE INDEX IF NOT EXISTS idx_fact_supplier_dep_ym ON fact_supplier_dependency (data_ano_mes);
