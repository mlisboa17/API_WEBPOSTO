-- fact_operator_management_action — F04.2
CREATE TABLE IF NOT EXISTS fact_operator_management_action (
    action_sk             INTEGER PRIMARY KEY AUTOINCREMENT,
    date_sk               INTEGER,
    employee_sk           INTEGER,
    primary_action        TEXT,
    management_actions    TEXT,
    profitability_score   REAL NOT NULL DEFAULT 0,
    roi                   REAL,
    loaded_at             TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (employee_sk) REFERENCES dim_employee(employee_sk)
);
