# F03.4-B — PRESTAÇÃO DE CONTAS INTELLIGENCE

## Respostas executivas (Agente 10)

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Prestação possui mais informação? | **True** |
| 2 | % diferença individual rastreável | **100.0%** |
| 3 | Maiores devedores | **[{'funcionarioCodigo': 276288, 'saldo': -1850.0}]** |
| 4 | Maiores credores | **[{'funcionarioCodigo': 213391, 'saldo': 1200.0}]** |
| 5 | Total vales | **R$ 407.918,05** |
| 6 | Total faltas | **R$ 11.783,87** |
| 7 | Total sobras | **R$ 3.299,48** |
| 8 | Despesas de caixa | **R$ 200,00** |
| 9 | Recuperável | **R$ 14.140,65** |
| 10 | F04 consome prestação? | **True** |

## Critério de decisão — fonte primária

```text
PRESTACAO_DE_CONTAS = FONTE PRIMÁRIA
```

Módulos futuros (caixa, operadores, vales, accountability, perdas, recuperação):

**{'caixa': 'PRESTACAO_DE_CONTAS', 'operadores': 'PRESTACAO_DE_CONTAS', 'vales': 'PRESTACAO_DE_CONTAS', 'accountability': 'PRESTACAO_DE_CONTAS', 'perdas': 'PRESTACAO_DE_CONTAS', 'recuperacao': 'PRESTACAO_DE_CONTAS'}**

## SLA

| Meta | Resultado |
|------|-----------|
| Snapshot HIT | **0.0 ms** |
| Paridade | **True** |

## Entregáveis

- `src/services/prestacao_contas_intelligence_service.py`
- `src/services/prestacao_contas_snapshot_service.py`
- `src/interfaces/http/routes/prestacao_contas.py`
- 10 relatórios MD + DW model

[PARECER FINAL: APROVADO PARA F04]
