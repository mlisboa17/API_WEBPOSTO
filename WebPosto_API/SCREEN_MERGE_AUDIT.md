# SCREEN MERGE AUDIT — P0.1-B

## Função auditada

`NetworkFinancialOverviewService._load_screen_expenses()`

---

## Fluxo ANTES (bug)

```text
DESPESAS_REDE row
  → _normalize_financeiro_screen_expense
  → linha origem=financeiro

CAIXA_REDE row + CAIXA_APRESENTADO (ap_map)
  → merge {row + ap_*}
  → _normalize_operational_screen_expense(origem=caixa, apresentado)
  → linha A origem=caixa R$135

  → _normalize_operational_screen_expense(origem=pdv, apurado)
  → linha B origem=pdv R$135

  → _apply_financeiro_matches (enriquece linha A com BOBINA)
  → linha C origem=caixa R$135 (descricao genérica escapa dedupe)

_dedupe_rows(keys inclui descricao) → 3 linhas operacionais
```

---

## Fluxo DEPOIS (corrigido)

```text
DESPESAS_REDE row
  → linha origem=financeiro (dedupe _EXPENSE_DEDUPE_KEYS)

CAIXA_REDE rows
  → _dedupe_closure_source_rows (empresa+data+caixa+turno+pdv)
  → merge com CAIXA_APRESENTADO
  → _normalize_closure_screen_expense (UMA linha)
     origem=caixa
     valor=despesaApurado
     despesaApurado / despesaApresentado / despesaDiferenca
  → _apply_financeiro_matches
  → dedupe _SCREEN_EXPENSE_DEDUPE_KEYS (sem descricao)
```

---

## Mapa registro → tela (caso 4343023)

| Etapa | Saída |
|-------|-------|
| CAIXA_REDE | caixaCodigo=4343023, pdv=15880, turno=1 |
| CAIXA_APRESENTADO | apurado=135, apresentado=135, diff=0 |
| Merge | chave (5555, 4343023) |
| Tela | **1 linha** caixa R$135, matchFinanceiro=Sim, BOBINA TERMICA |

---

## Ordem de fontes (inalterada)

1. `DESPESAS_FINANCEIRO_REDE`
2. Join `CAIXA_REDE`/`CAIXA` + `CAIXA_APRESENTADO`/`CAIXA_APRESENTADO_REDE`
3. Sem soma cross-origem no overview consolidado
