# FR-01 — Fueling Settlement Trace Validation

## Problem

O antifraude apresentava narrativa factualmente incorreta ao colapsar N abastecimentos / N pagamentos / N cartões em uma única forma + um NSU aplicado ao valor total do cupom.

## Root Cause

1. `_index_cartoes` — 1º CARTAO por `vendaCodigo`
2. `best_pag` — 1 forma de pagamento por abastecimento
3. `_pick_payment_anchor` — 1 bandeira/NSU na ocorrência
4. `valorTotalCartao` — soma dos abastecimentos mesmo em venda mista

(Itens 5–7 scoring/retenção MAX/agrupamento → **FR-02**)

## Domain Model

`FuelingSettlementTrace` (sob demanda / cache RAM; sem migration):

- `sale` · `fuelings[]` · `payments[]` · `cards[]`
- `reconciliation` · `retention` (por fueling + min/max)
- `trace_status` · `payment_mode`
- `legacy_projection` (campos N→1 documentados como DEPRECATED)

**EXPLAINED ≠ NO_FRAUD** — significa cadeia financeira/fiscal reconstruída.

## Cardinalities

| Relação | Preservada |
|---|---|
| Venda → fuelings | N |
| Venda → payments | N |
| Venda → cards | N |
| VFP.financeiroCodigo → CARTAO.cartaoCodigo | 1:1 estruturado |
| Fueling → payment | **não** (só sale-level) |

## Reuse

| Item | Decisão |
|---|---|
| `WebPostoPistaService.coletar_pista_universo` | REUSE_WITH_CHANGE |
| `AbastecimentoRestV1` campos TEF | DEPRECATED_PROJECTION (mantidos) |
| `FraudDetectionEngine._detect` score | REUSE_AS_IS (não alterado) |
| `FuelingSettlementTrace` | CREATE |

## Golden Case

Venda `366670631` · Cupom `3974` · 74014 · 2026-08-10 · CAIO `299254`

| | n | totais |
|---|---|---|
| fuelings | 3 | 100 + 268.73 + 40 = **408.73** |
| payments | 3 | CARTAO 100 · CARTAO 268.73 · DINHEIRO 40 |
| cards | 2 | Premmia PIX / Premmia Crédito · NSUs UUID distintos |

Retenções individuais: **35 / 18 / 13** min (não reduzidas a MAX na camada FR-01).

## Reconciliation

- `FUELING_TO_SALE` = EXACT  
- `SALE_TO_PAYMENT` = EXACT  
- `trace_status` = EXPLAINED  
- `payment_mode` = MIXED  

## Legacy Projection

| Campo | Classificação |
|---|---|
| `formaPagamento` | DEPRECATED_PROJECTION |
| `cartaoBandeira` | DEPRECATED_PROJECTION |
| `cartaoNsu` | DEPRECATED_PROJECTION |
| `cartaoAutorizacao` | DEPRECATED_PROJECTION |
| `valorTotalCartao` | DEPRECATED_PROJECTION |
| `settlementTrace` | FR-01 source of truth |

### Consumidores N→1 (preflight)

| Superfície | Usa settlementTrace? | Narrativa falsa N→1? | Severidade | Status |
|---|---|---|---|---|
| card-fraud-audit-panel `PagamentoBlock` | YES | NÃO (quando trace presente) | — | SAFE |
| export-fraud-legal-dossier | YES (`buildDossierPaymentEvidence`) | NÃO se trace presente; disclaimer se ausente | era HIGH | **FIXED** |
| whatsapp_guardian | NO | Baixo (valor total sem NSU único) | LOW | DEFERRED |
| API ocorrência (campos legados) | YES (+ campos legados) | Campos legados ainda presentes | MEDIUM | documentado |

## NSU Semantics

- Campo WebPosto `nsu` é dado bruto real.
- Se `nsuTef` null e valor UUID → `nsu_kind = RAW_UUID_OR_TOKEN` (não rotular como NSU TEF clássico).
- Um raw NSU pertence ao **componente de cartão**, não ao total da venda.
- Dinheiro não recebe NSU.

## Tests

`tests/unit/test_fueling_settlement_trace.py` — cases A–J (10 passed).

Case J prova: `TRACE=EXPLAINED` e `LEGACY_SCORE=95` coexistindo.

## Live Validation

2026-08-10 · empresa 74014 · venda 366670631:

```
TRACE=EXPLAINED MIXED
fuelings=3 payments=3 cards=2
totals 408.73 / 408.73 / 408.73 EXACT/EXACT
LEGACY_SCORE=95 (esperado nesta sprint)
```

## Known Limitations

- Sem Operações PDV na API.
- Sem link estruturado fueling↔payment (não há match por valor).
- Score 95 permanece até FR-02.
- Cache FR-01 no worker cobre o dia corrente; histórico via endpoint dedicado.

## FR-02 Dependency

Revisar: limiar 10 min, MAX retention, agrupamento multi-bico, pagamentos mistos, peso de cada evidência — **somente após** FR-01 estável.

## Product Gate

**FR01_VALIDATED**
