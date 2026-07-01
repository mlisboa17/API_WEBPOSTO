-- ========================================
-- SCRIPT: diagnose_schema.sql
-- OBJETIVO: Descobrir onde as tabelas realmente estão
-- ========================================

-- 1. Listar todos os schemas disponíveis
SELECT schema_name 
FROM information_schema.schemata 
WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
ORDER BY schema_name;

-- 2. Buscar tabelas que começam com 'dim_' ou 'fact_' em qualquer schema
SELECT 
    table_schema,
    table_name,
    table_type
FROM information_schema.tables 
WHERE (table_name LIKE 'dim_%' OR table_name LIKE 'fact_%' OR table_name = 'alert_events')
    AND table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY table_schema, table_name;

-- 3. Buscar especificamente as tabelas que o dashboard precisa
SELECT 
    table_schema,
    table_name
FROM information_schema.tables 
WHERE table_name IN (
    'dim_empresa',
    'dim_unidade',
    'dim_produto',
    'dim_caixa',
    'dim_cliente',
    'dim_tempo',
    'fact_venda',
    'fact_venda_item',
    'fact_receber',
    'fact_pagar',
    'fact_cartao',
    'fact_nfce',
    'alert_events',
    'fact_estoque'
)
ORDER BY table_schema, table_name;
