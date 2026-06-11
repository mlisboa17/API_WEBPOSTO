# Release Packaging — F05.1

## ENTRAM (commit `6d345ed` — já aplicado)

| Arquivo | Motivo |
|---------|--------|
| `src/services/executive_decision_engine_service.py` | Motor principal F05.1 |
| `src/services/executive_decision_engine_snapshot_service.py` | Snapshot service |
| `src/interfaces/http/routes/executive_decision_engine.py` | API `/api/v1/executive-decision` |
| `src/interfaces/http/app.py` | Registro router |
| `frontend/pages/executiveDecision.js` | Cockpit `view=executive-decision` |
| `frontend/app.js`, `index.html`, `api.js` | Integração UI |
| `dw/ddl/fact_decision_engine.sql` | Modelo DW |
| `tests/unit/test_executive_decision_engine_service.py` | 9 testes |
| `scripts/audit_f05_1_executive_decision_engine.py` | Auditoria live |
| `scripts/generate_f05_1_reports.py` | Gerador relatórios |
| `scripts/f05_1_executive_decision_engine.json` | Evidência audit |
| `snapshots/executive_decision_engine/*.json` | Snapshot homologado |
| 10× `*_REPORT.md` F05.1 | Documentação sprint |

## NÃO ENTRAM

| Arquivo | Motivo |
|---------|--------|
| `.claude/worktrees/*` | Artefato local Claude |
| `*.log` | Logs de desenvolvimento |
| `__pycache__` / `*.pyc` | Cache Python |
| `htmlcov/` | Coverage local |

## Comando (já executado)

```bash
git add <25 arquivos F05.1>
git commit -m "feat(f05.1): executive decision engine with governance-backed actions"
git push origin feature/f05-1-executive-decision-engine
```

Status: **commit e push concluídos** (`6d345ed`).
