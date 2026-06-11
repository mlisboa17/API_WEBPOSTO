# Commit Scope Validation — F05.1

## Arquivos esperados vs commitados

| Esperado | Commitado |
|----------|-----------|
| `executive_decision_engine_service.py` | Sim |
| `executive_decision_engine_snapshot_service.py` | Sim |
| `executive_decision_engine.py` (route) | Sim |
| `executiveDecision.js` | Sim |
| `fact_decision_engine.sql` | Sim |
| `test_executive_decision_engine_service.py` | Sim |
| `audit_f05_1_executive_decision_engine.py` | Sim |
| Relatórios F05.1 (10 MDs) | Sim |
| Integração frontend/API | Sim (`app.js`, `index.html`, `api.js`) |

## Fora do escopo no commit

Nenhum arquivo fora da F05.1 no commit `6d345ed`.

## Mistura de sprint

- **Commit isolado:** apenas F05.1 (25 arquivos)
- **Branch vs develop:** contém D04/D05/F03–F05 anteriores (base da branch) — esperado para PR consolidado, não mistura no commit F05.1

## Órfãos

Nenhum arquivo órfão no commit.
