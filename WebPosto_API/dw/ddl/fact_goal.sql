-- fact_goal — F04.5
CREATE TABLE IF NOT EXISTS fact_goal (
    goal_sk                     INTEGER PRIMARY KEY AUTOINCREMENT,
    date_sk                     INTEGER,
    employee_sk                 INTEGER,
    goal_type                   TEXT NOT NULL,
    scope                       TEXT NOT NULL,
    target_value                REAL NOT NULL DEFAULT 0,
    unit                        TEXT,
    loaded_at                   TEXT NOT NULL DEFAULT (datetime('now'))
);
