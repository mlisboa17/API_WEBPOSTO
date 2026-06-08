# BANKING COST ANALYSIS — F01.1.1

**Período:** 2026-06-01 → 2026-06-07 (rede)

## Tesouraria — MOVIMENTO_CONTA

| Classe | Qtd | Valor (R$) |
|---|---:|---:|
| Créditos | 1021 | 113719.34 |
| Débitos | 979 | 3410.49 |
| Tarifas (TAXA_TRANSFERENCIA) | 977 | 390.49 |
| Transferências | 978 | 58401.27 |

## Classificação PIX/TED/DOC

- Movimentos com descrição PIX/TED/DOC identificados na amostra: **0**
- Classificador atual usa `tipoDocumentoOrigem` (TAXA_TRANSFERENCIA, TRANSFERENCIA_BANCARIA)

## Economias potenciais

1. Tarifas acumuladas R$ **390,49** em **977** eventos — revisar pacote bancário (F02).
2. Transferências R$ **58.401,27** — avaliar consolidação de contas (F02).
3. Créditos vs débitos isolados — **não somar** com CP/CR (regra de ouro).

## Anomalias

- Nenhuma anomalia crítica de valor; paginação MOVIMENTO_CONTA limita amostra bruta a 200/request (FC agrega até 2000).
