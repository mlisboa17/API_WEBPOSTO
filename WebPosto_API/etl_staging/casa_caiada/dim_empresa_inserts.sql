-- INSERT statements for dim_empresa
-- Source: etl_staging\casa_caiada\dim_empresa.json
-- Tenant: casa_caiada
-- Records: 2
-- Generated: 2026-06-19T21:35:48.040849

SET app.current_tenant = 'casa_caiada';

INSERT INTO logos_dw.dim_empresa (empresacodigo, cnpj, razao, fantasia, tipologradouro, logradouro, endereco, bairro, numero, cep, cidade, estado, latitude, longitude, ultimousuarioalteracao, centrocustoprincipal, empresacodigoexterno, sigla, tipoimposto, codigo) VALUES (5555, '04.284.939/0001-86', 'AUTO POSTO CASA CAIADA LTDA', 'AP CASA CAIADA', 'AVE', 'AVENIDA GOVERNADOR CARLOS DE LIMA', 'AVE AVENIDA GOVERNADOR CARLOS DE LIMA', 'CASA CAIADA', '2350', '53.040-000', 'OLINDA', 'PE', -7.9847269, -34.8384772, 'CAMILY', 7295, NULL, NULL, 'R', 5555) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_empresa (empresacodigo, cnpj, razao, fantasia, tipologradouro, logradouro, endereco, bairro, numero, cep, cidade, estado, latitude, longitude, ultimousuarioalteracao, centrocustoprincipal, empresacodigoexterno, sigla, tipoimposto, codigo) VALUES (11495, '03.008.754/0001-86', 'RIO DOCE COMERCIO E SERVICOS LTDA', 'POSTO VIP', 'AVE', 'AVENIDA BRASIL', 'AVE AVENIDA BRASIL', 'RIO DOCE', '2701', '53.070-380', 'OLINDA', 'PE', -7.955013199999999, -34.851076, 'JOSÉ ARTHUR MAIA GIRAO', 7295, NULL, NULL, 'R', 11495) ON CONFLICT DO NOTHING;
