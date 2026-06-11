# EXPENSES SCREEN — BACKEND AUDIT

**Data:** 2026-06-09  
**Caso QA:** AP CASA CAIADA (5555) · 08/06/2026

---

## 1. Qual endpoint a tela chama?

| Camada | Artefato |
|--------|----------|
| Frontend | `fetchFinancialExpenses()` → `GET /v1/financial/expenses` |
| Rota | `src/interfaces/http/routes/fechamento_enterprise.py` → `financial_expenses` |
| Serviço | `NetworkFinancialOverviewService.get_financial_expenses()` |

A tela **não** usa `/api/v1/finance/center/expenses` nem `/api/v1/cash/operations/*` para listagem tabular.

---

## 2. Qual serviço monta os dados?

**Antes (bug):** `_load_filtered_expenses()` — uma única chamada a `CONSULTAR_DESPESAS_FINANCEIRO_REDE`.

**Depois (P0):** `_load_screen_expenses()` — consolidação multi-origem com merge `CAIXA(_REDE)` + `CAIXA_APRESENTADO(_REDE)`.

`_load_filtered_expenses()` **permanece intacto** para overview / Finance Center (regras consolidadas).

---

## 3. Qual filtro estava sendo aplicado?

| Filtro | Estado antes | Estado depois |
|--------|--------------|---------------|
| `empresaCodigo` | OK (P0.2 multiselect) | OK |
| `dataInicial/dataFinal` | OK | OK |
| `origem` | Parâmetro existia na rota, **sem fontes caixa/pdv** | Funcional com 3 origens |
| `texto` | **Ausente** | Adicionado |
| `financeiro/desconhecido/BOBINA` | **Não hardcoded no backend** | Sem filtro implícito |
| Paginação API | `limit` até 500; frontend agrega páginas | Mantido |

O sintoma “só BOBINA R$ 135” vinha da **fonte única financeira** + provável filtro client-side na tabela (`status=desconhecido`, busca textual).

---

## 4. Qual origem de dados era usada?

| Antes | Depois |
|-------|--------|
| `DESPESAS_FINANCEIRO_REDE` apenas | + `CAIXA_APRESENTADO` / `CAIXA_APRESENTADO_REDE` → `origem=caixa` |
| | + `CAIXA` / `CAIXA_REDE` + merge apresentado → `origem=pdv` |

---

## 5. Por que só retornava 1 registro?

1. **Causa principal:** endpoint listava somente despesas financeiras de rede; despesas operacionais de turno (caixa/PDV) nunca eram carregadas.
2. **Caso 5555 / 08-06-2026:** rede financeira tinha **2** lançamentos (R$ 1.912,00); a UI mostrava **1** (BOBINA R$ 135) — restante filtrado/oculto na tabela.
3. **Após P0:** **5** registros — financeiro 2 · caixa 2 · pdv 1 (evidência: `scripts/p0_expenses_screen_validation.json`).

---

## Evidência API (5555 · 08/06/2026)

```text
total: 5
financeiro: 2 · R$ 1.912,00
caixa:      2 · R$ 270,00
pdv:        1 · R$ 135,00
BOBINA TERMICA: presente
```
