# Data Quality Rules - LOGOS SPACE

## Objetivo
Definir as regras de confianca para os dados consumidos pelo BI no endpoint `/api/v1/data-quality`.

## Campos monitorados
- `empresaCodigo`
- `codWeb`
- `produtoCodigo`
- `contaCodigo`
- `centroCusto`
- `formaPagamentoCodigo`
- `dataMovimento`
- `valor`
- `codigo`

## Regras por campo

### empresaCodigo / codWeb
Invalido quando:
- `empresaCodigo` nao existe na base oficial de filiais (`/INTEGRACAO/EMPRESAS` + fallback local de rede).

### produtoCodigo
Invalido quando:
- `produtoCodigo` vazio em item de venda.
- `produtoCodigo` nao encontrado no catalogo de produtos da empresa (`/INTEGRACAO/PRODUTO`).

### contaCodigo
Invalido quando:
- despesa sem `contaCodigo`, sem `planoContaCodigo` e sem descricao de conta (`planoConta`).

### formaPagamentoCodigo
Invalido quando:
- forma de pagamento sem codigo e sem descricao util.

### dataMovimento
Invalido quando:
- data nula ou em formato invalido.
- data fora do periodo solicitado (`dataInicial`..`dataFinal`).

### valor
Invalido quando:
- valor nulo.
- valor nao interpretavel pelo normalizador monetario.
- valor negativo indevido.

### codigo (chave de negocio)
Invalido quando:
- registro duplicado para a mesma chave de negocio no mesmo dominio.

### centroCusto
Invalido quando:
- ausente em cenarios em que o processo de negocio exige preenchimento (regra dependente do dominio).

## Regras de duplicidade (chave de negocio)
- Despesa: `empresaCodigo + data + valor + planoConta + contaCodigo/planoContaCodigo`
- Venda: `empresaCodigo + vendaCodigo + data + totalVenda`
- Conta a pagar: `empresaCodigo + fornecedor + vencimento + valor`

## Score de qualidade
Formula:
- `score = validos / totalRegistros * 100`
- Se `totalRegistros = 0`, score = `100`

Status:
- `score >= 95`: `ok`
- `score >= 90`: `warning`
- `score < 90`: `danger`

## Exemplo de filiais conhecidas (base oficial)
- `5256 = POSTO BR SHOPPING`
- `5333 = POSTO JANGA`
- `5556 = POSTO CIDADE PATRIMONIO`
- `5557 = POSTO ENSEADA DO NORTE`
- `5560 = POSTO SERTA`
- `5559 = POSTO RJ`
- `46433 = POSTO DOZE`
- `74014 = POSTO DOZE FILIAL II`

## Lineage do endpoint
- Empresas: `/INTEGRACAO/EMPRESAS`
- Despesas: `/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE`
- Contas a pagar: `/INTEGRACAO/TITULO_PAGAR`
- Vendas e itens: `/INTEGRACAO/VENDA`, `/INTEGRACAO/VENDA_ITEM`, `/INTEGRACAO/VENDA_FORMA_PAGAMENTO`

## Otimizações de Desempenho (Sprint 16 & 17)

### 1. Filtro Selecionado Segmentado por Empresa de Origem
Para evitar percorrer sequencialmente todas as 13 filiais na API quando o usuário estiver filtrando apenas uma empresa específica na interface, implementamos um atalho direto (`selective single-company check`). Se o parâmetro opcional `empresaCodigo` estiver presente no corpo de filtros, o backend foca exclusivamente na filial mapeada correspondente, reduzindo em até **13x** a quantidade de requisições HTTP redundantes para a API legada do WebPosto.

### 2. Down-sampling de Transações para Combustíveis Ativos
Para reduzir o esforço de processamento de inventários e evitar transferências de payloads inflados, aplicamos um filtro preventivo de produtos para calcular e qualificar apenas dados de **combustíveis ativos**. Códigos inativos ou produtos sem movimentação relevante são ignorados no fluxo de loop analítico pesado.

### 3. Caching Centralizado e Curto de 60 Segundos
Estruturamos um mecanismo robusto de cache em memória (`analytics_cache.py`) associado aos endpoints analíticos do gateway: `/api/v1/dre`, `/api/v1/kpis` e `/api/v1/data-quality`.
- **TTL de Validade:** 60 segundos por chave.
- **Formato da Chave:** `endpoint + dataInicial + dataFinal + empresaCodigo + filial`.
- **Efeito:** Chamadas subsequentes de diretores em carregamento de páginas rápidas ou duplos cliques retornam em **0.00ms** diretamente da memória local, eliminando completamente latência residual e sobrecarga no ecossistema do WebPosto.
