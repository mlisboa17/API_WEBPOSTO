-- fact_operator_discount — F04.0
CREATE TABLE IF NOT EXISTS fact_operator_discount (
    discount_sk           INTEGER PRIMARY KEY AUTOINCREMENT,
    date_sk               INTEGER,
    employee_sk           INTEGER,
    pdv_sk                INTEGER,
    total_desconto        REAL NOT NULL DEFAULT 0,
    eventos_desconto      INTEGER NOT NULL DEFAULT 0,
    loaded_at             TEXT NOT NULL DEFAULT (datetime('now'))
);
