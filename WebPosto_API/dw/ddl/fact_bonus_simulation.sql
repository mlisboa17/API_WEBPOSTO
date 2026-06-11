-- fact_bonus_simulation — F04.5
CREATE TABLE IF NOT EXISTS fact_bonus_simulation (
    bonus_sk                    INTEGER PRIMARY KEY AUTOINCREMENT,
    date_sk                     INTEGER,
    employee_sk                 INTEGER,
    elegivel                    INTEGER NOT NULL DEFAULT 0,
    bonus_sugerido              REAL NOT NULL DEFAULT 0,
    roi_esperado                REAL NOT NULL DEFAULT 0,
    risco_bloqueante            INTEGER NOT NULL DEFAULT 0,
    evidence_json               TEXT,
    loaded_at                   TEXT NOT NULL DEFAULT (datetime('now'))
);
