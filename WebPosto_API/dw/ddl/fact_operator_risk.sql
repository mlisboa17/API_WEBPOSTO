-- fact_operator_risk — F04.0
CREATE TABLE IF NOT EXISTS fact_operator_risk (
    risk_sk               INTEGER PRIMARY KEY AUTOINCREMENT,
    date_sk               INTEGER,
    employee_sk           INTEGER,
    operator_risk_score   REAL NOT NULL DEFAULT 0,
    risk_band             TEXT,
    component_quebra      REAL,
    component_desconto    REAL,
    component_recorrencia REAL,
    component_contexto    REAL,
    loaded_at             TEXT NOT NULL DEFAULT (datetime('now'))
);
