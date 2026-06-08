-- fact_supplier_purchase — LOGOS SPACE DW (F01.4-C)
-- Status: Future Ready — bloqueado por COMPRA_REDE/NOTA_ENTRADA HTTP 401

CREATE TABLE IF NOT EXISTS fact_supplier_purchase (
    supplier_purchase_sk    INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_id             TEXT NOT NULL,
    date_sk                 INTEGER NOT NULL,
    company_sk              INTEGER NOT NULL,
    supplier_sk             INTEGER NOT NULL,
    valor                   REAL NOT NULL,
    nota_entrada_codigo     TEXT,
    status_carga            TEXT NOT NULL DEFAULT 'FUTURE_READY',
    bloqueio                TEXT NOT NULL DEFAULT 'COMPRA_REDE_401',
    loaded_at               TEXT,
    FOREIGN KEY (supplier_sk) REFERENCES dim_supplier (supplier_sk)
);
