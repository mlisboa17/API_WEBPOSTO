-- F07.4 — Produtos Vendidos performance & margin DW

CREATE TABLE IF NOT EXISTS fact_product_sales_margin (
    margin_id SERIAL PRIMARY KEY,
    sale_item_id VARCHAR(64),
    empresa_codigo BIGINT NOT NULL,
    produto_codigo BIGINT NOT NULL,
    departamento VARCHAR(32) NOT NULL,
    quantidade NUMERIC(14, 4) NOT NULL DEFAULT 0,
    receita NUMERIC(14, 2) NOT NULL DEFAULT 0,
    custo_total NUMERIC(14, 2) NOT NULL DEFAULT 0,
    margem_bruta NUMERIC(14, 2) NOT NULL DEFAULT 0,
    margem_bruta_pct NUMERIC(8, 2) NOT NULL DEFAULT 0,
    lineage JSONB NOT NULL DEFAULT '[]',
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_product_margin_by_department (
    dept_margin_id SERIAL PRIMARY KEY,
    departamento VARCHAR(32) NOT NULL,
    receita NUMERIC(14, 2) NOT NULL DEFAULT 0,
    margem_bruta NUMERIC(14, 2) NOT NULL DEFAULT 0,
    margem_pct NUMERIC(8, 2) NOT NULL DEFAULT 0,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_commercial_opportunity (
    opportunity_id SERIAL PRIMARY KEY,
    tipo VARCHAR(64) NOT NULL,
    prioridade VARCHAR(16) NOT NULL,
    descricao TEXT NOT NULL,
    empresa_codigo BIGINT,
    produto_codigo BIGINT,
    departamento VARCHAR(32),
    impacto_estimado_receita NUMERIC(14, 2),
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
