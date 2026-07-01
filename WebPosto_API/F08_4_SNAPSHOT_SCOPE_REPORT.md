# F08.4 Snapshot Scope Audit — IA-3

---

## Snapshots analisados

| Path | Necessário F08.4? | Classificação | Notas |
|------|-------------------|---------------|-------|
| `snapshots/financial/*` | **Sim** | **Obrigatório (runtime)** | Fonte de evidência via `financial_intelligence_evidence.py`. Não criados pela F08.4; herdados F08.0–F08.3. |
| `snapshots/cash_flow/*` | Não | **Não pertence** | Usado por `CorporateCashFlowService` / rotas legacy. F08.4 cash flow intelligence deriva de `financial_overview` + receivables, não deste path. |
| `snapshots/goals_campaign_engine/*` | Não | **Não pertence** | Metas executivas — sprint distinta. |
| `snapshots/operator_performance/*` | Não | **Não pertence** | Performance PDV — sprint distinta. |
| `snapshots/operator_profitability/*` | Não | **Não pertence** | ROI operador — sprint distinta. |
| `snapshots/people_intelligence/*` | Não | **Não pertence** | People intelligence — sprint distinta. |
| `snapshots/non_fuel_products/*` | Não | **Não pertence** | Commercial/products — sprint distinta. |
| `snapshots/product_master_cache/*` | Não | **Não pertence** | Cache catálogo — artefato operacional local. |

---

## Respostas diretas

| Pergunta | Resposta |
|----------|----------|
| Necessário para F08.4? | Apenas **`snapshots/financial/`** (já existente) |
| Opcional? | Nenhum dos listados na spec é opcional para F08.4 |
| Não pertence? | **Todos os 7 grupos** listados na IA-3 (exceto `financial/`) |

---

## Risco

Incluir snapshots de outras áreas no commit F08.4:

- Aumenta diff e ruído de review
- Pode mascarar regressões em módulos não relacionados
- **Não quebra** F08.4 runtime (engines não leem esses paths)

**Recomendação:** remover do histórico F08.4 em commit futuro de limpeza ou revert seletivo; manter apenas `snapshots/financial/` como dependência documentada.
