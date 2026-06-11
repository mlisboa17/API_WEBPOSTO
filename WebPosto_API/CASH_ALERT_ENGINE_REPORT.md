# CASH ALERT ENGINE REPORT — F03

**Sprint:** F03 · Cash Operations Intelligence  
**Motor:** `CashOperationsService._build_alerts`  
**Evidência runtime:** janela 2026-06-01 → 2026-06-07

---

## Matriz de regras

| Nível | Condição |
|-------|----------|
| INFO | R$ 0.01 ≤ \|diff\| < R$ 20.00 |
| ATENÇÃO | \|diff\| ≥ R$ 20.00 |
| ALTO | \|diff\| ≥ R$ 50.00 |
| CRÍTICO | \|diff\| ≥ R$ 100.00 **OU** ≥3 quebras consecutivas **OU** PDV ≥5 quebras/30d |

## Filtros dimensionais

- **Operador:** `funcionarioCodigo` (CAIXA_REDE / CAIXA)
- **PDV:** `pdvCodigo`
- **Filial:** `empresaCodigo` via `build_finance_center_filters`

## Resultado janela atual

| Métrica | Valor |
|---------|-------|
| Alertas ativos | **21** |
| CRÍTICO | 21 |
| ALTO | 0 |
| ATENÇÃO | 0 |
| INFO | 0 |

## Payload de alerta

```json
{
  "nivel": "CRITICO|ALTO|ATENCAO|INFO",
  "funcionarioCodigo": 276288,
  "pdvCodigo": 54193,
  "diferenca": -120.00,
  "motivo": "diferenca >= R$ 100.00"
}
```

## Integração

1. `GET /api/v1/cash/operations/alerts` — expõe `alerts.ativos`
2. Snapshot key: `cash:alerts:{dataIni}:{dataFim}:{empresa}`
3. DW: `fact_cash_alert` (DDL F03)
