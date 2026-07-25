# Sprint 4 — Comparativos, metas e oportunidades

**Data:** 2026-07-24  
**Status:** Comparativo diário entregue; metas e oportunidades pendentes

## Entregas

- Comparação apenas entre o mesmo departamento e o mesmo período.
- Exclusão explícita de empresa sem lote ou com cobertura não equivalente.
- Ranking por margem bruta em reais.
- Diferença em reais para a melhor empresa do mesmo departamento.
- Linhagem preservada para cada empresa comparada.
- API:
  `GET /api/v1/departmental-kpis/comparisons?data=AAAA-MM-DD`.

## Validação real — 2026-07-23

### Combustíveis

| Posição | Empresa | Receita | Margem bruta | Margem % |
|---:|---|---:|---:|---:|
| 1 | Posto Doze | R$ 48.871,87 | R$ 7.224,64 | 14,78% |
| 2 | Posto VIP | R$ 30.946,09 | R$ 4.041,34 | 13,06% |
| 3 | Casa Caiada | R$ 17.447,17 | R$ 2.280,96 | 13,07% |

### Conveniência

| Posição | Empresa | Receita | Margem bruta | Margem % |
|---:|---|---:|---:|---:|
| 1 | Posto VIP | R$ 4.539,49 | R$ 1.154,45 | 25,43% |
| 2 | Casa Caiada | R$ 18,00 | R$ 6,00 | 33,33% |
| 3 | Posto Doze | R$ 0,00 | R$ 0,00 | — |

### Lubrificantes

| Posição | Empresa | Receita | Margem bruta | Margem % |
|---:|---|---:|---:|---:|
| 1 | Casa Caiada | R$ 149,00 | R$ 85,83 | 57,60% |
| 2 | Posto Doze | R$ 211,47 | R$ 57,77 | 27,32% |
| 3 | Posto VIP | R$ 70,00 | R$ 30,05 | 42,93% |

## Limitações

- O ranking usa margem bruta em reais, não percentual isolado.
- Um único dia não sustenta tendência, meta ou recomendação financeira.
- A margem percentual de uma operação com receita muito baixa não deve ser usada
  automaticamente como benchmark para outra empresa.
- Metas e oportunidades permanecerão vazias até existir histórico comparável e
  regra de meta aprovada.
