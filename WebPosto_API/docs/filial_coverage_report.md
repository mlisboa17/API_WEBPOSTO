# Relatório de Cobertura e Integração das Filiais (Rede Lisboa)

**Data do Levantamento**: 2026-06-07  
**Responsável**: Agente de Integração (LOGOS SPACE)  
**Status do Token Ativo**: Parcial (Multilink com limitações de visibilidade direta)

---

## 1. Métrica de Cobertura Consolidada

O ecossistema LOGOS SPACE foi avaliado de modo a computar o nível real de integração e visibilidade de dados para cada filial operacional.

### Cobertura de Filiais

* **Filiais oficiais cadastradas**: 12
* **Filiais com dados reais identificados**: 9
* **Cobertura Geral**: 9 / 12 (75.0%)

---

## 2. Resultado Executivo de Visibilidade

Hoje o sistema possui:
* **12 filiais reconhecidas** (via base de fallback local e unificação de dados)
* **9 filiais com dados reais** (que aparecem com faturamento, despesas de rede ou estoque)
* **10 filiais dependentes de novo token** (para visibilidade total em endpoints não-rede, como contabilidade individual, vendas locais exclusivas e contas a pagar direcionadas)

---

## 3. Identificação Consolidada das 12 Filiais

Abaixo estão listadas todas as 12 filiais oficiais da Rede Lisboa com seus respectivos chassi-identificadores:

| Nome Fantasia | empresaCodigo | CNPJ | Razão Social |
|---|---|---|---|
| **POSTO BR SHOPPING** | 5256 | 07.018.760/0001-75 | DISTRIBUIDORA RS DERIVADOS DE PETROLEO LTDA |
| **POSTO JANGA** | 5333 | 05.428.059/0002-80 | POSTO CIDADE PATRIMONIO LTDA |
| **POSTO CIDADE PATRIMONIO** | 5556 | 05.428.059/0001-07 | POSTO CIDADE PATRIMONIO LTDA |
| **AP CASA CAIADA** | 5555 | 04.284.939/0001-86 | AUTO POSTO CASA CAIADA LTDA |
| **POSTO ENSEADA DO NORTE** | 5557 | 00.338.804/0001-03 | POSTO ENSEADA DO NORTE LTDA |
| **POSTO SERTA** | 5560 | 04.274.378/0001-34 | AUTO POSTO IGARASSU LTDA |
| **POSTO REAL** | 7 | 24.156.978/0001-05 | REAL RECIFE LTDA |
| **POSTO RJ** | 5559 | 08.726.064/0001-86 | RJ COMBUSTIVEIS E LUBRIFICANTES |
| **AUTO POSTO GLOBO** | 9 | 41.043.647/0001-88 | AUTO POSTO GLOBO LTDA |
| **POSTO VIP** | 11495 | 03.008.754/0001-86 | RIO DOCE COMERCIO E SERVICOS LTDA |
| **POSTO DOZE** | 46433 | 52.308.604/0001-01 | POSTO DOZE COMERCIO DE COMBUSTIVEIS E DERIVADOS |
| **POSTO DOZE FILIAL II** | 74014 | 52.308.604/0002-84 | POSTO DOZE COMERCIO DE COMBUSTIVEIS E DERIVADOS |

---

## 4. Tabela Geral de Diagnóstico por Filial

Esta tabela cruza a visibilidade direta de cada empresa na API e a existência de movimentações nos endpoints de processamento:

| Filial | Código | Dados Encontrados? | Token Cobre? | Estado de Bloqueio / Causa |
|---|---|---|---|---|
| **POSTO VIP** | 11495 | **Sim** | **Sim** | Cobertura Total via API direta e token nativo. |
| **AP CASA CAIADA** | 5555 | **Sim** | **Sim** | Cobertura Total via API direta e token nativo. |
| **POSTO JANGA** | 5333 | **Sim** (Parcial) | Não | **Token Insuficiente** (Apenas em endpoint de rede `DESPESAS_REDE`). |
| **POSTO CIDADE PATRIMONIO** | 5556 | **Sim** (Parcial) | Não | **Token Insuficiente** (Apenas em endpoint de rede `DESPESAS_REDE`). |
| **POSTO ENSEADA DO NORTE** | 5557 | **Sim** (Parcial) | Não | **Token Insuficiente** (Apenas em endpoint de rede `DESPESAS_REDE`). |
| **POSTO RJ** | 5559 | **Sim** (Parcial) | Não | **Token Insuficiente** (Apenas em endpoint de rede `DESPESAS_REDE`). |
| **POSTO SERTA** | 5560 | **Sim** (Parcial) | Não | **Token Insuficiente** (Apenas em endpoint de rede `DESPESAS_REDE`). |
| **POSTO DOZE** | 46433 | **Sim** (Parcial) | Não | **Token Insuficiente** (Apenas em endpoint de rede `DESPESAS_REDE`). |
| **POSTO DOZE FILIAL II** | 74014 | **Sim** (Parcial) | Não | **Token Insuficiente** (Apenas em endpoint de rede `DESPESAS_REDE`). |
| **POSTO BR SHOPPING** | 5256 | Não | Não | **Empresa não vinculada** no token do WebPosto / Ausência real de movimentação. |
| **POSTO REAL** | 7 | Não | Não | **Empresa não vinculada** no token do WebPosto / Ausência real de movimentação. |
| **AUTO POSTO GLOBO** | 9 | Não | Não | **Empresa não vinculada** no token do WebPosto / Ausência real de movimentação. |

---

## 5. Validação Técnica por Endpoint

Abaixo é descrito o escopo de atuação de cada endpoint do WebPosto mapeado no gateway com relação às filiais:

### A. EMPRESAS (`/INTEGRACAO/EMPRESAS`)
* **Status**: Parcial.
* **Cobertura**: Retorna apenas **2 filiais** (`5555` e `11495`).
* **Motivo**: O token ativo `<WEBPOSTO_API_TOKEN>` está vinculado apenas ao Posto VIP de forma nominal no cadastro da Quality Automação.

### B. VENDA (`/INTEGRACAO/VENDA`, `/INTEGRACAO/VENDA_ITEM`, `/INTEGRACAO/VENDA_FORMA_PAGAMENTO`)
* **Status**: Parcial.
* **Cobertura**: Retorna dados reais de vendas e itens apenas para as filiais **AP CASA CAIADA** (`5555`) e **POSTO VIP** (`11495`).
* **Motivo**: Restrição do token do gateway que não unifica receitas em ambiente local de rede sem escopos autorizados.

### C. DESPESAS (`/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE`)
* **Status**: **Alta Cobertura** (9 filiais).
* **Cobertura**: Retorna dados reais para `5333`, `5555`, `5556`, `5557`, `5559`, `5560`, `11495`, `46433` e `74014`.
* **Explicação técnica**: O endpoint de despesas de rede (`DESPESAS_REDE`) provém acesso federado ao fluxo de despesas integrado de todo o grupo Lisboa sob o CNPJ mestre do contrato, mesmo que as filiais operacionais individuais não estejam autorizadas na listagem de `/EMPRESAS` do token atual.

### D. CONTAS_PAGAR (`/INTEGRACAO/TITULO_PAGAR`)
* **Status**: Restrito.
* **Cobertura**: Retorna dados apenas para a filial **POSTO VIP** (`11495`).
* **Explicação técnica**: Algumas filiais não possuem títulos lançados ou estão bloqueadas por restrições operacionais específicas do token para fins de contas a pagar individuais.

### E. ESTOQUE e PRODUTOS (`/INTEGRACAO/PRODUTO_ESTOQUE`, `/INTEGRACAO/PRODUTO_EMPRESA`, `/INTEGRACAO/PRODUTO`)
* **Status**: Parcial.
* **Cobertura**: Retorna dados de estoque físico consolidados apenas para as filiais **AP CASA CAIADA** (`5555`) e **POSTO VIP** (`11495`).

---

## 6. Próxima Recomendação para Cobertura 100%

Para unificar de forma transparente e livre de falhas a inteligência de dados com cobertura de 100% da rede de postos sob o LOGOS SPACE, recomendamos a adoção das seguintes ações coordenadas:

1. **Geração de Novo Token Corporativo de Rede (Chave ERP/Multi-Posto)**:
   * Solicitar à equipe do WebPosto/Quality Automação a emissão de uma chave de integração vinculada à **Holding (Rede Lisboa)** contendo o escopo global explícito das 12 filiais ativas no contrato.
   * Isso permitirá que o endpoint `/INTEGRACAO/EMPRESAS` retorne todos os 12 nós dinamicamente, permitindo a sincronização automática de cadastros sem a dependência do mapeamento estático atual.
   
2. **Habilitação das Empresas Ocultas**:
   * Confirmar se as empresas **5256** (POSTO BR SHOPPING), **7** (POSTO REAL) e **9** (AUTO POSTO GLOBO) encontram-se devidamente parametrizadas e com o módulo de integração de terceiros ativo no painel administrativo retaguarda do WebPosto de cada unidade.

3. **Validação de Sincronizadores e Serviços Locais**:
   * Certificar-se de que os concentradores locais destas 12 filiais estejam enviando os dados de vendas e estoque em tempo real para a nuvem da Quality, diminuindo latências de importação de dados históricos.
