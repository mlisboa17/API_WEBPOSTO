-- INSERT for dim_empresa
-- Records: 2
SET app.current_tenant = 'posto_vip';

INSERT INTO logos_dw.dim_empresa (empresa_codigo, cnpj, razao_social, nome_fantasia, endereco, cidade, estado, ativo, _loaded_at, _source_endpoint, _record_hash) VALUES (5555, '04.284.939/0001-86', 'AUTO POSTO CASA CAIADA LTDA', 'AP CASA CAIADA', 'AVE AVENIDA GOVERNADOR CARLOS DE LIMA', 'OLINDA', 'PE', TRUE, 'CURRENT_TIMESTAMP', 'EMPRESA', 3251044826) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_empresa (empresa_codigo, cnpj, razao_social, nome_fantasia, endereco, cidade, estado, ativo, _loaded_at, _source_endpoint, _record_hash) VALUES (11495, '03.008.754/0001-86', 'RIO DOCE COMERCIO E SERVICOS LTDA', 'POSTO VIP', 'AVE AVENIDA BRASIL', 'OLINDA', 'PE', TRUE, 'CURRENT_TIMESTAMP', 'EMPRESA', 3626104230) ON CONFLICT DO NOTHING;