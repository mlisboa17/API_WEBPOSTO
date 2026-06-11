-- dim_turn — LOGOS SPACE DW F03
CREATE TABLE IF NOT EXISTS dim_turn (
    turn_sk               INTEGER PRIMARY KEY AUTOINCREMENT,
    turno_codigo          INTEGER,
    turno_nome            TEXT NOT NULL,
    ordem                 INTEGER,
    loaded_at             TEXT NOT NULL DEFAULT (datetime('now')),
    source_system         TEXT NOT NULL DEFAULT 'WEBPOSTO'
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_dim_turn_nk ON dim_turn (turno_codigo, turno_nome);
