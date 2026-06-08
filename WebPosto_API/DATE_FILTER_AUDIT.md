# DATE_FILTER_AUDIT — Sprint P0

**Gerado:** 2026-06-08T12:57:30

## Pipeline global

- Frontend input: `type=date → YYYY-MM-DD`
- Frontend URL: `dataInicial & dataFinal na query string`
- Backend: `Query dataInicial/dataFinal str (sem conversão timezone)`
- WebPosto: `dataInicial/dataFinal repassados como recebidos`

## Issues globais

- **[P2]** default_periodo_utc: app.js define dataInicial/dataFinal com new Date().toISOString().slice(0,10) — em America/Sao_Paulo após 21h UTC vira dia seguinte.
- **[INFO]** display_utc_intentional: formatDate usa Date.UTC + timeZone UTC — evita shift na exibição de strings YYYY-MM-DD.

## Por tela

| View | Exibido | Enviado | Recebido | Timezone | Perda | Bug |
|---|---|---|---|---|---|---|
| executive | DD/MM/YYYY via formatDate (Intl pt-BR, t... | YYYY-MM-DD | YYYY-MM-DD | UTC display | False | — |
| fuels | DD/MM/YYYY via formatDate (Intl pt-BR, t... | YYYY-MM-DD | YYYY-MM-DD | UTC display | False | — |
| sales | DD/MM/YYYY via formatDate (Intl pt-BR, t... | YYYY-MM-DD | YYYY-MM-DD | UTC display | False | — |
| expenses | DD/MM/YYYY via formatDate (Intl pt-BR, t... | YYYY-MM-DD | YYYY-MM-DD | UTC display | False | — |
| accounts | DD/MM/YYYY via formatDate (Intl pt-BR, t... | YYYY-MM-DD | YYYY-MM-DD | UTC display | False | — |
| stock | DD/MM/YYYY via formatDate (Intl pt-BR, t... | YYYY-MM-DD | YYYY-MM-DD | UTC display | False | — |
| dashboard | DD/MM/YYYY via formatDate (Intl pt-BR, t... | YYYY-MM-DD | YYYY-MM-DD | UTC display | False | — |

## Conclusão

**Sem bug P0 de data comprovado** no pipeline principal. Risco P2: default `toISOString` no app.js para período inicial.
