-- fact_operator_accountability — F04.0
CREATE TABLE IF NOT EXISTS fact_operator_accountability (
    accountability_sk     INTEGER PRIMARY KEY AUTOINCREMENT,
    date_sk               INTEGER,
    employee_sk           INTEGER,
    saldo_operacional     REAL NOT NULL DEFAULT 0,
    diferenca_acumulada   REAL,
    compensado_automatico REAL NOT NULL DEFAULT 0,
    loaded_at             TEXT NOT NULL DEFAULT (datetime('now'))
);
