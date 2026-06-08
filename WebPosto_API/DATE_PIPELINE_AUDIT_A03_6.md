# DATE_PIPELINE_AUDIT_A03_6

**Gerado:** 2026-06-08T14:44:37

## Padrão interno

**YYYY-MM-DD** em todo pipeline de filtros.

## Issues

- **[P2]** `frontend/app.js`: Default dataInicial/dataFinal via toISOString() — pode deslocar 1 dia após 21h BRT
- **[INFO]** `frontend/services/format.js`: Exibição usa Date.UTC + timeZone UTC — correto para strings YYYY-MM-DD
- **[INFO]** `frontend/services/export.js`: toLocaleString apenas no rodapé 'Gerado em' — não afeta filtros

## Por tela

| Tela | Enviado | Exibido | Bug P0 |
|---|---|---|---|
| executive | YYYY-MM-DD (query dataInicial/... | DD/MM/YYYY UTC | Não |
| dashboard | YYYY-MM-DD (query dataInicial/... | DD/MM/YYYY UTC | Não |
| expenses | YYYY-MM-DD (query dataInicial/... | DD/MM/YYYY UTC | Não |
| accounts | YYYY-MM-DD (query dataInicial/... | DD/MM/YYYY UTC | Não |
| sales | YYYY-MM-DD (query dataInicial/... | DD/MM/YYYY UTC | Não |
| stock | YYYY-MM-DD (query dataInicial/... | DD/MM/YYYY UTC | Não |
| fuels | YYYY-MM-DD (query dataInicial/... | DD/MM/YYYY UTC | Não |
| financial | YYYY-MM-DD (query dataInicial/... | DD/MM/YYYY UTC | Não |

## Padrões JS encontrados

- `app.js`: {'toISOString': 2, 'new Date()': 2, 'toLocaleString': 0, 'localeDateString': 0}
- `format.js`: {'toISOString': 0, 'new Date()': 1, 'toLocaleString': 0, 'localeDateString': 0}
- `filters.js`: {'toISOString': 0, 'new Date()': 0, 'toLocaleString': 0, 'localeDateString': 0}
- `snapshotService.js`: {'toISOString': 1, 'new Date()': 2, 'toLocaleString': 0, 'localeDateString': 0}
- `export.js`: {'toISOString': 0, 'new Date()': 1, 'toLocaleString': 1, 'localeDateString': 0}

**Conclusão:** Sem bug P0 de data comprovado no pipeline de filtros
