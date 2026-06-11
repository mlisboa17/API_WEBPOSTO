-- dim_operator — LOGOS SPACE DW F03
CREATE TABLE IF NOT EXISTS dim_operator (
    operator_sk           INTEGER PRIMARY KEY AUTOINCREMENT,
    funcionario_codigo    INTEGER NOT NULL UNIQUE,
    nome                  TEXT,
    cpf                   TEXT,
    empresa_codigo        INTEGER,
    ativo                 INTEGER NOT NULL DEFAULT 1,
    loaded_at             TEXT NOT NULL DEFAULT (datetime('now')),
    source_system         TEXT NOT NULL DEFAULT 'WEBPOSTO'
);

CREATE INDEX IF NOT EXISTS idx_dim_operator_codigo ON dim_operator (funcionario_codigo);
