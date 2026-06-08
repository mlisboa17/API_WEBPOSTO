# POSTMAN_STRATEGY — Sprint P0

**Gerado:** 2026-06-08T13:00:44

## Vale utilizar Postman?

**Sim, como complemento** — não substitui scripts Python para auditorias quantitativas.

## Melhor no Postman

- Smoke test manual de endpoints `_REDE` com token atual
- Exploração ad-hoc de parâmetros (dataInicial, ultimoCodigo)
- Compartilhar collection com Quality Automação (evidência 401/404)
- Testes de regressão visual por analista de negócio

## Melhor em Python

- Comparação quantitativa camadas (API vs backend vs dedupe)
- Auditoria multi-período automatizada
- Cobertura de 11 filiais em lote
- Geração de relatórios MD/JSON

## Collections oficiais recomendadas

1. `postman_webposto_network_collection.json` — rede financeiro/vendas/estoque/combustível
2. `LOGOS Backend Local` — `/v1/financial/*`, `/api/v1/*` (criar separado)

## Ambientes

| Ambiente | baseUrl WebPosto | baseUrl LOGOS |
|---|---|---|
| local | (config .env) | http://127.0.0.1:8040 |
| staging | TBD | TBD |

## Resumo probe (39 endpoints)

- USAR_AGORA: 15
- USAR_COM_CUIDADO: 5
- NAO_USAR: 14

### Top USAR_AGORA

- `TituloPagarRede` — 66 registros, filiais [5555, 11495, 2758905, 2796802, 2952501]
- `ContaRede` — 17 registros, filiais [5555, 11495, 17837, 20936, 27173]
- `MovimentoConta` — 200 registros, filiais [5256, 5333, 5554, 5557, 5559]
- `DespesasFinanceiroRede` — 427 registros, filiais [5256, 5333, 5555, 5556, 5557]
- `VendaRede` — 200 registros, filiais [5555, 11495, 355229847, 355229854, 355229941]
- `VendaItem` — 200 registros, filiais [5555, 11495, 746134869, 746134876, 746134989]
- `VendaFormaPagamento` — 200 registros, filiais [5555, 11495, 355229847, 355229854, 355229941]
- `AbastecimentoRede` — 200 registros, filiais [5555, 11495, 374577757, 374577764, 374577873]
- `CaixaRede` — 21 registros, filiais [5555, 11495, 4335818, 4335835, 4335874]
- `CaixaApresentadoRede` — 21 registros, filiais [5555, 11495, 4335818, 4335835, 4335874]
