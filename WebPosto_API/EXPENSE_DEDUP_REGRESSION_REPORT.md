# EXPENSE DEDUP REGRESSION AUDIT — Agente 7

Validação: despesas legítimas com mesmo dia + PDV + turno mas `caixaCodigo` ou valor distintos **devem permanecer separadas**.

| Janela | Fechamentos esperados | Linhas operacionais (novo) | Paridade | Falsos positivos | Seguro? |
|--------|----------------------:|---------------------------:|---------:|-----------------:|--------:|
| 7d | 19 | 19 | 0 | 0 | Sim |
| 30d | 85 | 85 | 0 | 0 | Sim |
| 90d | 180 | 180 | 0 | 0 | Sim |

## Duplicidade verdadeira (exemplos)

### 7d
- ? (11495) · 2026-06-06 · caixa 4340637 · PDV 56764 · dup R$ 745,00 · caixa+pdv
- ? (11495) · 2026-06-04 · caixa 4338777 · PDV 54193 · dup R$ 548,65 · caixa+pdv
- ? (11495) · 2026-06-05 · caixa 4339655 · PDV 54193 · dup R$ 486,00 · caixa+pdv

### 30d
- ? (11495) · 2026-05-30 · caixa 4334613 · PDV 54193 · dup R$ 4.148,00 · caixa+pdv
- ? (5555) · 2026-05-26 · caixa 4330269 · PDV 15880 · dup R$ 1.320,80 · caixa+pdv
- ? (11495) · 2026-05-19 · caixa 4323599 · PDV 54193 · dup R$ 1.269,00 · caixa+pdv

### 90d
- ? (5555) · 2026-04-25 · caixa 4300877 · PDV 15880 · dup R$ 4.899,07 · caixa+pdv
- ? (11495) · 2026-05-02 · caixa 4307424 · PDV 54193 · dup R$ 4.407,00 · caixa+pdv
- ? (11495) · 2026-04-15 · caixa 4291181 · PDV 54193 · dup R$ 3.573,32 · caixa+pdv


## Despesas distintas válidas (exemplos)


## Parecer Agente 7

- **Falsos positivos de deduplicação:** Não (0)
- **Algoritmo seguro para produção:** Sim
- **Correção retroativa:** Recomendada — duplicidade sistêmica em múltiplas janelas; totais históricos da tela estavam superestimados.