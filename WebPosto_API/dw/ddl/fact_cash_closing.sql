-- fact_cash_closing — LOGOS SPACE DW F03
-- Grain: caixaCodigo + dataMovimento + empresaCodigo

CREATE TABLE IF NOT EXISTS fact_cash_closing (
    cash_closing_sk       INTEGER PRIMARY KEY AUTOINCREMENT,
    caixa_codigo          INTEGER NOT NULL,
    empresa_codigo        INTEGER NOT NULL,
    cash_date_sk          INTEGER NOT NULL,
    operator_sk           INTEGER,
    pdv_sk                INTEGER,
    turn_sk               INTEGER,
    abertura_ts           TEXT,
    fechamento_ts         TEXT,
    apurado               REAL NOT NULL DEFAULT 0,
    diferenca             REAL NOT NULL DEFAULT 0,
    fechado               INTEGER,
    consolidado           INTEGER,
    loaded_at             TEXT NOT NULL DEFAULT (datetime('now')),
    source_system         TEXT NOT NULL DEFAULT 'WEBPOSTO',
    FOREIGN KEY (cash_date_sk) REFERENCES dim_cash_date (cash_date_sk),
    FOREIGN KEY (operator_sk) REFERENCES dim_operator (operator_sk),
    FOREIGN KEY (pdv_sk) REFERENCES dim_pdv (pdv_sk),
    FOREIGN KEY (turn_sk) REFERENCES dim_turn (turn_sk)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_fact_cash_closing_nk
    ON fact_cash_closing (caixa_codigo, empresa_codigo, cash_date_sk);
CREATE INDEX IF NOT EXISTS idx_fact_cash_closing_date ON fact_cash_closing (cash_date_sk);
CREATE INDEX IF NOT EXISTS idx_fact_cash_closing_operator ON fact_cash_closing (operator_sk);
CREATE INDEX IF NOT EXISTS idx_fact_cash_closing_pdv ON fact_cash_closing (pdv_sk);
