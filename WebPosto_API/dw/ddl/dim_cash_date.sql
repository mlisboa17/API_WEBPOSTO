-- dim_cash_date — LOGOS SPACE DW F03
CREATE TABLE IF NOT EXISTS dim_cash_date (
    cash_date_sk          INTEGER PRIMARY KEY AUTOINCREMENT,
    date_sk               INTEGER NOT NULL,
    data_movimento        TEXT NOT NULL UNIQUE,
    dia_semana            INTEGER,
    semana_ano            INTEGER,
    mes                   INTEGER,
    ano                   INTEGER,
    loaded_at             TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (date_sk) REFERENCES dim_date (date_sk)
);

CREATE INDEX IF NOT EXISTS idx_dim_cash_date_mov ON dim_cash_date (data_movimento);
