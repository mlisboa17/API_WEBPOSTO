-- fact_management_action — F04.4
CREATE TABLE IF NOT EXISTS fact_management_action (
    action_sk                   INTEGER PRIMARY KEY AUTOINCREMENT,
    date_sk                     INTEGER,
    employee_sk                 INTEGER,
    primary_action              TEXT NOT NULL,
    recommended_actions         TEXT,
    global_score                REAL NOT NULL DEFAULT 0,
    accountability_score        REAL NOT NULL DEFAULT 0,
    roi_norm                    REAL NOT NULL DEFAULT 0,
    risk_score                  REAL NOT NULL DEFAULT 0,
    evidence_json               TEXT,
    loaded_at                   TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (employee_sk) REFERENCES dim_employee(employee_sk)
);
