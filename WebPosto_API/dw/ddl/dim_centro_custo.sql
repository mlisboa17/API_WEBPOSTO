-- dim_centro_custo — LOGOS SPACE DW (F01.4-A)
-- Fonte primária: TITULO_PAGAR.centroCustoCodigo / MOVIMENTO_CONTA.centroCustoCodigo
-- CENTRO_CUSTO_REDE: HTTP 401 (lacuna documentada)

CREATE TABLE IF NOT EXISTS dim_centro_custo (
    centro_custo_sk         INTEGER PRIMARY KEY AUTOINCREMENT,
    centro_custo_codigo     INTEGER NOT NULL,
    centro_custo_descricao  TEXT,
    empresa_codigo          INTEGER,
    categoria_logos         TEXT,
    ativo                   INTEGER NOT NULL DEFAULT 1,
    valid_from              TEXT NOT NULL DEFAULT (datetime('now')),
    valid_to                TEXT,
    is_current              INTEGER NOT NULL DEFAULT 1,
    UNIQUE (centro_custo_codigo, empresa_codigo, is_current)
);

CREATE INDEX IF NOT EXISTS idx_dim_centro_custo_empresa ON dim_centro_custo (empresa_codigo);
CREATE INDEX IF NOT EXISTS idx_dim_centro_custo_codigo ON dim_centro_custo (centro_custo_codigo);
