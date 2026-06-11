# CASH OPERATIONS UI REPORT — F03

**Rota UI:** `/app/financial?view=cash-operations`  
**Tab:** Cash Operations (menu Financial)

## Componentes

1. **Cards alto impacto** — Diferença Total Rede + Cash Risk Score
2. **Painel alertas** — tabela por nível (CRÍTICO/ALTO/ATENÇÃO/INFO)
3. **Listas vermelhas** — turnos, PDVs, operadores críticos
4. **Rankboards** — Top operadores piores + Top PDVs
5. **Heatmap Turno×PDV** — CSS inline (sem lib gráfica pesada)

## Performance alvo

- Snapshot-first → render < **2s**
- Export CSV operadores via botão cockpit

**Arquivo:** `frontend/pages/cashOperations.js`
