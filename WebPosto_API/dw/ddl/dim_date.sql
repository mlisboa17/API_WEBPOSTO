-- dim_date — LOGOS SPACE DW (F01.4-B)

CREATE TABLE IF NOT EXISTS dim_date (
    date_sk           INTEGER PRIMARY KEY,
    full_date         TEXT NOT NULL UNIQUE,
    year              INTEGER NOT NULL,
    quarter           INTEGER NOT NULL,
    month             INTEGER NOT NULL,
    day               INTEGER NOT NULL,
    day_of_week       INTEGER NOT NULL,
    day_name          TEXT NOT NULL,
    is_weekend        INTEGER NOT NULL DEFAULT 0,
    is_month_end      INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_dim_date_year_month ON dim_date (year, month);
