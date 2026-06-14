# IA-5 — Opportunity Center Report (UX-02)

## Centralização F07.4–F07.8 (sem expor motores)

| Fonte interna | Campo exibido | View destino |
|---------------|---------------|--------------|
| `commercialAssignmentEngine` | Ação comercial | `commercialExecution` |
| `commercialLearning` recomendações | Recomendação | `commercialLearning` |
| `benchmark` gaps | Benchmark não atingido | `benchmark` |

## Colunas visíveis

| Coluna | Descrição |
|--------|-----------|
| Oportunidade | Título da ação/recomendação |
| Impacto | ROI / delta financeiro formatado |
| Filial | Nome via registry Onda 1 |
| Prioridade | ALTO / MÉDIO / etc. |
| Responsável | Owner da ação |

## Regras

- Motores (`commercialAssignmentEngine`, etc.) **não** aparecem na UI.
- Máximo 8 linhas na home.
- Clique na linha → navegação para módulo especializado.

## Parecer IA-5

Opportunity Center implementado conforme F07.4–F07.8 agregados client-side.
