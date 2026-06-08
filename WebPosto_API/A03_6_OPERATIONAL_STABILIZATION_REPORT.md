# A03_6_OPERATIONAL_STABILIZATION_REPORT

**Gerado:** 2026-06-08T14:44:37
**Período:** 2026-06-01 .. 2026-06-07

---

## Respostas obrigatórias (15)

### 1. Datas estão corretas?
**Sim no pipeline P0.** YYYY-MM-DD ponta a ponta. Risco P2: default `toISOString` em app.js. Ver `DATE_PIPELINE_AUDIT_A03_6.md`.

### 2. Filtros estão corretos?
**Despesas multiselect: Sim** (P0.2). KPIs/accounts ainda loop por filial em alguns fluxos.

### 3. Despesas estão corretas?
**Sim**. Fonte DESPESAS_REDE + filtro memória. Casos A–D: {"A_11495": true, "B_5555": true, "C_multi": true, "D_todos": true}

### 4. Caixa está correto?
**Parcial — dados disponíveis, não integrado ao BI principal.** Agregados em CAIXA_APRESENTADO. Ver `CAIXA_FINANCE_MODEL.md`.

### 5. Banco está correto?
**Dados OK na API; não integrado ao LOGOS.** 400 movimentos + 400 transferências. Ver `BANKING_MODEL.md`.

### 6. Contas a pagar estão corretas?
**Sim no módulo accounts-payable** (TITULO_PAGAR). Não misturar com despesas gerenciais.

### 7. Contas a receber estão corretas?
**API retorna 11 registros; LOGOS stub vazio.** Integração pendente A04.

### 8. Existem dados de rede aproveitáveis?
**Sim.** USAR_AGORA: MOVIMENTO_CONTA, CAIXA, CAIXA_APRESENTADO, TITULO_PAGAR, EMPRESAS, DESPESAS_REDE...

### 9. O Postman agrega valor?
**Sim** — smoke tests e evidência QA. Python superior para auditorias. Ver `POSTMAN_VALIDATION_REPORT.md`.

### 10. Quais endpoints integrar na A04?
MOVIMENTO_CONTA, CAIXA_APRESENTADO, TITULO_RECEBER, EMPRESAS, CENTRO_CUSTO_REDE (se 200), NOTA_ENTRADA (quando token).

### 11. Top 10 melhorias técnicas

1. Manter single-fetch despesas (P0.2) — validado
2. Implementar cache TTL despesas por período+empresa
3. Otimizar executive KPIs (9–19s medidos)
4. Snapshot warm-up job pós-refresh
5. Paginação ultimoCodigo preventiva em despesas
6. Multiselect TITULO_PAGAR (mesmo padrão despesas)
7. Banner UX escopo rede vs filial
8. Integrar MOVIMENTO_CONTA fase A04
9. Validar FINANCEIRO_EXCLUSAO filtro data antes BI
10. Reduzir chamadas TITULO_PAGAR em overview (N× filial)

### 12. Top 10 melhorias de negócio

1. Documentar diferença Despesa Gerencial vs Contas a Pagar
2. Expor totais caixa (despesaApurado) no dashboard operacional
3. Fluxo caixa projetado a partir TITULO_PAGAR
4. Conciliação bancária MOVIMENTO_CONTA
5. Cobertura rede filiais 5256/5333 via despesas rede
6. Ticket Quality: empresaCodigo em DESPESAS_REDE
7. Identificar AUTO POSTO GLOBO (filial pendente)
8. Vale funcionário via CAIXA_APRESENTADO
9. Inadimplência via TITULO_RECEBER
10. Compras detalhadas quando token NOTA_ENTRADA liberado

### 13. Sistema está pronto para A04?
**Sim, com ressalvas.** Despesas/filtros estabilizados (P0.2). DW pode iniciar com fact_despesa_gerencial + fact_titulo_pagar.

### 14. Nota de maturidade atual
**7.0/10** (operacional financeiro)

### 15. Risco operacional atual
**35/100** — principal risco: confusão Despesa Gerencial vs Título a Pagar na percepção do usuário.

---

## Despesas — evidência

| Caso | Registros | Valor | Empresas | Pass |
|---|---:|---:|---|---|
| A_11495 | 73 | 24926.71 | [11495] | True |
| B_5555 | 46 | 7292.73 | [5555] | True |
| C_multi | 119 | 32219.44 | [5555, 11495] | True |
| D_todos | 417 | 127565.20 | [5256, 5333, 5555, 5556, 5557, 5559, 5560, 11495, 46433, 74014] | True |

## Performance (ms médio)

- **executive**: 8990.9ms (max 14659.2ms)
- **dashboard**: 3391.1ms (max 3391.1ms)
- **expenses**: 3101.2ms (max 3101.2ms)
- **accounts**: 3864.0ms (max 3864.0ms)
- **sales**: 10623.0ms (max 10623.0ms)
- **stock**: 4337.6ms (max 4337.6ms)
- **fuels**: 6830.9ms (max 11500.4ms)
- **financial**: 850.8ms (max 1693.1ms)
