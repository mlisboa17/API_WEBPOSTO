-- F07.6 — Commercial Action Center DW

CREATE TABLE IF NOT EXISTS fact_commercial_action (
    action_id SERIAL PRIMARY KEY,
    action_code VARCHAR(32) NOT NULL UNIQUE,
    tipo VARCHAR(64) NOT NULL,
    titulo VARCHAR(256) NOT NULL,
    descricao TEXT,
    produto_codigo BIGINT,
    empresa_codigo BIGINT,
    departamento VARCHAR(32),
    prioridade VARCHAR(16) NOT NULL,
    status VARCHAR(32) NOT NULL,
    prazo VARCHAR(16),
    owner_id BIGINT,
    owner_name VARCHAR(128),
    owner_role VARCHAR(64),
    impacto_estimado_receita NUMERIC(14, 2),
    impacto_estimado_margem NUMERIC(14, 2),
    evidencia JSONB NOT NULL DEFAULT '{}',
    lineage JSONB NOT NULL DEFAULT '[]',
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_commercial_action_summary (
    summary_id SERIAL PRIMARY KEY,
    total_acoes INT NOT NULL DEFAULT 0,
    acoes_alta_prioridade INT NOT NULL DEFAULT 0,
    impacto_total_receita NUMERIC(14, 2),
    impacto_total_margem NUMERIC(14, 2),
    por_status JSONB NOT NULL DEFAULT '{}',
    por_prioridade JSONB NOT NULL DEFAULT '{}',
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
