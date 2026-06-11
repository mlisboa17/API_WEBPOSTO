-- fact_shift_profitability — F04.3
CREATE TABLE IF NOT EXISTS fact_shift_profitability (
    shift_profitability_sk    INTEGER PRIMARY KEY AUTOINCREMENT,
    date_sk                   INTEGER,
    turn_sk                   INTEGER,
    receita_bruta             REAL NOT NULL DEFAULT 0,
    destruicao_margem         REAL NOT NULL DEFAULT 0,
    margem_operacional        REAL NOT NULL DEFAULT 0,
    resultado_liquido         REAL NOT NULL DEFAULT 0,
    roi                       REAL NOT NULL DEFAULT 0,
    shift_risk_score          REAL NOT NULL DEFAULT 0,
    loaded_at                 TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (turn_sk) REFERENCES dim_turn(turn_sk)
);
