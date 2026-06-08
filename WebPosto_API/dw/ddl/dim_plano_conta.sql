-- dim_plano_conta — LOGOS SPACE DW (F01.4-A)
-- Granularidade: 1 linha por plano de conta gerencial
-- SCD Type 1 (overwrite) na carga A04

CREATE TABLE IF NOT EXISTS dim_plano_conta (
    plano_conta_sk          INTEGER PRIMARY KEY AUTOINCREMENT,
    plano_conta_id          INTEGER NOT NULL,
    codigo_gerencial        INTEGER NOT NULL,
    descricao_gerencial     TEXT NOT NULL,
    codigo_contabil         INTEGER,
    descricao_contabil      TEXT,
    natureza                TEXT,
    tipo                    TEXT,
    apura_dre               TEXT,
    categoria_logos         TEXT NOT NULL,
    categoria_logos_v2      TEXT NOT NULL,
    categoria_logos_v3      TEXT NOT NULL,
    classification_source   TEXT,
    confidence_score        REAL CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    ativo                   INTEGER NOT NULL DEFAULT 1,
    valid_from              TEXT NOT NULL DEFAULT (datetime('now')),
    valid_to                TEXT,
    is_current              INTEGER NOT NULL DEFAULT 1,
    UNIQUE (codigo_gerencial, is_current)
);

CREATE INDEX IF NOT EXISTS idx_dim_plano_conta_codigo ON dim_plano_conta (codigo_gerencial);
CREATE INDEX IF NOT EXISTS idx_dim_plano_conta_categoria_v3 ON dim_plano_conta (categoria_logos_v3);
CREATE INDEX IF NOT EXISTS idx_dim_plano_conta_ativo ON dim_plano_conta (ativo);
