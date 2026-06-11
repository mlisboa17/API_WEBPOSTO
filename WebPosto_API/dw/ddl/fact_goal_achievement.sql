-- fact_goal_achievement — F04.5
CREATE TABLE IF NOT EXISTS fact_goal_achievement (
    achievement_sk              INTEGER PRIMARY KEY AUTOINCREMENT,
    date_sk                       INTEGER,
    employee_sk                   INTEGER,
    goal_type                     TEXT NOT NULL,
    realizado                     REAL NOT NULL DEFAULT 0,
    meta                          REAL NOT NULL DEFAULT 0,
    percentual_atingido           REAL NOT NULL DEFAULT 0,
    gap                           REAL NOT NULL DEFAULT 0,
    status                        TEXT,
    loaded_at                     TEXT NOT NULL DEFAULT (datetime('now'))
);
