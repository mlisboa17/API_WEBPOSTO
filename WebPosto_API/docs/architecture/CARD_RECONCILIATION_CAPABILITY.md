# Card Reconciliation Capability — VALUE-04

**Decisão formal:** `reconciliation_level = 2` (**LEVEL 2 — TRANSACTIONAL EVIDENCE**)

> Atualizado em 2026-07-21. Revisão da decisão LEVEL 1 original (histórico abaixo) após
> descoberta e integração do endpoint `/INTEGRACAO/CARTAO` e do motor de matching
> banco↔WebPosto (`src/services/bank_reconciliation/`). Esta revisão fecha a lacuna de
> evidência externa que `docs/d02/D02_CONCEPTUAL_CORRECTION.md` já documentava como
> necessária para "Cartões" (Adquirente/portal/NSU) e "PIX/transferência" (extrato bancário).

## Justificativa (evidência atual)

| Critério | Evidência |
|---|---|
| Dados transacionais TEF | **Disponíveis** via `/INTEGRACAO/CARTAO`: NSU, `nsuTef`, `autorizacao`, `administradoraCodigo`, `centroCustoDescricao` (PISTA/LOJA) por venda |
| Venda forma pagamento | Volume real confirmado (milhares de linhas/período nos 3 postos) — a leitura anterior de "0 registros" estava desatualizada/incorreta |
| Extrato bancário (OFX) | Parser real (`ofx_parser.py`) classifica 100% dos lançamentos testados (PagBank e Itaú/Rede-Cielo) |
| Matching venda↔banco | Implementado: `match_card_settlements` (transação a transação, formato PagBank) e `compare_daily_card_settlements_with_lag` (balde diário, formato Itaú/Rede-Cielo, com lag D+1 útil e bundling de fim de semana) |
| Taxa de adquirente | Parametrizada e validada contra fonte oficial (Rede/e-Rede e PagBank) em `src/domain/reconciliation/acquirer_fee_model.py` |
| Vínculo venda↔título | Campo `vendaCodigo` presente; ainda não validado como link direto a cartão |

## O que LEVEL 2 permite afirmar

- Matching transação-a-transação entre venda WebPosto e lançamento bancário real (PagBank)
- Matching agregado diário por bandeira/modalidade com lag de liquidação (Itaú/Rede-Cielo)
- Gap real (venda vs. banco) por dia/bandeira/modalidade, com taxa de adquirente validada
- Atribuição de centro de custo (PISTA/LOJA) por venda de cartão via `/INTEGRACAO/CARTAO`

## O que ainda é proibido / limitado (gaps reais, não resolvidos)

- PIX não é rastreável por transação: `venda_forma_pagamento` de PIX sempre tem `administradoraCodigo=null` e `taxaPercentual=null` — validação só é possível a nível de cadastro
- "Crédito Pré-Pago" não é identificável em nenhuma fonte WebPosto (cadastro `tipo` só tem 5 valores fixos; `/INTEGRACAO/CARTAO` não tem campo de BIN/flag pré-pago)
- Vip/Itaú: gap de sexta-feira (fim de semana colado) ainda maior que dias úteis — limitação conhecida do bundling universal, documentada em `card_bank_matching_service.py`
- Atribuição de adquirente por venda individual (Rede vs. Cielo) ainda não é possível — heurística por sufixo de código foi tentada e descartada por inconsistência real entre bandeiras

## Fontes por papel

| Papel | Fonte |
|---|---|
| Expectativa | `TITULO_RECEBER` (pendente) + `venda_forma_pagamento` (bruto/líquido esperado) |
| Evidência transacional cartão | `/INTEGRACAO/CARTAO` (NSU, autorização, centro de custo) |
| Evidência externa banco | Extrato OFX real (PagBank BANKID=290; Itaú BANKID=0341), via `ofx_parser.py` |
| Liquidação contábil | `TITULO_RECEBER` (`dataPagamento`, `pendente=false`) |
| Taxa de adquirente | `src/domain/reconciliation/acquirer_fee_model.py` (Supabase → `config/acquirer_fee_model.json` → seed em memória) |

---

## Histórico — decisão original (LEVEL 1, superada)

**Decisão formal:** `reconciliation_level = 1` (**LEVEL 1 — AGGREGATE SIGNAL**)

### Justificativa

| Critério | Evidência |
|---|---|
| Dados transacionais TEF | Ausentes (sem NSU, autorização, adquirente) |
| Venda forma pagamento | Endpoint existe; **0 registros** nos 3 postos (30d) |
| Titulo receber | Disponível; classificação pendente/vencido/recebido |
| Vínculo venda↔titulo | Campo `vendaCodigo` presente; **não validado** como cartão |
| Movimento bancário | Disponível; **sem match** titulo a titulo |

### O que LEVEL 1 permitia afirmar

- Total de recebíveis **vencidos** sem evidência de liquidação (`pendente=true`, sem `dataPagamento`)
- Concentração por cliente / contagem de títulos
- **Não** afirmar gap cartão TEF vs adquirente
- **Não** afirmar perda confirmada — apenas ausência de evidência de baixa

### O que LEVEL 1 proibia

- Transaction reconciliation
- "R$ X de cartão não recebido" sem fonte cartão
- CONFIRMED Money Found por ausência de baixa alone

