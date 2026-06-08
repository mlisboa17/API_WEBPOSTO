# TREASURY_MODULE_BLUEPRINT — A03.7

**Período evidência:** 2026-06-01 .. 2026-06-07

## Fontes

- MOVIMENTO_CONTA: 200 reg, 486.2ms
- TRANSFERENCIA_BANCARIA: 200 reg

## Mapeamento tipos

| Tipo | Contagem |
|---|---:|
| Crédito | 100 |
| Débito | 100 |

## Origem documento (`tipoDocumentoOrigem`)

| Origem | Contagem | Interpretação LOGOS |
|---|---:|---|
| TRANSFERENCIA_BANCARIA | 100 | Transferências entre contas / recebimentos |
| TAXA_TRANSFERENCIA | 100 | Tarifas bancárias (par crédito+débito) |

**Evidência amostra (01/06/2026):**
- Crédito R$ 50,00 — `"TRANSF. BANCÁRIA : AG:4047 CONTA:10993263..."`
- Débito R$ 0,33 — `"TAXA REFERENTE A TRANSFERÊNCIA..."`

## PIX / TED / DOC

No período auditado, **nenhum padrão PIX/TED/DOC** apareceu em `descricao`. Movimentos dominados por transferências bancárias internas + taxas. Classificação futura via regex em `descricao` + `tipoDocumentoOrigem`.

## Campos chave (schema completo)

`empresaCodigo`, `movimentoContaCodigo`, `valor`, `dataMovimento`, `descricao`, `tipoDocumentoOrigem`, `codigoTipoDocumentoOrigem`, `documentoOrigemCodigo`, `tipo`, `conciliado`, `contaCodigo`, `planoContaGerencialCodigo`, `centroCustoCodigo`

## Paginação

API retorna **200 registros por chamada** (486ms). Campo `ultimoCodigo` presente — paginar em produção para volume completo.

## Módulo TESOURARIA (futuro F02)

- Extrato consolidado por contaCodigo
- Conciliação bancária (conciliado flag)
- Tarifas isoladas para DRE financeiro
- Não misturar com despesas gerenciais
