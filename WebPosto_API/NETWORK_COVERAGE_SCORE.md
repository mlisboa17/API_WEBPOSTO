# NETWORK COVERAGE SCORE — Índice de Cobertura da Rede
## LOGOS SPACE Combustíveis | Sprint A03

| Campo | Valor |
|---|---|
| **Endpoint** | `GET /api/v1/network/coverage` |
| **Implementação** | `build_network_coverage()` em `executive_snapshot_service.py` |
| **Data** | 2026-06-08 |

---

## Indicador Oficial: Índice de Cobertura da Rede

```
indiceCoberturaRede = (operacional × 0.5) + (combustível × 0.3) + (confirmadas × 0.2)
```

| Componente | Peso | Fórmula |
|---|---|---|
| Cobertura operacional | 50% | filiaisComDados / filiaisAtivas |
| Cobertura combustível | 30% | filiaisComCombustivel / filiaisAtivas |
| Filiais confirmadas | 20% | filiaisConfirmadas / filiaisTotais |

---

## Métricas Expostas

| Campo | Descrição |
|---|---|
| `filiaisTotais` | Total de filiais no FilialMaster |
| `filiaisAtivas` | Confirmadas com status operacional ATIVA |
| `filiaisComDados` | Ativas com dados operacionais WebPosto |
| `filiaisComCombustivel` | Ativas com dados LMC (5555, 11495 + flag) |
| `filiaisSemToken` | Ativas com limitação de token |
| `filiaisSemSincronizacao` | Sem API encontrada ou pendente |
| `filiaisInativas` | Status INATIVA |
| `filiaisPendentesIdentificacao` | Sem codWeb mapeado |
| `indiceCoberturaRede` | Score 0-100 para diretoria |
| `mensagemDiretoria` | Texto padrão de comunicação |

---

## Valores Atuais (baseline rede)

| Métrica | Valor | % |
|---|---|---|
| Filiais totais | 11 | 100% |
| Filiais ativas | 9 | 82% |
| Filiais com dados | 2 | 18% |
| Filiais com combustível | 2 | 18% |
| Filiais sem token | 1+ | ~9% |
| Índice cobertura rede | ~25-30 | — |

---

## Mensagem para Diretoria

> **O software LOGOS SPACE está operacional.**
> **A limitação atual é a integração WebPosto (token e endpoints por filial).**

O índice separa claramente:
- **Maturidade do software** (snapshot, multiselect, dashboards) → operacional
- **Maturidade da integração** (token 2/11, endpoints `_REDE` 401) → limitação externa

---

## Uso no Dashboard

| View | Exibição |
|---|---|
| `executive` | Card Coverage via snapshot |
| API direta | `/api/v1/network/coverage` |
| Futuro A04 | Série histórica no DW |

---

*Sprint A03 — indicador oficial implementado.*
