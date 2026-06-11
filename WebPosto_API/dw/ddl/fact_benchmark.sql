-- fact_benchmark — F04.6
CREATE TABLE IF NOT EXISTS fact_benchmark (
    benchmark_id SERIAL PRIMARY KEY,
    benchmark_type VARCHAR(32) NOT NULL,
    entity_key VARCHAR(64) NOT NULL,
    entity_name VARCHAR(256),
    score NUMERIC(12, 2),
    receita NUMERIC(14, 2),
    lucro NUMERIC(14, 2),
    roi NUMERIC(12, 2),
    perdas NUMERIC(14, 2),
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    empresa_codigo INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- fact_gap — F04.6
CREATE TABLE IF NOT EXISTS fact_gap (
    gap_id SERIAL PRIMARY KEY,
    gap_type VARCHAR(32) NOT NULL,
    entity_key VARCHAR(64),
    gap_value NUMERIC(14, 2),
    media_rede NUMERIC(14, 2),
    valor_realizado NUMERIC(14, 2),
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- fact_best_practice — F04.6
CREATE TABLE IF NOT EXISTS fact_best_practice (
    practice_id SERIAL PRIMARY KEY,
    practice_type VARCHAR(16) NOT NULL,
    padrao VARCHAR(256),
    acao TEXT,
    referencia_json JSONB,
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- dim_benchmark_type — F04.6
CREATE TABLE IF NOT EXISTS dim_benchmark_type (
    benchmark_type_code VARCHAR(32) PRIMARY KEY,
    benchmark_type_name VARCHAR(128) NOT NULL,
    sprint VARCHAR(16) DEFAULT 'F04.6'
);

INSERT INTO dim_benchmark_type (benchmark_type_code, benchmark_type_name) VALUES
    ('FILIAL', 'Benchmark Filial'),
    ('OPERADOR', 'Benchmark Operador'),
    ('PDV', 'Benchmark PDV'),
    ('TURNO', 'Benchmark Turno')
ON CONFLICT (benchmark_type_code) DO NOTHING;
