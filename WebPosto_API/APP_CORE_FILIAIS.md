# APP_CORE — Filiais LOGOS SPACE

Fonte única versionada da rede de postos. **Sem consulta WebPosto live.**

## Catálogo oficial (12)

| Nome Fantasia | COD WEB / empresaCodigo | CNPJ | Ativa | Status Evidência | Snapshot |
|---------------|-------------------------|------|-------|------------------|----------|
| POSTO VIP | 11495 | 03.008.754/0001-86 | Sim | COMPROVADA | Ativa |
| AP CASA CAIADA | 5555 | 04.284.939/0001-86 | Sim | COMPROVADA | Ativa |
| POSTO BR SHOPPING | 5256 | 07.018.760/0001-75 | Sim | COMPROVADA | Ativa |
| POSTO JANGA | 5333 | 05.428.059/0002-80 | Sim | COMPROVADA | Ativa |
| POSTO CIDADE PATRIMONIO | 5556 | 05.428.059/0001-07 | Sim | COMPROVADA | Ativa |
| POSTO ENSEADA DO NORTE | 5557 | 00.338.804/0001-03 | Sim | COMPROVADA | Ativa |
| POSTO REAL | 5558 | 24.156.978/0001-05 | Não | COMPROVADA | Fora snapshot |
| POSTO RJ | 5559 | 08.726.064/0001-86 | Sim | COMPROVADA | Ativa |
| POSTO SERTÃ | 5560 | 04.274.378/0001-34 | Sim | COMPROVADA | Ativa |
| POSTO DOZE | 46433 | 52.308.604/0001-01 | Sim | COMPROVADA | Ativa |
| POSTO DOZE FILIAL II | 74014 | 52.308.604/0002-84 | Sim | COMPROVADA | Ativa |
| AUTO POSTO GLOBO | PENDENTE_41043647000188 | 41.043.647/0001-88 | Não | PENDENTE_EVIDENCIA | Fora snapshot |

## Regras

- `empresaCodigo` = COD WEB (quando homologado)
- UI deve exibir **Nome Fantasia**, nunca código bruto
- Filial ausente no master → **não inventar**
- Evidência ausente → `PENDENTE_EVIDENCIA` (não entra em listas operacionais do frontend)
- Evidência completa → `COMPROVADA` (pode estar inativa, ex.: POSTO REAL)

## Artefatos

```text
app_core/filial_registry.py
scripts/sync_filiais_manifest.py
frontend/data/filiais.json
frontend/filiais.js
```

## Sincronização

```bash
python scripts/sync_filiais_manifest.py
python scripts/audit_app_core_filiais.py
python -m pytest tests/unit/test_filial_registry_parity.py -q
```

## Pendências

1. **AUTO POSTO GLOBO** — aguardando COD WEB / empresaCodigo homologado
2. **POSTO REAL (5558)** — inativa; mantida no registry por histórico

## Fonte

- Master: `src/domain/entities/filial_master.py`
- Snapshot: `snapshots/executive/` → `kpis.empresasCodigos`
