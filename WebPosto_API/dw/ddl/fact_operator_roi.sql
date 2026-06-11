-- fact_operator_roi — F04.2
CREATE TABLE IF NOT EXISTS fact_operator_roi (
    roi_sk                INTEGER PRIMARY KEY AUTOINCREMENT,
    date_sk               INTEGER,
    employee_sk           INTEGER,
    resultado_liquido     REAL NOT NULL DEFAULT 0,
    risco_economico       REAL NOT NULL DEFAULT 0,
    roi                   REAL NOT NULL DEFAULT 0,
    roi_pct               REAL NOT NULL DEFAULT 0,
    retorno_por_venda     REAL NOT NULL DEFAULT 0,
    loaded_at             TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (employee_sk) REFERENCES dim_employee(employee_sk)
);
