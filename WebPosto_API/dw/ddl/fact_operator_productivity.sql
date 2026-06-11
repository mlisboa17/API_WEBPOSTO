-- fact_operator_productivity — F04.0
CREATE TABLE IF NOT EXISTS fact_operator_productivity (
    productivity_sk       INTEGER PRIMARY KEY AUTOINCREMENT,
    date_sk               INTEGER,
    employee_sk           INTEGER,
    productivity_score    REAL NOT NULL DEFAULT 0,
    productivity_band     TEXT,
    abastecimentos        INTEGER NOT NULL DEFAULT 0,
    itens_vendidos        INTEGER NOT NULL DEFAULT 0,
    loaded_at             TEXT NOT NULL DEFAULT (datetime('now'))
);
