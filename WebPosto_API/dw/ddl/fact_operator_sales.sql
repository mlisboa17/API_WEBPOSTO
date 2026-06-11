-- fact_operator_sales — F04.0
CREATE TABLE IF NOT EXISTS fact_operator_sales (
    sales_sk              INTEGER PRIMARY KEY AUTOINCREMENT,
    date_sk               INTEGER,
    employee_sk           INTEGER,
    pdv_sk                INTEGER,
    total_vendas          REAL NOT NULL DEFAULT 0,
    quantidade_vendas     INTEGER NOT NULL DEFAULT 0,
    ticket_medio          REAL NOT NULL DEFAULT 0,
    volume_combustivel    REAL NOT NULL DEFAULT 0,
    volume_conveniencia   REAL NOT NULL DEFAULT 0,
    loaded_at             TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (employee_sk) REFERENCES dim_employee(employee_sk)
);
