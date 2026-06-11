-- fact_operator_sales_score — F04.1
CREATE TABLE IF NOT EXISTS fact_operator_sales_score (
    sales_score_sk        INTEGER PRIMARY KEY AUTOINCREMENT,
    date_sk               INTEGER,
    employee_sk           INTEGER,
    sales_score           REAL NOT NULL DEFAULT 0,
    sales_band            TEXT,
    quantidade_vendas     INTEGER NOT NULL DEFAULT 0,
    total_vendas          REAL NOT NULL DEFAULT 0,
    ticket_medio          REAL NOT NULL DEFAULT 0,
    volume_combustivel    REAL NOT NULL DEFAULT 0,
    volume_conveniencia   REAL NOT NULL DEFAULT 0,
    loaded_at             TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (employee_sk) REFERENCES dim_employee(employee_sk)
);
