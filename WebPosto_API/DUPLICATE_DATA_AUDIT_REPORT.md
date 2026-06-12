# Duplicate Data Audit

- Mesma chave configurada VIP/Casa: **False**
- Duplicidade detectada: **True**

- VENDA: tokens ['TOKEN_POSTO_VIP', 'TOKEN_AP_CASA_CAIADA'] → empresas [5555, 11495]
- VENDA: tokens ['TOKEN_POSTO_VIP', 'WEBPOSTO_API_KEY'] → empresas [5555, 11495]
- VENDA: tokens ['TOKEN_AP_CASA_CAIADA', 'WEBPOSTO_API_KEY'] → empresas [5555, 11495]
- ABASTECIMENTO: tokens ['TOKEN_POSTO_VIP', 'TOKEN_AP_CASA_CAIADA'] → empresas [5555, 11495]
- ABASTECIMENTO: tokens ['TOKEN_POSTO_VIP', 'WEBPOSTO_API_KEY'] → empresas [5555, 11495]
- ABASTECIMENTO: tokens ['TOKEN_AP_CASA_CAIADA', 'WEBPOSTO_API_KEY'] → empresas [5555, 11495]
- LMC_REDE: tokens ['TOKEN_POSTO_VIP', 'TOKEN_AP_CASA_CAIADA'] → empresas [5555, 11495]
- LMC_REDE: tokens ['TOKEN_POSTO_VIP', 'WEBPOSTO_API_KEY'] → empresas [5555, 11495]
- LMC_REDE: tokens ['TOKEN_AP_CASA_CAIADA', 'WEBPOSTO_API_KEY'] → empresas [5555, 11495]

Auditoria por empresaCodigo; IDs de venda/LMC exigem amostragem adicional se tokens distintos.
