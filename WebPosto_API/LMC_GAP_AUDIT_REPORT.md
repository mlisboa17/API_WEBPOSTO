# LMC Gap Audit

- Litros vendidos: **57,725.9 L**
- Litros conciliados: **2,958.2 L**
- Litros não conciliados: **54,767.7 L**
- Cobertura LMC: **5.12%**

## Por quê?

- **Join ABASTECIMENTO×VENDA_ITEM incompleto**: 84/200 (42.0%)
- **LMC snapshot subdimensionado vs volume vendido**: 28 registros LMC vs 57,725.9 L vendidos
- **Endpoints bico/tanque bloqueados (401)**: CONSULTAR_LMC_REDE_BICO, CONSULTAR_LMC_REDE_TANQUE, BICO_REDE
- **VENDA_ITEM_REDE bloqueado (401)**: /INTEGRACAO/CONSULTAR_VENDA_ITEM_REDE

**Fonte que falta:** CONSULTAR_LMC_REDE expandido + join ABAST 100% + token bico/tanque
