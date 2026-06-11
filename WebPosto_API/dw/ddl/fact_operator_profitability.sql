-- fact_operator_profitability — F04.2
CREATE TABLE IF NOT EXISTS fact_operator_profitability (
    profitability_sk          INTEGER PRIMARY KEY AUTOINCREMENT,
    date_sk                   INTEGER,
    employee_sk               INTEGER,
    receita_bruta             REAL NOT NULL DEFAULT 0,
    destruicao_margem         REAL NOT NULL DEFAULT 0,
    margem_operacional        REAL NOT NULL DEFAULT 0,
    profitability_score       REAL NOT NULL DEFAULT 0,
    profitability_adjusted    REAL NOT NULL DEFAULT 0,
    profitability_band        TEXT,
    loaded_at                 TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (employee_sk) REFERENCES dim_employee(employee_sk)
);
