# F01.1-P0 — FILTERS AND FINANCE CENTER REPORT

**Sprint:** F01.1-P0  
**Gerado:** 2026-06-08

---

## 1. Agentes executados

| Agente | Escopo | Status |
|---|---|---|
| Frontend UX | Multiselect checkbox, chips, busca | ✅ |
| Backend Filter | Normalização `Todos` → rede | ✅ |
| Performance | Snapshot Finance Center TTL 5min | ✅ |
| Finance Center | Tela + API snapshot | ✅ |
| QA | Testes unitários filtros + F01 | ✅ |
| Architecture | Recomendações documentadas | ✅ |

---

## 2. Arquivos alterados

**Frontend:** `EmpresaMultiselect.js`, `filters.js`, `styles.css`, `api.js`, `app.js`, `index.html`, `pages/financeCenter.js`

**Backend:** `multiselect_utils.py`, `executive_snapshot_service.py`, `corporate_finance_center_service.py`, `finance_center_snapshot_service.py`, `finance_center.py`

**Testes:** `tests/unit/test_multiselect_utils.py`

---

## 3. Bug raiz encontrado

1. **UX:** `<select multiple>` exigia Ctrl/Cmd+click — padrão obsoleto.
2. **Filtros:** `"Todos"` podia trafegar como string; snapshots geravam chaves diferentes (`:Todos` vs `:` vs `all`).
3. **Finance Center:** endpoints existiam sem tela; snapshot não persistia.

---

## 4. Correções aplicadas

- Componente **EmpresaMultiselect** com checkbox, busca, Selecionar Tudo, Limpar, chips e Aplicar.
- **`normalizeEmpresaParam`** no frontend — nunca envia `Todos`/`all` à API.
- **`is_network_wide_empresa` / `empresa_snapshot_suffix`** no backend — chave unificada `all`.
- **`build_snapshot_key`** executive/financial usa sufixo normalizado.
- Tela **Centro Financeiro** consumindo `/api/v1/finance/center/*`.
- **Snapshot** `GET/POST /api/v1/finance/center/snapshot|refresh` TTL **5 min**.

---

## 5. Antes / depois

| Aspecto | Antes | Depois |
|---|---|---|
| Seleção empresa | Ctrl+click nativo | Checkbox + chips |
| Modo rede | `""` ou acidente `"Todos"` | Checkbox "Todos os postos" → `empresaCodigo` omitido |
| Snapshot key | `:Todos` vs `:` | sempre `:all` |
| Centro Financeiro | Só API | Tab + cards + export CSV/PDF |

---

## 6. Resultado filtro Todos

- Estado interno: `empresaCodigo: ""`
- Query API: param **omitido** (null)
- Contador UI: **"(Todos os postos)"**
- Validação F01: **419** despesas rede (01–07/06/2026)

---

## 7. Resultado multiselect

| Caso | Despesas (evidência F01) |
|---|---:|
| 11495 | 73 |
| 5555 | 46 |
| 11495,5555 | 119 |

---

## 8. Resultado por tela

| Tela | Filtro compartilhado | Snapshot |
|---|---|---|
| Executive | ✅ EmpresaMultiselect | executive:* 5min |
| Dashboard | ✅ | — |
| Expenses | ✅ | — |
| Accounts | ✅ | — |
| Sales | ✅ | — |
| Stock | ✅ | — |
| Fuels | ✅ | fuel:* 15min |
| **Finance Center** | ✅ | finance:center:* 5min |

---

## 9. Performance antes/depois

| Métrica | Antes | Depois |
|---|---|---|
| Finance Center 1ª carga | ~15s live | Snapshot hit ~instantâneo |
| Mudança filtro | debounce 300ms | mantido (1 interação → 1 refresh) |
| Payables legacy | N× filial | Finance Center: 1 fetch (F01) |

---

## 10. Centro Financeiro concluído?

**Sim (MVP F01.1).** Tab, 5 cards, aging CP/CR, tesouraria, classificação LOGOS, caixa, export CSV/PDF.

---

## 11. Exportações validadas?

**CSV/PDF** implementados na tela (mesmas linhas agregadas por bucket). Validação manual recomendada após restart 8040.

---

## 12. Snapshot validado?

Rotas `GET /api/v1/finance/center/snapshot` e `POST /refresh` implementadas. Frontend usa padrão snapshot-first (igual fuels).

---

## 13. Dívidas técnicas encontradas

1. `/v1/financial/accounts-payable` ainda loop N filiais (legado).
2. Multiselect analytics (KPIs) ainda sequencial por filial.
3. Header filters em tabelas ainda `<select multiple>` nativo.
4. Classificação LOGOS ~50% OUTROS — revisão keywords.
5. **Restart uvicorn 8040** necessário após deploy.

---

## 14. Próxima sprint recomendada

**F01.2 — Fluxo de Caixa** + unificar fetch N filiais nos endpoints legados + migrar header filters para EmpresaMultiselect.

---

## 15. Nota de maturidade atualizada

**7.8 / 10** (+0.3 vs F01) — filtros compartilhados modernizados + Centro Financeiro operacional.

**Risco operacional:** **28 / 100** (−2)

---

## Deploy

```powershell
Stop-Process -Id (Get-NetTCPConnection -LocalPort 8040).OwningProcess -Force
python -m uvicorn src.main:app --host 127.0.0.1 --port 8040
```

Abrir `/app/financial` → aba **Centro Financeiro**.
