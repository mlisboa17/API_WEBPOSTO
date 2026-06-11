-- fact_training — F04.4
CREATE TABLE IF NOT EXISTS fact_training (
    training_sk                 INTEGER PRIMARY KEY AUTOINCREMENT,
    date_sk                     INTEGER,
    employee_sk                 INTEGER,
    training_categories         TEXT,
    evidence_json               TEXT,
    loaded_at                   TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (employee_sk) REFERENCES dim_employee(employee_sk)
);
