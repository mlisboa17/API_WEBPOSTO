-- fact_supplier_strategy — LOGOS SPACE DW (F01.4-D)

CREATE TABLE IF NOT EXISTS fact_supplier_strategy (
    strategy_sk             INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_sk             INTEGER NOT NULL,
    data_ano_mes            TEXT NOT NULL,
    strategic_score         INTEGER NOT NULL,
    strategic_band          TEXT NOT NULL,
    supplier_strategic      INTEGER NOT NULL DEFAULT 0,
    volume_component        REAL,
    capilaridade_component  REAL,
    recorrencia_component   REAL,
    criticidade_component   REAL,
    loaded_at               TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (supplier_sk) REFERENCES dim_supplier (supplier_sk)
);

CREATE INDEX IF NOT EXISTS idx_fact_supplier_strategy_ym ON fact_supplier_strategy (data_ano_mes);
