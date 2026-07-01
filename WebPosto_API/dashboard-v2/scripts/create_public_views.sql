-- ========================================
-- SCRIPT: create_public_views.sql
-- OBJETIVO: Criar views no schema public que apontam para tabelas do logos_dw
-- MOTIVO: Dashboard espera tabelas em public, mas dados estão em logos_dw
-- NOTA: Apenas 6 tabelas existem atualmente no logos_dw
-- ========================================

-- DIMENSÕES (3 tabelas)
-- ----------------------------------------

-- Criar view para dim_cliente
CREATE OR REPLACE VIEW public.dim_cliente AS
SELECT * FROM logos_dw.dim_cliente;

-- Criar view para dim_empresa
CREATE OR REPLACE VIEW public.dim_empresa AS
SELECT * FROM logos_dw.dim_empresa;

-- Criar view para dim_produto
CREATE OR REPLACE VIEW public.dim_produto AS
SELECT * FROM logos_dw.dim_produto;

-- FATOS (3 tabelas)
-- ----------------------------------------

-- Criar view para fact_receber
CREATE OR REPLACE VIEW public.fact_receber AS
SELECT * FROM logos_dw.fact_receber;

-- Criar view para fact_venda
CREATE OR REPLACE VIEW public.fact_venda AS
SELECT * FROM logos_dw.fact_venda;

-- Criar view para fact_venda_item
CREATE OR REPLACE VIEW public.fact_venda_item AS
SELECT * FROM logos_dw.fact_venda_item;

-- ========================================
-- PERMISSÕES: Conceder SELECT individualmente em cada view
-- ========================================

GRANT SELECT ON public.dim_cliente TO anon, authenticated;
GRANT SELECT ON public.dim_empresa TO anon, authenticated;
GRANT SELECT ON public.dim_produto TO anon, authenticated;
GRANT SELECT ON public.fact_receber TO anon, authenticated;
GRANT SELECT ON public.fact_venda TO anon, authenticated;
GRANT SELECT ON public.fact_venda_item TO anon, authenticated;

-- ========================================
-- VERIFICAÇÃO: Confirmar que as views foram criadas
-- ========================================

SELECT 
    schemaname, 
    viewname 
FROM pg_views 
WHERE schemaname = 'public' 
    AND (viewname LIKE 'dim_%' OR viewname LIKE 'fact_%')
ORDER BY viewname;
