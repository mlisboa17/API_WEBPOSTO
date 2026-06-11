-- fact_operator_compliance — F04.1
CREATE TABLE IF NOT EXISTS fact_operator_compliance (
    compliance_sk         INTEGER PRIMARY KEY AUTOINCREMENT,
    date_sk               INTEGER,
    employee_sk           INTEGER,
    compliance_score      REAL NOT NULL DEFAULT 0,
    compliance_band       TEXT,
    total_desconto        REAL NOT NULL DEFAULT 0,
    cancelamentos         INTEGER NOT NULL DEFAULT 0,
    nfce_anomalias        INTEGER NOT NULL DEFAULT 0,
    loaded_at             TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (employee_sk) REFERENCES dim_employee(employee_sk)
);
