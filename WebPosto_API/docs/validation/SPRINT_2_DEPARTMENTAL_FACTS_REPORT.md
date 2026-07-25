# Sprint 2 — Relatório da camada de fatos departamentalizados

**Data:** 2026-07-24  
**Status:** Base canônica implementada; integração com o ETL pendente

## Implementado

- Contrato único para fatos de venda, custo, despesa, estoque e caixa.
- Dimensões presentes no fato: empresa, departamento, grupo, produto, data e turno.
- Classificação exclusivamente por `grupoCodigo` confirmado.
- Quarentena explícita para grupo ausente, não classificado ou ambíguo.
- Rejeição de registros pertencentes a empresas não licenciadas.
- Deduplicação por tipo, empresa e identidade do registro de origem.
- Linhagem com token lógico, endpoint, período e horário da coleta.
- Reconciliação entre total aceito da origem e fatos classificados + quarentena.
- Materialização separada da publicação: lotes podem ser preservados para revisão,
  mas KPIs ficam bloqueados quando a quarentena supera 2%.
- Persistência atômica na área privada `.runtime/departmental_facts`, fora da pasta
  pública de snapshots e excluída do Git.

## API de qualidade

- `POST /api/v1/departmental-facts/materialize?empresaCodigo=...&data=AAAA-MM-DD`
- `GET /api/v1/departmental-facts/quality?empresaCodigo=...&data=AAAA-MM-DD`

A API de qualidade retorna contagens, paginação, cobertura, duplicidades, conflitos,
reconciliação e motivos de bloqueio; ela não publica KPIs quando a cobertura falha.

## Regras de segurança

1. COMODATO, DIVERSOS e USO E CONSUMO nunca recebem departamento automaticamente.
2. `tipoProduto` C, P ou U não substitui evidência de `grupoCodigo`.
3. Registro de empresa externa é rejeitado e não entra no total autorizado.
4. Registro licenciado sem departamento permanece contabilizado na quarentena.
5. Diferença de reconciliação deve ser zero antes de publicação.
6. Quarentena acima de 2% bloqueia publicação executiva.

## Validação

Os testes cobrem:

- classificação dos três departamentos;
- motivos de quarentena;
- duplicidade;
- isolamento das três licenças;
- valores de venda, custo, despesa, estoque e caixa;
- linhagem completa;
- amostras capturadas de VENDA_ITEM, despesas e CAIXA para Posto VIP e Casa Caiada.

## Próximo incremento

Conectar `DepartmentalFactBuilder` ao coletor paginado para materializar lotes
completos por empresa e dia. A publicação executiva deve permanecer bloqueada quando:

- paginação não comprovar término;
- diferença de reconciliação for diferente de zero;
- a cobertura do catálogo de produtos não permitir classificar os itens.

## Diagnóstico ao vivo — Posto Doze

Em 2026-07-23, a identidade composta de estoque preservou 1.871 linhas, sem
duplicatas, conflitos ou diferença de reconciliação. A quarentena observada foi:

- 1.748 produtos em USO E CONSUMO;
- 12 produtos em DIVERSOS;
- 2 produtos em COMODATO;
- 3 produtos no grupo 166355, identificado como fluidos para freios/transmissões
  e incorporado a Lubrificantes conforme o escopo aprovado.

A alta quarentena de estoque é consequência direta da decisão de manter USO E
CONSUMO fora dos KPIs; esses registros permanecem preservados e visíveis.

## Materialização real

O lote do Posto Doze de 2026-07-23 foi persistido com sucesso na área privada:

| Domínio | Classificados | Quarentena | Diferença |
|---|---:|---:|---:|
| Vendas | 924 | 0 | 0,00 |
| Custos | 924 | 0 | 0,000 |
| Despesas | 0 | 9 | 0,00 |
| Estoque | 109 | 1.762 | 0 |
| Caixa | 0 | 1 | 0,00 |

O lote foi materializado, mas corretamente marcado como não publicável para KPIs
globais devido à quarentena de despesas, estoque e caixa. Vendas e custos possuem
cobertura departamental completa nesse recorte.
