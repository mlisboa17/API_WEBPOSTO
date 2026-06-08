# Sprint 22A - Fuel Network Probe

Data de execucao: 2026-06-08
Periodo: 2026-05-09 ate 2026-06-08

## Resumo

| Endpoint | HTTP | empresaCodigo | produtoCodigo | quantidade | data | Cobertura filiais |
|---|---:|:---:|:---:|:---:|:---:|---:|
| CONSULTAR_VENDA_ITEM_REDE | 401 | NAO | NAO | NAO | NAO | 0 |
| CONSULTAR_ABASTECIMENTO_REDE | 401 | NAO | NAO | NAO | NAO | 0 |
| CONSULTAR_VENDA_REDE | 200 | NAO | NAO | NAO | NAO | 0 |
| CONSULTAR_LMC_REDE | 200 | SIM | SIM | SIM | SIM | 2 |

## Conclusoes

- CONSULTAR_LMC_REDE deve ser a base oficial da Sprint 22 quando retornar HTTP 200 com campos estruturais esperados.
- CONSULTAR_VENDA_ITEM_REDE status atual: 401.
- CONSULTAR_ABASTECIMENTO_REDE status atual: 401.
- CONSULTAR_VENDA_REDE status atual: 200.
- CONSULTAR_LMC_REDE cobertura de filiais no periodo: 2.
- Cobertura de filiais considera o conjunto distinto de empresaCodigo retornado por endpoint.