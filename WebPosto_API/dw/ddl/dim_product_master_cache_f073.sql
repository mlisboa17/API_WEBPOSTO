-- F07.3 — Product Master cache & performance DW

CREATE TABLE IF NOT EXISTS dim_product_master_cache (
    cache_id SERIAL PRIMARY KEY,
    produto_codigo BIGINT NOT NULL,
    empresa_codigo BIGINT NOT NULL,
    nome_produto VARCHAR(256),
    departamento VARCHAR(32) NOT NULL,
    fonte VARCHAR(64) NOT NULL,
    confidence VARCHAR(16) NOT NULL DEFAULT 'MEDIA',
    last_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    evidence JSONB NOT NULL DEFAULT '[]',
    UNIQUE (produto_codigo, empresa_codigo)
);

CREATE TABLE IF NOT EXISTS fact_product_lookup_performance (
    perf_id SERIAL PRIMARY KEY,
    tempo_lookup_antes_sec NUMERIC(10, 2),
    tempo_lookup_depois_sec NUMERIC(10, 2),
    reducao_percentual NUMERIC(8, 2),
    lookups_executados INT,
    cache_hits INT,
    cache_misses INT,
    cache_hit_rate_pct NUMERIC(8, 2),
    timeouts INT,
    errors INT,
    performance_aprovada BOOLEAN NOT NULL DEFAULT FALSE,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_product_residual_sku (
    residual_id SERIAL PRIMARY KEY,
    produto_codigo BIGINT NOT NULL,
    classificacao_final VARCHAR(32) NOT NULL,
    nome_resolvido VARCHAR(256),
    departamento VARCHAR(32),
    venda_item_ocorrencias INT,
    empresa_codigo BIGINT,
    probes JSONB NOT NULL DEFAULT '[]',
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
