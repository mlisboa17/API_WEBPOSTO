-- dim_company — LOGOS SPACE DW (F01.4-B)

CREATE TABLE IF NOT EXISTS dim_company (
    company_sk        INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id        TEXT NOT NULL,
    company_name      TEXT,
    rede_codigo       TEXT,
    ativo             INTEGER NOT NULL DEFAULT 1,
    valid_from        TEXT NOT NULL DEFAULT (datetime('now')),
    valid_to          TEXT,
    is_current        INTEGER NOT NULL DEFAULT 1,
    UNIQUE (company_id, is_current)
);

CREATE INDEX IF NOT EXISTS idx_dim_company_id ON dim_company (company_id);
