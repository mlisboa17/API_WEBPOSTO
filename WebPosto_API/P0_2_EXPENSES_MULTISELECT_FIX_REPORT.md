# P0.2 — Expenses Multiselect Fix Report

**Data:** 2026-06-08  
**Período de teste:** 2026-06-01 .. 2026-06-07  
**Backend:** http://127.0.0.1:8040

---

## 1. Arquivos corrigidos

| Arquivo | Mudança |
|---|---|
| `src/services/network_financial_overview_service.py` | Fix multiselect + single-fetch rede |
| `tests/unit/test_expense_multiselect_filter.py` | Testes unitários novos |
| `scripts/p0_2_validate_expenses_multiselect.py` | Validação automatizada casos A–D |
| `LOGOS_FINANCIAL_MODEL_1.0.md` | Modelo financeiro oficial |

---

## 2. Função corrigida

| Função | Correção |
|---|---|
| `_expense_matches_empresa()` | **Nova** — filtra por `empresa_codigo` ou `empresa_codigos` |
| `_expense_matches()` | Delega filtro empresa para `_expense_matches_empresa()` |
| `_fetch_despesas_rede()` | **Nova** — 1 chamada sem `empresaCodigo` (API ignora) |
| `_load_filtered_expenses()` | **Nova** — normaliza + filtra + dedupe em memória |
| `get_financial_expenses()` | Remove loop N× fetch; usa `_load_filtered_expenses()` |
| `get_financial_overview_only()` | 1 fetch despesas + agrupa por filial |
| `get_financial_overview()` | Usa `_resolve_empresas` + 1 fetch despesas |

---

## 3. Prova antes / depois

### Antes (P0 auditado)

| Caso | Registros | Empresas |
|---|---:|---|
| `11495` | 71 | `[11495]` ✅ |
| `11495,5555` | **415** | **10 filiais** ❌ |
| Todos | 415 | 10 filiais |

**Causa:** loop por filial + `_expense_matches` sem `empresa_codigos` → cada iteração aceitava rede inteira.

### Depois (P0.2 — execução real)

| Caso | Registros | Valor | Empresas |
|---|---:|---:|---|
| A `11495` | **71** | **R$ 24.676,71** | `[11495]` ✅ |
| B `5555` | **46** | **R$ 7.292,73** | `[5555]` ✅ |
| C `11495,5555` | **117** | **R$ 31.969,44** | `[11495, 5555]` ✅ |
| D Todos | **415** | **R$ 127.315,20** | 10 filiais ✅ |

**Evidência:** `scripts/p0_2_validation_result.json` — todos `pass: true`.

**Chamadas API:** 1× `CONSULTAR_DESPESAS_FINANCEIRO_REDE` por request de despesas (confirmado nos logs uvicorn).

---

## 4. Resultado empresa 11495

```text
71 registros | R$ 24.676,71 | apenas empresaCodigo 11495
```

---

## 5. Resultado empresa 5555

```text
46 registros | R$ 7.292,73 | apenas empresaCodigo 5555
```

---

## 6. Resultado multiselect 11495,5555

```text
117 registros | R$ 31.969,44
empresas: [5555, 11495]
NUNCA: 5256, 5333, 5556, 5557, 5559, 5560, 46433, 74014
```

Validação: 71 + 46 = 117 ✅

---

## 7. Resultado Todos

```text
415 registros | R$ 127.315,20
10 filiais: 5256, 5333, 5555, 5556, 5557, 5559, 5560, 11495, 46433, 74014
```

Nota: 415 vs 427 API bruta = 12 removidos por `_dedupe_rows` (dedupe intra-fonte, esperado).

---

## 8. Validação frontend

| Tela | Status | Observação |
|---|---|---|
| `view=expenses` | ✅ | Consome `/v1/financial/expenses` — herda fix backend |
| `view=dashboard` | ✅ | Overview usa mesmo pipeline despesas |
| `view=executive` | ✅ | KPIs despesas via analytics → `get_financial_expenses` |

**Sem alteração frontend necessária** — bug era 100% backend.

Filtros URL/multiselect já serializam `11495,5555` corretamente (`app.js`).

---

## 9. Validação CSV/PDF

Exportações usam `sortedRows` da tabela = mesmas linhas do backend.

| Export | Comportamento pós-fix |
|---|---|
| CSV despesas | = linhas filtradas backend ✅ |
| PDF despesas | = linhas filtradas backend ✅ |

---

## 10. Modelo financeiro oficial

Criado: **`LOGOS_FINANCIAL_MODEL_1.0.md`**

Define 7 fact tables, regras de dedupe intra-fonte, classificação Despesa Gerencial / Contas a Pagar / Caixa / Bancário / Auditoria.

---

## 11. Pronto para retomar A03.6?

| Critério | Status |
|---|---|
| Multiselect despesas P0 | ✅ Corrigido e provado |
| Single-fetch performance | ✅ 1 chamada WebPosto/des pesas |
| Modelo financeiro formal | ✅ LOGOS_FINANCIAL_MODEL_1.0 |
| Dedupe inter-fontes | ✅ Documentado — não misturar |
| FINANCEIRO_EXCLUSAO em BI | ❌ Ainda bloqueado (filtro data) |
| UX banner escopo rede | ⏳ Backlog A04 (opcional) |
| Titulo multiselect | ⏳ Fora escopo P0.2 — titulo_pagar ainda loop por filial |

### Veredicto

**Sim — pronto para retomar A03.6** no eixo despesas/multiselect.  
Pendências menores (UX banner, titulo multiselect) não bloqueiam estabilização operacional.

---

## Comandos de revalidação

```bash
python scripts/p0_2_validate_expenses_multiselect.py
python -m pytest tests/unit/test_expense_multiselect_filter.py -q
```
