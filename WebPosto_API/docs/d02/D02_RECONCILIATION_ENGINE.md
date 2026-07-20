# D02 — Reconciliation Engine (Agente 6)

> Motor de **pré-conferência interna** — [D02_CONCEPTUAL_CORRECTION.md](./D02_CONCEPTUAL_CORRECTION.md)

## Componentes

| Módulo | Path |
|---|---|
| Domínio | `src/domain/reconciliation/` |
| Service | `src/services/cash_reconciliation/cash_reconciliation_service.py` |
| Pré-conferência | `pre_reconciliation_engine.py` |
| Snapshot | `cash_reconciliation_snapshot_service.py` |
| Router | `src/interfaces/http/routes/cash_reconciliation.py` |

## Fluxo

```text
WebPosto CAIXA + CAIXA_APRESENTADO + VFP + DESPESAS
        ↓
build_items() — 1 item por turno × natureza com movimento
        ↓
PreReconciliationEngine — AUTO_MATCH / NEEDS_REVIEW / DIVERGENT
        ↓
AuditSignalEngine — sinais determinísticos
        ↓
summary + exceptions → API + frontend
```

## Estratégias por natureza

`nature_strategies.py` — tolerância R$ 0,01; limiar divergente R$ 10,00; DINHEIRO considera sangria; CARTAO exige breakdown VFP quando disponível.

## Performance

Snapshot-first TTL 300s; reutiliza `CashOperationsService._fetch_merged`.
