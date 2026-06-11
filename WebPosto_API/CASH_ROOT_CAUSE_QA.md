# CASH ROOT CAUSE QA — F02.1-B

**Tolerância máxima diferença reconciliação:** 0,00

| Validação | Resultado |
|-----------|-----------|
| JSON audit gerado | ✅ `f02_1b_root_cause.json` |
| Relatórios MD (10 agentes) | ✅ gerados |
| merged 7d | 21 registros |
| Turnos com diff ≠ 0 | 21 |
| dinheiroDiferenca = diferenca (7d) | ✅ PASS |
| Janelas 7/30/90d | ✅ |
| Janela 365d | ⚠️ Omitida via --skip-365 |
| READ ONLY | ✅ apenas GET / SELECT |

**Veredito QA:** APROVADO
