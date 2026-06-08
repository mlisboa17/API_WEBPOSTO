# SPRINT 22A — Relatório de Auditoria de Vendas na Rede

Período de análise: **7 dias** (de 31/05/2026 a 07/06/2026)

## 1. EmpresaCodigos Encontrados

Nenhum `empresaCodigo` foi encontrado nos endpoints de rede consultados.

## 2. Novas Filiais Descobertas

Nenhuma nova filial foi descoberta. Todos os códigos encontrados já eram conhecidos.

## 3. Litros Vendidos por Combustível

Não foi possível consolidar os litros vendidos por combustível. O endpoint `CONSULTAR_VENDA_ITEM_REDE` pode não ter retornado dados ou não conter a informação de litros.

## 4. Melhor Endpoint para Dashboard Executivo

### BAIXO VALOR
- **CONSULTAR_VENDA_ITEM_REDE (não retornou dados de litros)**

## 5. Conclusão

❌ **NÃO É POSSÍVEL** construir os dashboards de combustível com os dados atualmente retornados pelos endpoints de rede.

A informação de **litros** ou um identificador claro de combustível não está presente ou não foi encontrada nos endpoints de maior prioridade (`CONSULTAR_VENDA_ITEM_REDE`).
