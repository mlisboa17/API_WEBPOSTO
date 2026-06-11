-- fact_bonus — F04.4
CREATE TABLE IF NOT EXISTS fact_bonus (
    bonus_sk                    INTEGER PRIMARY KEY AUTOINCREMENT,
    date_sk                     INTEGER,
    employee_sk                 INTEGER,
    bonus_recomendado           REAL NOT NULL DEFAULT 0,
    resultado_liquido           REAL NOT NULL DEFAULT 0,
    bonus_roi_esperado          REAL NOT NULL DEFAULT 0,
    loaded_at                   TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (employee_sk) REFERENCES dim_employee(employee_sk)
);
