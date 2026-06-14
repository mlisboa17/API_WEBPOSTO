# IA-7 — Snapshot-First Guard

## Flag

```python
WebPostoClient(..., allow_live: bool = False)
```

## Comportamento

| allow_live | request() / wrappers |
|------------|----------------------|
| `False` (default) | `WebPostoSnapshotGuardError` — bloqueia HTTP |
| `True` | Permite chamada live (scripts de auditoria) |

## Motores F03–F07

- **Não migrados** nesta onda
- Continuam usando snapshots homologados + `src/gateway/webposto_client.py` legado
- Gateway root (`gateway/`) é **facade incremental** para próximas ondas

## Integração Onda 1

- Filiais oficiais: `app_core.filial_registry`
- Gateway aceita `empresa_codigo` sem assumir token=filial
