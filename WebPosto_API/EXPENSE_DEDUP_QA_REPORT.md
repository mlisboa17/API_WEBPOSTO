# EXPENSE DEDUP QA REPORT — P0.1-B

**Caso:** AP CASA CAIADA · 5555 · 08/06/2026

---

## Cenário confirmado: **A — Duplicidade corrigida**

| Métrica | Antes | Depois |
|---------|------:|-------:|
| Caixa qtd | 2 | **1** |
| Caixa valor | R$ 270,00 | **R$ 135,00** |
| PDV qtd | 1 | **0** (incorporado na linha caixa) |
| Total qtd | 5 | **3** |
| Total valor | R$ 2.317,00 | **R$ 2.047,00** |

---

## Detalhe pós-correção

```text
financeiro: 2 registros · R$ 1.912,00 (BOBINA + FARDAMENTOS)
caixa:      1 registro  · R$ 135,00  (fechamento 4343023, match BOBINA)
```

---

## Paridade canais

| Canal | Status |
|-------|--------|
| API `/v1/financial/expenses` | ✅ baseline |
| Tabela UI | ✅ mesmo payload |
| CSV/PDF | ✅ export = rows renderizadas |
| Snapshot overview | ✅ não alterado |

**Diferença:** R$ 0,00 entre tabela e API (mesma fonte).

---

## Testes automatizados

```text
tests/unit/test_screen_expenses_closure_dedup.py — 2/2 OK
tests/unit/test_screen_expenses_consolidation.py — 3/3 OK
Total dedup-related: 5/5 OK
```

---

## QA Veredito

**APROVADO** — Cenário A validado com evidência quantitativa.
