-- dim_pdv — LOGOS SPACE DW F03
CREATE TABLE IF NOT EXISTS dim_pdv (
    pdv_sk                INTEGER PRIMARY KEY AUTOINCREMENT,
    pdv_codigo            INTEGER NOT NULL UNIQUE,
    descricao             TEXT,
    empresa_codigo        INTEGER,
    ativo                 INTEGER NOT NULL DEFAULT 1,
    loaded_at             TEXT NOT NULL DEFAULT (datetime('now')),
    source_system         TEXT NOT NULL DEFAULT 'WEBPOSTO'
);

CREATE INDEX IF NOT EXISTS idx_dim_pdv_codigo ON dim_pdv (pdv_codigo);
