# DIR-01 — Validation Report (fase nominal)

**Data:** 2026-07-05  
**Branch:** `feature/build-03-trust-home`  
**Decisão:** `175da101-6f68-42f4-9d2b-9b42e6cedea2` (VALUE-03 · POSTO DOZE FILIAL II · 74014)

## Entrega runtime (API real + snapshot owner)

| # | Item | Resultado |
|---|------|-----------|
| 1 | Fonte nominal encontrada | **CAIXA + CAIXA_APRESENTADO** (`valeFunApurado` por turno) + **FUNCIONARIO** (nome por código) |
| 2 | evidence_items | **16** · R$ **8.401,00** |
| 3 | EXACT | **0** |
| 4 | PROBABLE | **3** |
| 5 | AMBIGUOUS | **0** |
| 6 | NO_MATCH | **13** |
| 7 | Com funcionário | **3** |
| 8 | Com caixa | **3** |
| 9 | Com turno | **3** |
| 10 | Total c/ funcionário | **R$ 450,00** |
| 11 | Total s/ funcionário | **R$ 7.951,00** |
| 12 | Tela validada runtime | **SIM** — `GET /api/v1/decisions/{id}/evidence` → 200; frontend `decisionDetail.js` com badges |
| 13 | Limitações | Vale consolidado sem beneficiário na DESPESAS_REDE; match via total turno (não linha a linha); VALE_FUNCIONARIO_REDE (401) indisponível |
| 14 | Parecer final | **PARCIAL** — 3/16 vales R$150 com operador+turno; 13 lançamentos (R$7.951) exigem fonte complementar |

Evidência JSON: `docs/validation/DIR_01_RUNTIME.json`

## Fontes auditadas

| Fonte | Resultado |
|-------|-----------|
| DESPESAS_FINANCEIRO_REDE | 16 lançamentos · sem `funcionarioCodigo` |
| CAIXA / CAIXA_REDE | `funcionarioCodigo`, `caixaCodigo`, `turno` por fechamento |
| CAIXA_APRESENTADO | `valeFunApurado` agregado por turno — candidato nominal |
| FUNCIONARIO | Nome resolvido por código |
| VALE_FUNCIONARIO_REDE | **401** — não disponível no token |
| MOVIMENTO_CONTA / VENDA_FORMA_PAGAMENTO | Sem vínculo linha a linha para vales consolidados |
| Prestação de Contas (parser) | Complementar necessária para 13 NO_MATCH |

## DIR-01C (Prestação markdown)

Ver `docs/validation/DIR_01C_NOMINAL_EVIDENCE_ENRICHMENT.md` — cobertura nominal inalterada (**5,4%**).

## DIR-01D (Executive Review Request)

Ver `docs/validation/DIR_01D_EXECUTIVE_REVIEW_RUNTIME.md` — solicitação real com idempotência; fronteira Diretoria→Financeiro.

## Matches PROBABLE (amostra real)

| Data | Valor | Funcionário | Caixa | Turno |
|------|-------|-------------|-------|-------|
| 2026-06-14 | R$ 150 | DOUGLAS HENRIQUE CABRAL ISIDRO ARAU | 4346306 | 1º TURNO |
| 2026-06-18 | R$ 150 | RYAN HENRIQUE SILVA DE AZEVEDO | 4354022 | 1º TURNO |
| 2026-06-25 | R$ 150 | RYAN HENRIQUE SILVA DE AZEVEDO | 4359778 | 1º TURNO |

## Testes

`tests/unit/test_decision_evidence.py` — matcher + builder (5 passed, integration opcional)

## Pergunta final

**"Agora o diretor consegue saber quais lançamentos formaram o alerta e quem precisa conferir cada item?"**

**NÃO** — parcialmente. Os 16 lançamentos e R$ 8.401 estão visíveis; apenas **3** (R$ 450) têm funcionário/turno identificados honestamente. Os **13** restantes permanecem **não identificados** até VALE_FUNCIONARIO_REDE ou Prestação de Contas.
