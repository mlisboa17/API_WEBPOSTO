-- dim_cost_center — alias lógico de dim_centro_custo (F01.4-B)
-- Ver dim_centro_custo.sql para DDL completo

CREATE VIEW IF NOT EXISTS dim_cost_center AS
SELECT
    centro_custo_sk AS cost_center_sk,
    codigo AS cost_center_id,
    descricao AS cost_center_name,
    empresa_codigo,
    is_current
FROM dim_centro_custo
WHERE is_current = 1;
