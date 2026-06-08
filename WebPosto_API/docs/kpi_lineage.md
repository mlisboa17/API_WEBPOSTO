# Data Lineage (Rastreabilidade de Indicadores)

Este documento centraliza a origem (`lineage`) dos cálculos presentes no Painel Executivo do WebPosto Integração. Mapeamos desde o Campo Bruto no Payload JSON até a métrica visual no UI.

---

## 1. Faturamento Total
**Origem de Dados (Endpoint):** `/INTEGRACAO/VENDA` (Rota frontend: `/v1/sales`)
**Agregação Frontend:** Vendas agregadas filtradas pelo frontend

**Lineage Técnico:**
- Componente: `kpiBar.js` -> `Faturamento Total`
  - Motor: `analyticsEngine.js` -> `computeIndicators()` -> `let faturamento = 0`
    - Atributo base: `venda.totalVenda` via parseFloat.
      - Chave: `empresaCodigo` presente e validada, agrupada se Rede.
    - Condição de Contorno: Vendas sem `totalVenda` geram valor 0 e não quebram o pipeline.

---

## 2. Despesas Totais
**Origem de Dados (Endpoint):** `/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE` (Rota frontend: `/v1/financial/expenses`)
**Agregação Frontend:** Despesas pagas ou pendentes mapeadas.

**Lineage Técnico:**
- Componente: `kpiBar.js` -> `Despesas Totais`
  - Motor: `analyticsEngine.js` -> `computeIndicators()` -> `let despesasTotais = 0`
    - Atributo base: `despesa.valor` via parseFloat.
      - Chave: `empresaCodigo` e `planoConta` mapeado.

---

## 3. Resultado Operacional (DRE)
**Origem de Dados (Endopint):** `VENDA` e `CONSULTAR_DESPESAS_FINANCEIRO_REDE`.
**Cálculo Derivado**

**Lineage Técnico:**
- Componente: `dreBlock.js` -> `Resultado Operacional`
  - Motor: `analyticsEngine.js` -> `computeDRE()`
    - Atributo Base (Receita): `venda.totalVenda` (soma total)
    - Atributo Base (Custo Produto): `espesa.valor` restrito aos que contém `"custo"` ou `"fornecedor"`.
    - Atributo Base (Outras Despesas): `despesa.valor` remanescentes.
    - Fórmula: `Receitas - Custos Produto - Outras Despesas`.

---

## 4. Ticket Médio
**Origem de Dados:** `/INTEGRACAO/VENDA`
**Índice Composto**

**Lineage Técnico:**
- Componente: `kpiBar.js` -> `Ticket Médio`
  - Motor: `analyticsEngine.js` -> `computeIndicators()`
    - Fórmula: `Faturamento Total / Quantidade de Vendas`
    - Atributos base: `venda.totalVenda` (acumulador V) / Count de laços `vendas(items)`.
    - Contorno protetivo: Valida divisão por 0 caso array = length 0.

---

## 5. Clientes
**Origem de Dados:** `/INTEGRACAO/VENDA`
**Índice Isolado por Set/Hash**

**Lineage Técnico:**
- Componente: `kpiBar.js` -> `Clientes`
  - Motor: `analyticsEngine.js` -> `computeIndicators()` -> `clientesSet.size`
    - Atributo Base: `venda.cliente` (Nome / String)
    - Contorno: Ignora `cliente` === `""` ou Null, mapeamento usando `Set()` para assegurar Uniq count por nome na string nativa.

---

## 6. Estoque Total
**Origem de Dados:** `/INTEGRACAO/PRODUTO_ESTOQUE` ou `/INTEGRACAO/PRODUTO_EMPRESA` (Rota: `/v1/stock`)
**Agregação Linear**

**Lineage Técnico:**
- Componente: `kpiBar.js` -> `Estoque Total`
  - Motor: `analyticsEngine.js` -> `computeStockIndicator()` -> `estoqueTotal += quantidade`
    - Atributo Base: `estoque.quantidade`.
    - Contorno: Converte Strings de Float limitados à `,` e tira os R$ caso API devolva moeda.

---

## Notas de Governança
- Faturamento consolidado soma todos os blocos brutos em período aberto.
- Filtros de UI base (Ex: Selecionar Filial POSTO VIP) invoca roteamento `?empresaCodigo=11495` antes da rede chamar os endpoints. Assim sendo, a engine de métricas garante que toda visão Rede vs Filial é garantidamente controlada via URL.
