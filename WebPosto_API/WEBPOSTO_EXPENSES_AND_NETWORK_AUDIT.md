# WEBPOSTO EXPENSES AND NETWORK AUDIT
## Sprint Emergencial — LOGOS SPACE Combustíveis

| Campo | Valor |
|---|---|
| **Data** | 2026-06-08 |
| **Período auditado** | 2026-06-03 .. 2026-06-08 |
| **Scripts** | `scripts/audit_expenses_webposto.py`, `scripts/webposto_network_probe.py` |
| **Artefatos** | `audit_expenses_webposto_result.json`, `webposto_network_probe_result.json`, `postman_webposto_network_collection.json` |

---

## Resumo da Causa Raiz

A API **`/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE` ignora o parâmetro `empresaCodigo`** e sempre retorna despesas de **toda a rede** (~288 registros, R$ 74.743,55 no período testado).

O WebPosto original exibe esse volume **rede**. O LOGOS SPACE, com filial **11495** selecionada, filtra corretamente no backend e exibe **45 registros (R$ 13.810,23)** — exatamente os lançamentos da filial.

**Não é perda de dados por paginação** (`ultimoCodigo` ausente neste endpoint no período).  
**Não é bug de frontend/tabela** — tabela = backend = export CSV/PDF.  
**É divergência de escopo:** rede WebPosto vs filial LOGOS.

---

## Tabela Comparativa (empresa 11495)

| Fonte | Registros | Valor Total | Empresas no payload | Observação |
|---|---:|---:|---|---|
| WebPosto UI (referência) | ~288 rede | ~R$ 74.743 | 10 filiais | Sem filtro filial ou visão rede |
| API bruta (com `empresaCodigo=11495`) | 288 | R$ 74.731,55 | 10 filiais | **`empresaCodigo` ignorado pela API** |
| API bruta — só filial 11495 | 45 | R$ 13.810,23 | 11495 | Contagem manual pós-fetch |
| Backend LOGOS | 45 | R$ 13.810,23 | 11495 | Filtro client-side `_expense_matches` |
| Frontend tabela | 45 | R$ 13.810,23 | 11495 | = backend |
| Export CSV/PDF | 45 | R$ 13.810,23 | 11495 | = `sortedRows` da tabela |

## Tabela Comparativa (Todas / sem filtro filial)

| Fonte | Registros | Valor Total | Observação |
|---|---:|---:|---|
| API bruta rede | 288 | R$ 74.743,55 | 1 chamada |
| Backend LOGOS | 282 | R$ 74.281,55 | Loop por filial + dedupe |
| Perda dedupe | 6 | ~R$ 462 | `_dedupe_rows` agressivo |

---

## Respostas Obrigatórias

### 1. Por que as despesas não estavam completas?

Porque o usuário compara **despesas da rede inteira no WebPosto** (~288 lançamentos, 10 filiais) com **despesas filtradas por filial no LOGOS** (ex.: 45 para POSTO VIP 11495). O endpoint de despesas **não respeita `empresaCodigo`** — o LOGOS compensa filtrando no backend, mas a UI WebPosto mostra o universo maior.

### 2. O erro está no endpoint, backend, snapshot, frontend ou filtro?

| Camada | Veredito |
|---|---|
| **Endpoint WebPosto** | **CAUSA PRINCIPAL** — ignora `empresaCodigo` |
| **Backend LOGOS** | Comportamento **correto** para filial selecionada; ineficiente (N chamadas redundantes) |
| **Filtro frontend** | **OK** — repassa filial; tabela reflete backend |
| **Snapshot** | **N/A** — expenses usa live API |
| **Deduplicação backend** | **RISCO menor** — remove 6–29 registros em visão rede |

### 3. Quantas despesas existem na API bruta?

**288 registros** (rede, período 2026-06-03..2026-06-08), valor **R$ 74.743,55**.

### 4. Quantas chegam no backend?

| Filtro | Registros |
|---|---:|
| Filial 11495 | **45** |
| Todas filiais | **282** (após dedupe) |

### 5. Quantas aparecem na tabela?

Igual ao backend: **45** (filial 11495) ou **282** (todas).

### 6. Quais despesas estavam faltando?

**242 lançamentos de outras filiais** quando filial 11495 está selecionada:

| Filial | Registros | Exemplo valor parcial |
|---|---:|---|
| 74014 | 35 | — |
| 5557 | 52 | — |
| 5256 | 15 | — |
| 5559 | 29 | — |
| 46433 | 29 | — |
| 5555 | 25 | — |
| 5333 | 18 | — |
| 5556 | 30 | — |
| 5560 | 10 | — |
| **11495** | **45** | **R$ 13.810,23** |

POSTO REAL **5558** (inativa 20/05/2026): **0 registros**. AUTO POSTO GLOBO: pendente identificação.

### 7. Correção recomendada

**Imediato (sem refatorar arquitetura):**

1. **UX:** Mensagem na view Despesas: *"Endpoint WebPosto retorna dados da rede; exibindo N lançamentos da(s) filial(is) selecionada(s) de M totais no período."*
2. **Backend:** Uma única chamada `CONSULTAR_DESPESAS_FINANCEIRO_REDE` + filtro client-side por `empresaCodigos` (elimina N×288 chamadas redundantes).
3. **Documentar** contrato: KPIs e tabela usam **mesmo subconjunto filtrado** (45 = R$ 13.810,23 ✅).

**Quality Automação:**

4. Solicitar que `CONSULTAR_DESPESAS_FINANCEIRO_REDE` **honre `empresaCodigo`** ou documentar oficialmente que é endpoint de rede.

**Opcional:**

5. Revisar `_dedupe_rows` — 29 colisões em visão rede (chaves muito amplas).
6. Adicionar paginação `ultimoCodigo` em `_fetch_despesas` (preventivo — TITULO_PAGAR já pagina).

### 8. Quais endpoints de rede retornam dados úteis?

**USAR_AGORA (14 endpoints)** — amostra:

| Endpoint | Registros | Filiais alvo com dados |
|---|---:|---|
| `CONSULTAR_DESPESAS_FINANCEIRO_REDE` | 288 | 10/11 filiais |
| `CONSULTAR_LMC_REDE` | variável | 5555, 11495 |
| `VENDA` | variável | multi-filial |
| `VENDA_ITEM` / `_REDE` | variável | parcial (401 _REDE) |
| `PRODUTO_ESTOQUE` | variável | multi-filial |
| `EMPRESAS` | 11 | cadastro |
| `CAIXA` / `CAIXA_APRESENTADO` | variável | multi-filial |
| `ABASTECIMENTO` | variável | multi-filial |
| `MOVIMENTO_CONTA` | 1000+ | 11495 (paginar) |

Detalhe completo: `webposto_network_probe_result.json`

### 9. Quais endpoints podem melhorar cobertura com token atual?

| Endpoint | Potencial |
|---|---|
| `CONSULTAR_DESPESAS_FINANCEIRO_REDE` | **10/11 filiais** — melhor cobertura despesas rede |
| `CONSULTAR_LMC_REDE` | Combustível físico (5555, 11495 confirmados) |
| `VENDA` + `VENDA_ITEM` | Vendas por filial (sem `_REDE` 401) |
| `MOVIMENTO_CONTA` | Movimentação financeira (paginar) |
| `TITULO_PAGAR` | Contas a pagar (paginar `ultimoCodigo`) |
| `PRODUTO_ESTOQUE` | Estoque multi-filial |

**401 / sem token:** `VENDA_ITEM_REDE`, `PRODUTO_REDE`, `PRODUTO_EMPRESA_REDE`, `PRODUTO_COMBUSTIVEL`

### 10. Quais endpoints devem ir para Postman oficial?

Collection gerada: **`postman_webposto_network_collection.json`**

Incluir prioritariamente:

- `CONSULTAR_DESPESAS_FINANCEIRO_REDE`
- `TITULO_PAGAR` / `TITULO_RECEBER`
- `CONTA` / `MOVIMENTO_CONTA`
- `VENDA` / `VENDA_ITEM`
- `CONSULTAR_LMC_REDE`
- `PRODUTO_ESTOQUE` / `PRODUTO`
- `EMPRESAS`
- `CAIXA`

### 11. Quais endpoints solicitar à Quality Automação?

| Prioridade | Solicitação |
|---|---|
| P0 | Habilitar `empresaCodigo` em `CONSULTAR_DESPESAS_FINANCEIRO_REDE` |
| P0 | Habilitar `VENDA_ITEM_REDE`, `VENDA_FORMA_PAGAMENTO_REDE` (401 hoje) |
| P0 | Expandir token LMC para 11 filiais |
| P1 | Habilitar `PRODUTO_REDE`, `PRODUTO_EMPRESA_REDE` |
| P1 | Documentar paginação `ultimoCodigo` por endpoint |
| P2 | Endpoints inferidos 404: `PLANO_CONTA_GERENCIAL`, `LANCAMENTO_CONTABIL`, `DRE` |

### 12. Próxima ação recomendada

1. **Validar com usuário:** comparar WebPosto UI **com mesma filial selecionada** (11495) — deve convergir para 45 / R$ 13.810,23.
2. **Implementar banner UX** de escopo rede vs filial (1h).
3. **Otimizar `_fetch_despesas`:** 1 fetch + filtro client-side (2h).
4. **Abrir ticket Quality** com evidência JSON desta auditoria.
5. **Importar** `postman_webposto_network_collection.json` no Postman oficial LOGOS.

---

## Classificação de Endpoints (resumo probe)

| Classificação | Qtd |
|---|---:|
| USAR_AGORA | 14 |
| USAR_COM_CUIDADO | 6 |
| APENAS_DIAGNOSTICO | 5 |
| NAO_USAR | 14 |

---

## Artefatos Gerados

| Arquivo | Descrição |
|---|---|
| `scripts/audit_expenses_webposto.py` | Auditoria camadas despesas |
| `audit_expenses_webposto_result.json` | Resultado JSON |
| `audit_expenses_webposto_report.md` | Relatório parcial despesas |
| `scripts/webposto_network_probe.py` | Probe rede automatizado |
| `webposto_network_probe_result.json` | Resultado probe |
| `postman_webposto_network_collection.json` | Collection Postman |

---

*Sprint Emergencial — causa raiz provada com evidência quantitativa. Correção de código aguarda validação do usuário sobre escopo filial vs rede.*
