-- fact_pdv_profitability — F04.3
CREATE TABLE IF NOT EXISTS fact_pdv_profitability (
    pdv_profitability_sk      INTEGER PRIMARY KEY AUTOINCREMENT,
    date_sk                   INTEGER,
    pdv_sk                    INTEGER,
    receita_bruta             REAL NOT NULL DEFAULT 0,
    destruicao_margem         REAL NOT NULL DEFAULT 0,
    margem_operacional        REAL NOT NULL DEFAULT 0,
    resultado_liquido         REAL NOT NULL DEFAULT 0,
    roi                       REAL NOT NULL DEFAULT 0,
    monitoramento_prioritario INTEGER NOT NULL DEFAULT 0,
    loaded_at                 TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (pdv_sk) REFERENCES dim_pdv(pdv_sk)
);
