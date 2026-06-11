# OPERATOR PERFORMANCE ENGINE — F03.4 · Agente 1

## Fórmula

```text
OperatorPerformanceScore (0–100)
= 40% Diferenças de Caixa
+ 25% Recorrência
+ 15% Cash Risk Score
+ 10% Sobras Compensadas
+ 10% Evolução Temporal
```

## Pesos aplicados

| Componente | Peso |
|------------|------|
| Diferença caixa | 0.4 |
| Recorrência | 0.25 |
| Cash Risk | 0.15 |
| Sobras compensadas | 0.1 |
| Evolução temporal | 0.1 |

## Bandas

| Faixa | Classificação |
|-------|---------------|
| 90–100 | Excelente |
| 75–89 | Bom |
| 60–74 | Atenção |
| 0–59 | Crítico |

## Resultado rede (90d)

| Métrica | Valor |
|---------|-------|
| Score médio | **40.48** |
| Operadores classificados | **7** |
| Excelentes | **0** |
| Críticos | **6** |
| Build ms | **71238.1** |

## Casos críticos monitorados

| Alvo | Score | Banda |
|------|-------|-------|
| Operador 276288 | 60.92 | Atencao |
| Operador 294273 | 17.83 | Critico |
| PDV 54193 | 26.72 | Critico |
| PDV 15880 | 44.3 | Critico |
