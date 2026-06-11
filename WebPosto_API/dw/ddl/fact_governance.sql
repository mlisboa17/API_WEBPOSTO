-- fact_governance — F04.4
CREATE TABLE IF NOT EXISTS fact_governance (
    governance_sk               INTEGER PRIMARY KEY AUTOINCREMENT,
    date_sk                     INTEGER,
    employee_sk                 INTEGER,
    governance_band             TEXT NOT NULL,
    global_score                REAL NOT NULL DEFAULT 0,
    accountability_score        REAL NOT NULL DEFAULT 0,
    profitability_band          TEXT,
    primary_action              TEXT,
    loaded_at                   TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (employee_sk) REFERENCES dim_employee(employee_sk)
);
