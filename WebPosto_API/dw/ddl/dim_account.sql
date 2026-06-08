-- dim_account — alias lógico de dim_plano_conta (F01.4-B)
-- Ver dim_plano_conta.sql para DDL completo; esta view unifica nomenclatura A04

CREATE VIEW IF NOT EXISTS dim_account AS
SELECT
    plano_conta_sk AS account_sk,
    codigo_gerencial AS account_id,
    descricao_gerencial AS account_name,
    categoria_logos_v3 AS financial_category,
    apura_dre,
    classification_source,
    confidence_score,
    is_current
FROM dim_plano_conta
WHERE is_current = 1;
