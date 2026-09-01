# Homologação departamental com dados reais — 24/07/2026

## Escopo

Coleta somente leitura no WebPosto para 23/07/2026, cobrindo as empresas 11495,
5555 e 74014. Os lotes foram persistidos apenas na área privada local. Nenhum
lançamento, baixa ou alteração foi enviado ao WebPosto.

## Resultado da coleta

| Empresa | Tempo | Paginação | Vendas classificadas | Vendas em quarentena | Publicável |
|---|---:|---|---:|---:|---|
| 11495 — Posto VIP | 27,22 s | Completa | 1.211 | 1 | Não |
| 5555 — AP Casa Caiada | 8,76 s | Completa | 249 | 0 | Não |
| 74014 — Posto Doze Filial II | 9,36 s | Completa | 924 | 0 | Não |

Produto, item vendido e estoque concluíram a paginação nas três empresas. As
chamadas de despesas e caixa responderam com sucesso.

## Bloqueios reproduzidos

Os três lotes foram materializados, mas permanecem corretamente bloqueados para
publicação por:

- `QUARANTINE_ABOVE_TOLERANCE:expenses`;
- `QUARANTINE_ABOVE_TOLERANCE:stock`;
- `QUARANTINE_ABOVE_TOLERANCE:cash`.

Nenhuma despesa ou movimento de caixa recebeu departamento sem evidência. A alta
quarentena de estoque continua relacionada principalmente aos grupos mantidos fora
dos KPIs gerenciais.

## Governança

- Saúde do período: `DEGRADED`.
- Materialização disponível nas três empresas.
- Empresas publicáveis: 0 de 3.
- Alertas gerados: 9 avisos de cobertura.
- Alertas críticos: 0.
- O sistema não publicou lucro com cobertura incompleta.

## Pendências

1. Classificar despesas e caixa com evidência de centro de custo/departamento.
2. Separar estoque gerencial dos itens em quarentena aprovada.
3. Corrigir a linha isolada 84 do `.env`; o carregador identifica um UUID sem nome
   de variável. O valor não foi registrado neste relatório.
4. Repetir a homologação após as correções e exigir publicação segura nas três
   empresas.
