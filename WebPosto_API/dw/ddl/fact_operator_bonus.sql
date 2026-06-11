-- fact_operator_bonus — F04.1
CREATE TABLE IF NOT EXISTS fact_operator_bonus (
    bonus_sk              INTEGER PRIMARY KEY AUTOINCREMENT,
    date_sk               INTEGER,
    employee_sk           INTEGER,
    global_score          REAL NOT NULL DEFAULT 0,
    global_classification TEXT,
    bonus_eligibility     TEXT,
    context_adjusted_score REAL NOT NULL DEFAULT 0,
    loaded_at             TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (employee_sk) REFERENCES dim_employee(employee_sk)
);
