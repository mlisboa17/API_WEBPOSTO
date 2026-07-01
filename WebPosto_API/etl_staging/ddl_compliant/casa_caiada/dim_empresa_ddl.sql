-- DDL-COMPLIANT INSERT for dim_empresa
-- Tenant: casa_caiada
-- Records: 2
-- Generated: 2026-06-19T22:40:09.288122

SET app.current_tenant = 'casa_caiada';

INSERT INTO logos_dw.dim_empresa (empresa_codigo, cnpj, razao_social, nome_fantasia, endereco, cidade, estado, ativo) VALUES (5555, '04.284.939/0001-86', 'AUTO POSTO CASA CAIADA LTDA', 'AP CASA CAIADA', 'AVE AVENIDA GOVERNADOR CARLOS DE LIMA', 'OLINDA', 'PE', TRUE) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_empresa (empresa_codigo, cnpj, razao_social, nome_fantasia, endereco, cidade, estado, ativo) VALUES (11495, '03.008.754/0001-86', 'RIO DOCE COMERCIO E SERVICOS LTDA', 'POSTO VIP', 'AVE AVENIDA BRASIL', 'OLINDA', 'PE', TRUE) ON CONFLICT DO NOTHING;
