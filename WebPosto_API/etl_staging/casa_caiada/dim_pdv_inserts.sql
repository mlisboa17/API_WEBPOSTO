-- INSERT statements for dim_pdv
-- Source: etl_staging\casa_caiada\dim_pdv.json
-- Tenant: casa_caiada
-- Records: 30
-- Generated: 2026-06-19T21:35:48.063274

SET app.current_tenant = 'casa_caiada';

INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (5555, 15880, 'POSTO CASA CAIADA', 'Pista', 'true', '001', 15880) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (5555, 16735, 'GETNET PN YG01002038', 'Mobile', 'false', '002', 16735) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (5555, 16736, 'CIELO NS: 4AJ722X65.', 'Mobile', 'true', '003', 16736) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (11495, 54193, 'POSTO VIP - RIO DOCE LISBOA', 'Pista', 'true', '001', 54193) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (11495, 56764, 'LOJA - CAIXA LOJA', 'Conveniência', 'true', '002', 56764) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (11495, 56800, 'CIELO (4A577TC1L)', 'Mobile', 'false', '003', 56800) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (11495, 56801, 'REDE 01 (SD135498)', 'Mobile', 'false', '004', 56801) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (11495, 56802, 'REDE 02 (SD081769)', 'Mobile', 'false', '005', 56802) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (11495, 57769, 'REDE 03 (SD97679)', 'Mobile', 'false', '006', 57769) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (5555, 61153, 'PAGBANK NS:6001062506096335', 'Mobile', 'true', '004', 61153) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (5555, 61154, 'PDV PAGBANK NS: PBA1242E72733.', 'Mobile', 'true', '005', 61154) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (11495, 61285, 'REDE 04 (SD136045)', 'Mobile', 'false', '007', 61285) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (11495, 61286, 'PB 05 (PBA123C477817)', 'Mobile', 'false', '008', 61286) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (11495, 66037, 'PB 06 (PBA1241A74507)', 'Mobile', 'false', '009', 66037) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (11495, 66103, 'REDE 07 4AJ08PV2M', 'Mobile', 'true', '010', 66103) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (11495, 66301, 'REDE 08 4AH45S58Y', 'Mobile', 'true', '011', 66301) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (11495, 68479, 'REDE 09 4AK35XN52', 'Mobile', 'true', '012', 68479) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (11495, 68875, 'PB 10 (PB3S24CC72342).', 'Mobile', 'false', '013', 68875) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (11495, 75640, 'CIELO 4AB950737', 'Mobile', 'true', '014', 75640) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (11495, 78016, 'REDE 11 4AJ90CF7S', 'Mobile', 'true', '015', 78016) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (11495, 78247, 'REDE  4AG88XC51', 'Mobile', 'true', '016', 78247) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (11495, 80392, 'TESTE 01', 'Mobile', 'false', '017', 80392) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (5555, 81415, 'INATIVADO', 'Mobile', 'false', '006', 81415) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (11495, 82735, 'CIELO 4AG95RH6Z', 'Mobile', 'true', '018', 82735) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (11495, 83890, 'CIELO 4AG95RD4D', 'Mobile', 'false', '019', 83890) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (11495, 83891, 'CIELO 4AG95RF7Y', 'Mobile', 'true', '020', 83891) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (11495, 88147, 'PDV LOJA 03.', 'Conveniência', 'true', '021', 88147) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (11495, 90787, 'REDE 4AJ90BK6V', 'Mobile', 'true', '022', 90787) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (5555, 91117, 'GERENCIAL', 'Escritório', 'true', '007', 91117) ON CONFLICT DO NOTHING;
INSERT INTO logos_dw.dim_pdv (empresacodigo, pdvcodigo, pdv, tipo, ativo, pdvreferencia, codigo) VALUES (11495, 91877, 'REDE SD018210', 'Mobile', 'true', '023', 91877) ON CONFLICT DO NOTHING;
