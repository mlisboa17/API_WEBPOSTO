# WEBPOSTO_FULL_AUDIT_P0

**Gerado:** 2026-06-08T13:00:44
**Backend:** http://127.0.0.1:8040

---

## 1. Por que as despesas estão divergentes?

A API **`CONSULTAR_DESPESAS_FINANCEIRO_REDE` ignora `empresaCodigo`** e retorna sempre a rede inteira.
Ao comparar WebPosto UI (visão rede) com LOGOS (filial 11495 selecionada), parece que faltam despesas — na verdade são **de outras filiais**.

## 2. Onde os registros desaparecem?

| Camada | Perda comprovada | Contexto |
|---|---|---|
| API ignora `empresaCodigo` | **Sim** | 427 rede vs 71 filial 11495 (01–07/06) |
| Backend single-filial | **Não** | 71 = correto para 11495 |
| Backend multiselect | **Sim — BUG** | `11495,5555` retorna 415 (10 filiais), igual a "todas" |
| Normalização | 0 descartados | — |
| Dedupe (visão rede) | 44 descartados | Colisões em chave composta |
| Frontend/export | **Não** | Tabela = backend = CSV/PDF |

## 3. Existe problema de data?

**Não P0 comprovado.** Pipeline YYYY-MM-DD ponta a ponta. Risco P2: default período via `toISOString()` (UTC). Ver `DATE_FILTER_AUDIT.md`.

## 4. Existe problema de filtro?

**Sim — dois pontos comprovados:**

1. **API WebPosto:** `empresaCodigo` ignorado em `DESPESAS_FINANCEIRO_REDE`
2. **Backend LOGOS multiselect despesas:** `_expense_matches` não usa `empresa_codigos` no loop — multiselect retorna rede inteira (415 = todas)

Single-filial funciona (71 só 11495). Ver `FILTER_AUDIT_REPORT.md`.

## 5. Existe problema de snapshot?

Snapshots respondem HTTP 200. Executive fromSnapshot=False. 
Snapshot financial é agregado — não substitui contagem linha a linha de despesas. **Não é causa raiz** das despesas faltantes.

## 6. Existe problema de exportação?

**Não comprovado.** Export CSV/PDF usa mesmas linhas da tabela (sortedRows).

## 7. Qual tela está mais crítica?

**EXPENSES** — percepção de dados incompletos (escopo rede vs filial) + **bug multiselect backend**.  
**EXECUTIVE / FUELS** — PARCIAL: snapshot vazio (`fromSnapshot=False`), mas KPIs/DRE/data-quality respondem HTTP 200 com dados (~9–19s).  
Telas **OK**: sales, expenses (single-filial), accounts, stock, dashboard.

## 8. Quais telas estão estáveis?

sales, expenses, accounts, stock, dashboard

## 9. Quais endpoints de rede podem aumentar cobertura?

`TituloPagarRede`, `ContaRede`, `MovimentoConta`, `DespesasFinanceiroRede`, `VendaRede`, `VendaItem`, `VendaFormaPagamento`, `AbastecimentoRede`

## 10. Quais endpoints devem entrar no BI?

DESPESAS_FINANCEIRO_REDE, VENDA, PRODUTO_ESTOQUE, LMC_REDE, TITULO_PAGAR, MOVIMENTO_CONTA, EMPRESAS.

## 11. Vale utilizar Postman?

Sim — smoke tests e evidência para Quality. Ver `POSTMAN_STRATEGY.md`.

## 12. Próxima correção prioritária

1. **Backend P0:** corrigir `_expense_matches` / loop multiselect — filtrar por `empresaCodigo` da iteração ou `empresa_codigos`
2. **Backend:** 1 fetch despesas + filtro client-side (eliminar N×427 chamadas)
3. **UX:** banner "endpoint retorna rede; exibindo N de M da filial selecionada"
4. **Quality:** solicitar API honrar `empresaCodigo` em DESPESAS_REDE
5. Revisar dedupe em visão multi-filial (44 colisões)

---

## Evidência quantitativa — período 01/06–07/06, filial 11495

| Fonte | Registros | Valor |
|---|---:|---:|
| API bruta (rede) | 427 | 135761.20 |
| Backend LOGOS | 71 | 24676.71 |
| Após normalização | 383 | 123899.40 |

## Períodos auditados

- **dia_06_06**: API rede=52, backend 11495=8, valor=846.10
- **semana_01_07**: API rede=427, backend 11495=71, valor=24676.71
- **ultimos_30_dias**: API rede=1660, backend 11495=334, valor=103792.68

## Cobertura filiais alvo

- **5256**: 2 endpoints com dados
- **5333**: 2 endpoints com dados
- **5555**: 14 endpoints com dados
- **5556**: 1 endpoints com dados
- **5557**: 2 endpoints com dados
- **5558** (INATIVA desde 20/05/2026): 0 endpoints com dados
- **5559**: 2 endpoints com dados
- **5560**: 2 endpoints com dados
- **11495**: 17 endpoints com dados
- **46433**: 2 endpoints com dados
- **74014**: 2 endpoints com dados
