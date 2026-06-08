# A04-PREP / F01 — FINANCE CENTER API REPORT

**Sprint:** A04-Prep / F01  
**Gerado:** 2026-06-08  
**Período validado:** 2026-06-01 .. 2026-06-07  
**Evidência:** `scripts/validate_f01_results.json` (validação direta serviço + WebPosto live)

---

## 1. Endpoints criados

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/v1/finance/center/summary` | Resumo corporativo (blocos separados) |
| GET | `/api/v1/finance/center/expenses` | Despesas gerenciais + `categoriaLogos` |
| GET | `/api/v1/finance/center/payables` | Contas a pagar por bucket |
| GET | `/api/v1/finance/center/receivables` | Contas a receber por bucket |
| GET | `/api/v1/finance/center/bank-movements` | Movimento bancário classificado |
| GET | `/api/v1/finance/center/cash` | Operação de caixa (CAIXA + APRESENTADO) |

**Arquivos:**
- `src/interfaces/http/routes/finance_center.py`
- `src/services/corporate_finance_center_service.py`
- `src/services/logos_expense_classifier.py`

**Registro:** `src/interfaces/http/app.py` → `finance_center.router`

> **Deploy:** reiniciar uvicorn na porta **8040** para expor as rotas HTTP (servidor atual retorna 404 — código anterior em memória).

---

## 2. Fontes usadas

| Bloco LOGOS | Endpoint WebPosto | Fetch |
|---|---|---|
| Despesas gerenciais | `CONSULTAR_DESPESAS_FINANCEIRO_REDE` | 1× rede |
| Contas a pagar | `TITULO_PAGAR` | 1× rede (filtro client-side) |
| Contas a receber | `TITULO_RECEBER` | 1× rede |
| Movimento bancário | `MOVIMENTO_CONTA` | paginação `ultimoCodigo` (até 10 páginas) |
| Caixa | `CAIXA` + `CAIXA_APRESENTADO` | 2× paralelo, filtro client-side |

**Regra respeitada:** nenhuma soma entre fontes; summary expõe blocos independentes (sem `totalFinanceiro`).

---

## 3. Filtros suportados

| Filtro | Summary | Expenses | Payables | Receivables | Bank | Cash |
|---|---|---|---|---|---|---|
| `dataInicial` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `dataFinal` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `empresaCodigo` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `centroCusto` | — | ✓ | — | — | — | — |
| `planoConta` | — | ✓ | — | — | — | — |
| `categoriaLogos` | — | ✓ | — | — | — | — |
| `page` / `limit` | — | ✓ | ✓ | ✓ | ✓ | — |

`empresaCodigo`: valor único, CSV (`11495,5555`), vazio ou `Todos` → rede disponível.

---

## 4. Multiselect funcionando

Validação live (despesas, `limit=500`):

| Caso | Registros | Empresas |
|---|---:|---|
| Todos | **419** | 10 filiais |
| 11495 | **73** | só 11495 |
| 5555 | **46** | só 5555 |
| 11495,5555 | **119** | 11495 + 5555 |

Padrão: **1 fetch rede** + filtro backend (P0.2 preservado).

---

## 5. Categorias LOGOS criadas

Campo novo: **`categoriaLogos`** em despesas (não sobrescreve plano WebPosto).

| Categoria | Valor período (R$) |
|---|---:|
| OPERACIONAL | 4.420,31 |
| PESSOAL | 53.689,01 |
| COMPRAS | 5.681,12 |
| FINANCEIRO | 87,50 |
| COMERCIAL | 6,00 |
| OUTROS | 63.883,26 |

Classificador: `src/services/logos_expense_classifier.py`

---

## 6. Dados por fonte (01–07/06/2026)

| Fonte | Volume | Destaques |
|---|---|---|
| Despesas | 419 reg / R$ 127.767 | 10 filiais |
| Contas pagar | 70 títulos | Aberto R$ 311k; Pago 7; Vencido 31; A vencer 32 |
| Contas receber | **11** títulos / R$ 176,31 | 11 pendentes; 6 vencidos |
| Movimento bancário | **2.000** movimentos (10 páginas) | Crédito/débito + tarifas/transferências |
| Caixa | **21** turnos | Despesa caixa R$ 4.949; Vale func. R$ 19.879 |

---

## 7. Performance

| Endpoint / operação | ms (live) |
|---|---:|
| Expenses (Todos, 1º call c/ discovery) | ~24.000* |
| Expenses (filial) | ~1.200 |
| Summary (paralelo 5 fontes) | ~14.500 |
| Payables / Receivables | ~340–2.600 |
| Bank (10 páginas) | ~6.400 |
| Caixa (2 fontes) | ~860 |

\* primeira chamada inclui discovery de permissões WebPostoClient.

**Snapshot keys** definidas (persistência futura):
`finance:center:{module}:{dataInicial}:{dataFinal}:{empresaCodigo}`

---

## 8. Limitações

1. **8040** precisa restart para rotas HTTP novas.
2. `fundoCaixa` / sangria / suprimento — **indisponíveis** na API CAIXA.
3. Movimento bancário: cap de **10 páginas** (2.000 reg) no serviço atual.
4. Classificação LOGOS por keywords — **OUTROS** ainda alto (~50%); revisão manual recomendada.
5. Endpoints legados `/v1/financial/*` **inalterados** (contas pagar legado ainda faz loop N filiais).

---

## 9. Pronto para tela Centro Financeiro?

**Sim — backend pronto.** Falta apenas:
- Reiniciar API 8040
- Tela consumir `/api/v1/finance/center/*` (fora do escopo F01)
- Cache Snapshot First (chaves definidas, TTL 5min recomendado)

---

## 10. Pronto para DW?

**Parcialmente.** Facts separados validados; DW pode modelar:
- `fact_despesa_gerencial`
- `fact_titulo_pagar` / `fact_titulo_receber`
- `fact_movimento_conta`
- `fact_caixa_turno`

Aguardar F01 em produção + persistência snapshot antes do pipeline A04.

---

## 11. Próxima sprint recomendada

**A04 / F01.1 — Snapshot + Tela Centro Financeiro**
1. Persistir snapshot TTL 5min (`SnapshotStore`)
2. Tela holding (blocos separados, sem total único)
3. Otimizar summary (cache warm, reduzir páginas MOVIMENTO no summary)
4. Expandir classificador LOGOS (planoContaGerencialCodigo lookup)

---

## Testes

- Unitários: `tests/unit/test_finance_center_service.py` — **5 passed**
- Validação live: `python scripts/validate_f01_finance_center_direct.py` — **11/11 PASS**

---

## Contratos preservados

- Dashboards existentes: **não alterados**
- `/v1/financial/expenses`, `/accounts-payable`, etc.: **não alterados**
- Dados WebPosto: **somente leitura**
