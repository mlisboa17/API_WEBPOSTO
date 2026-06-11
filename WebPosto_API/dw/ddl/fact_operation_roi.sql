-- fact_operation_roi — F04.3
CREATE TABLE IF NOT EXISTS fact_operation_roi (
    operation_roi_sk          INTEGER PRIMARY KEY AUTOINCREMENT,
    date_sk                   INTEGER,
    pdv_sk                    INTEGER,
    turn_sk                   INTEGER,
    employee_sk               INTEGER,
    receita_bruta             REAL NOT NULL DEFAULT 0,
    resultado_liquido         REAL NOT NULL DEFAULT 0,
    risco_economico           REAL NOT NULL DEFAULT 0,
    roi                       REAL NOT NULL DEFAULT 0,
    operation_score           REAL NOT NULL DEFAULT 0,
    operation_band            TEXT,
    primary_action            TEXT,
    loaded_at                 TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (pdv_sk) REFERENCES dim_pdv(pdv_sk),
    FOREIGN KEY (turn_sk) REFERENCES dim_turn(turn_sk),
    FOREIGN KEY (employee_sk) REFERENCES dim_employee(employee_sk)
);
