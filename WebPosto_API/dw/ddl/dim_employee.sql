-- dim_employee — LOGOS SPACE DW F04.0
CREATE TABLE IF NOT EXISTS dim_employee (
    employee_sk           INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id             INTEGER NOT NULL,
    employee_code           INTEGER NOT NULL,
    employee_name           TEXT,
    employee_cpf            TEXT,
    employee_reference      TEXT,
    employee_status         TEXT NOT NULL DEFAULT 'ATIVO',
    empresa_codigo          INTEGER,
    loaded_at               TEXT NOT NULL DEFAULT (datetime('now')),
    source_system           TEXT NOT NULL DEFAULT 'WEBPOSTO_FUNCIONARIO'
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_dim_employee_code ON dim_employee (employee_code);
