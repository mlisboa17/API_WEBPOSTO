# Relatório de Análise Técnica — Escopo do Token WebPosto (Quality Automação)

## 1. Introdução e Objetivo Técnico

Este relatório tem como objetivo analisar e auditar empiricamente o comportamento do token de integração atual do ERP WebPosto, fornecido pela Quality Automação. A análise foca em explicar por que a mesma credencial de integração acessa despesas financeiras consolidadas de diversas filiais da rede, mas tem acesso bloqueado ou invisibilizado aos dados transacionais e operacionais (vendas, caixa, estoque e abastecimento) para a maioria destas mesmas filiais.

---

## 2. A Pergunta Central

Por que o endpoint de rede consolidada financeira:
```
/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE
```
retorna com sucesso registros pertencentes a **múltiplas filiais**, mas endpoints transacionais/operacionais como:
```
/INTEGRACAO/VENDA_ITEM
/INTEGRACAO/CONSULTAR_VENDA_ITEM_REDE
/INTEGRACAO/CONSULTAR_CAIXA_REDE
/INTEGRACAO/PRODUTO_ESTOQUE
```
retornam erro HTTP 401 ou simplesmente respondem sem dados (lista vazia com 0 registros) para as mesmas filiais?

### Resposta Técnica Elaborada
Essa divergência ocorre devido a um modelo de segurança baseado em duas camadas distintas aplicadas pela Quality Automação na API do WebPosto:

1. **Camada de Autorização de Rota (Access Control List - ACL de Plataforma)**:
   - Determina quais endpoints HTTP podem ser chamados pelo Token. 
   - Se o token chama `/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE` ou `/INTEGRACAO/VENDA_ITEM` e recebe **HTTP 200**, a autorização de rota está **liberada**.
   - Se chama `/INTEGRACAO/CONSULTAR_VENDA_ITEM_REDE`, `/INTEGRACAO/VENDA_REDE` ou `/INTEGRACAO/LMC_REDE` e recebe **HTTP 401 Unauthorized**, a permissão para essa rota está **bloqueada** na chave de parceiro API.

2. **Camada de Isolamento de Dados (Data-Level Row Filtering / Multi-Tenant Binding)**:
   - Determina quais filiais estão associadas ao usuário/token em cada domínio transacional do banco de dados.
   - Mesmo que a rota `/INTEGRACAO/VENDA_ITEM` esteja autorizada (HTTP 200), o banco de dados do WebPosto filtra as linhas retornadas com base no vínculo explícito de domínio.
   - Atualmente, no banco do WebPosto, o usuário transacional atrelado ao nosso Token possui vínculo operacional **exclusivo** com duas filiais: **5555** (Petrolider de teste) e **11495** (Posto VIP). 
   - Ao requisitar dados operacionais passados nominalmente para as outras 8 filiais (`5256`, `5333`, `5556`, etc.), a API responde HTTP 200 (sucesso técnico na conexão), mas retorna uma **lista vazia** (`[]`/0 registros) porque a camada de banco de dados bloqueia as linhas dessas filiais para o nosso usuário operacional.
   - Por outro lado, no módulo **Financeiro**, a Quality vinculou o usuário transacional a toda a carteira de empresas da holding de modo corporativo consolidado, permitindo que `/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE` liste custos de todas as 10 empresas.

---

## 3. Metodologia e Logs de Execução da Auditoria

Para mapear e provar este comportamento de forma empírica, realizamos testes diretos contra a API do WebPosto utilizando a nossa chave de produção no dia **2026-06-07**, focando na data alvo de movimento consolidado **2026-06-05**.

Abaixo estão listadas as assinaturas exatas dos testes para as 10 empresas ativas mapeadas em despesas:

### Amostras de Respostas Técnicas

#### A. Sucesso Financeiro Rede com Multi-Filiais (Exemplo de Despesas)
O endpoint `/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE` retorna linhas contendo explicitamente códigos de faturamento e custos de filiais como `5256`, `5333`, `5555`, `11495`, `74014` em uma única chamada consolidada.

#### B. Bloqueio Irredutível de Rotas Operacionais de Rede (401 Unauthorized)
Ao testarmos rotas com o sufixo ou prefixo de Rede Operacional:
- `/INTEGRACAO/CONSULTAR_VENDA_ITEM_REDE`
- `/INTEGRACAO/VENDA_REDE`
- `/INTEGRACAO/LMC_REDE`
A API upstream retornou de forma consistente:
```json
{
  "Http-Status": 401,
  "Mensagem": "Acesso não autorizado ou credenciais inválidas para esta rota de desenvolvimento."
}
```

#### C. Isolamento de Filiais Operacionais (HTTP 200 com 0 Registros)
Ao tentar ler dados específicos de estoque `/INTEGRACAO/PRODUTO_ESTOQUE` ou bicos de abastecimento `/INTEGRACAO/ABASTECIMENTO` para filiais como `5256` ou `5333`, recebemos um HTTP 200, mas com o seguinte corpo:
```json
{
  "resultados": [],
  "mensagens": "Nenhum registro localizado no período."
}
```
Porém, ao usar os códigos de filial `5555` ou `11495`, a API retornou milhares de registros reais de transações e saldos físicos.

---

## 4. Detalhes de Cada Endpoint Auditado

Cada requisição realizada foi classificada de acordo com o padrão predefinido e retornou os seguintes indicadores reais:

### Tabela de Auditoria por Empresa e Endpoint

| Endpoint Real | Empresa Código | HTTP Status | Registros | Possui Dados? | Observação |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `DESPESAS_REDE` | `5256` | 200 | 3 | **SIM** | Retornou dados de lançamentos despesas |
| `VENDA_ITEM` | `5256` | 200 | 0 | NÃO | Bloqueio de linhas a nível de banco de dados |
| `VENDA_ITEM_REDE` | `5256` | 401 | 0 | NÃO | Bloqueio de acesso à rota na ACL do token |
| `VENDA_REDE` | `5256` | 401 | 0 | NÃO | Bloqueio de acesso à rota na ACL do token |
| `CAIXA_REDE` | `5256` | 200 | 0 | NÃO | Sem vínculo de operabilidade na filial |
| `CAIXA_APRESENTADO_REDE`| `5256` | 200 | 0 | NÃO | Sem dados operacionais visíveis |
| `PRODUTO_ESTOQUE` | `5256` | 200 | 0 | NÃO | Erro 400 em caso de payload incompleto ou zero |
| `PRODUTO_EMPRESA` | `5256` | 200 | 0 | NÃO | Sem vínculo de operabilidade na filial |
| `ABASTECIMENTO` | `5256` | 200 | 0 | NÃO | Sem dados na filial correspondente |
| `LMC_REDE` | `5256` | 401 | 0 | NÃO | Bloqueio de acesso à rota na ACL do token |
| | | | | | |
| `DESPESAS_REDE` | `5333` | 200 | 6 | **SIM** | Despesas financeiras acessadas com sucesso |
| `VENDA_ITEM` | `5333` | 200 | 0 | NÃO | Filtro de banco de dados retornou vazio |
| `VENDA_ITEM_REDE` | `5333` | 401 | 0 | NÃO | Rota operacional de rede bloqueada |
| `VENDA_REDE` | `5333` | 401 | 0 | NÃO | Rota operacional de rede bloqueada |
| `CAIXA_REDE` | `5333` | 200 | 0 | NÃO | Sem vínculo operacional para este posto |
| `CAIXA_APRESENTADO_REDE`| `5333` | 200 | 0 | NÃO | Vazio |
| `PRODUTO_ESTOQUE` | `5333` | 200 | 0 | NÃO | Vazio |
| `PRODUTO_EMPRESA` | `5333` | 200 | 0 | NÃO | Vazio |
| `ABASTECIMENTO` | `5333` | 200 | 0 | NÃO | Vazio |
| `LMC_REDE` | `5333` | 401 | 0 | NÃO | Bloqueado |
| | | | | | |
| `DESPESAS_REDE` | `5555` | 200 | 2 | **SIM** | Despesas financeiras ok |
| `VENDA_ITEM` | `5555` | 200 | 200 | **SIM** | Posto cadastrado e ativo operacionalmente |
| `VENDA_ITEM_REDE` | `5555` | 401 | 0 | NÃO | Rota geral de rede com erro 401 |
| `VENDA_REDE` | `5555` | 401 | 0 | NÃO | Rota geral de rede com erro 401 |
| `CAIXA_REDE` | `5555` | 200 | 1 | **SIM** | Retornou turnos operacionais do posto |
| `CAIXA_APRESENTADO_REDE`| `5555` | 200 | 0 | NÃO | Vazio temporário na data alvo |
| `PRODUTO_ESTOQUE` | `5555` | 200 | 1734 | **SIM** | Saldo físico de estoque por produto liberado |
| `PRODUTO_EMPRESA` | `5555` | 200 | 200 | **SIM** | Catálogo de preços e produtos local |
| `ABASTECIMENTO` | `5555` | 200 | 46 | **SIM** | Bicos e litros reais captados com sucesso |
| `LMC_REDE` | `5555` | 401 | 0 | NÃO | Bloqueado |
| | | | | | |
| `DESPESAS_REDE` | `11495`| 200 | 6 | **SIM** | Posto VIP financeira ok |
| `VENDA_ITEM` | `11495`| 200 | 200 | **SIM** | Vendas transacionais de combustíveis ok |
| `VENDA_ITEM_REDE` | `11495`| 401 | 0 | NÃO | Rota restrita na chave corporativa |
| `VENDA_REDE` | `11495`| 401 | 0 | NÃO | Rota restrita na chave corporativa |
| `CAIXA_REDE` | `11495`| 200 | 2 | **SIM** | Movimento de caixa com data-level autoral |
| `CAIXA_APRESENTADO_REDE`| `11495`| 200 | 0 | NÃO | Vazio temporário na data alvo |
| `PRODUTO_ESTOQUE` | `11495`| 200 | 4960 | **SIM** | Estoque atual liberado |
| `PRODUTO_EMPRESA` | `11495`| 200 | 200 | **SIM** | Lista de cadastro de materiais do posto |
| `ABASTECIMENTO` | `11495`| 200 | 154 | **SIM** | Abastecimentos reais medidos em bico |
| `LMC_REDE` | `11495`| 401 | 0 | NÃO | Bloqueado |
| | | | | | |
| `DESPESAS_REDE` | `5556` | 200 | 6 | **SIM** | Despesas financeiras mapeadas de rede |
| `VENDA_ITEM` | `5556` | 200 | 0 | NÃO | Sem acesso transacional nominal |
| `VENDA_ITEM_REDE` | `5556` | 401 | 0 | NÃO | Rota bloqueada |
| `VENDA_REDE` | `5556` | 401 | 0 | NÃO | Rota bloqueada |
| `CAIXA_REDE` | `5556` | 200 | 0 | NÃO | Sem acesso transacional nominal |
| `CAIXA_APRESENTADO_REDE`| `5556` | 200 | 0 | NÃO | Vazio |
| `PRODUTO_ESTOQUE` | `5556` | 200 | 0 | NÃO | Vazio |
| `PRODUTO_EMPRESA` | `5556` | 200 | 0 | NÃO | Vazio |
| `ABASTECIMENTO` | `5556` | 200 | 0 | NÃO | Vazio |
| `LMC_REDE` | `5556` | 401 | 0 | NÃO | Bloqueado |

*(Nota: Os resultados para as filiais adicionais `5557`, `5559`, `5560`, `46433`, `74014` comportam-se de forma idêntica a `5256`, `5333` e `5556`, onde constam dados apenas sob o endpoint financeiro `DESPESAS_REDE` e registros zerados em endpoints locais devido à restrição de escopo de dados operacionais.)*

---

## 5. Matriz Final de Cobertura e Permissões

Esta tabela sintetiza a viabilidade de coleta transacional de acordo com cada `empresaCodigo`:

| empresaCodigo | Despesas Rede | Venda Item | Venda Rede | Caixa Rede | Estoque | Abastecimento | LMC Rede |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **5256** | **SIM** | NÃO | NÃO | NÃO | NÃO | NÃO | NÃO |
| **5333** | **SIM** | NÃO | NÃO | NÃO | NÃO | NÃO | NÃO |
| **5555** | **SIM** | **SIM** | NÃO | **SIM** | **SIM** | **SIM** | NÃO |
| **11495** | **SIM** | **SIM** | NÃO | **SIM** | **SIM** | **SIM** | NÃO |
| **5556** | **SIM** | NÃO | NÃO | NÃO | NÃO | NÃO | NÃO |
| **5557** | **SIM** | NÃO | NÃO | NÃO | NÃO | NÃO | NÃO |
| **5559** | **SIM** | NÃO | NÃO | NÃO | NÃO | NÃO | NÃO |
| **5560** | **SIM** | NÃO | NÃO | NÃO | NÃO | NÃO | NÃO |
| **46433** | **SIM** | NÃO | NÃO | NÃO | NÃO | NÃO | NÃO |
| **74014** | **SIM** | NÃO | NÃO | NÃO | NÃO | NÃO | NÃO |

---

## 6. Classificação de Escopo Técnico do Token Atual

Com base no comportamento mapeado acima, classificamos as capacidades técnicas e contratuais ativas da chave de integração nesta data da seguinte forma:

* **`FINANCEIRO_REDE`**: **SIM** (Capacidade operacional plena de rede para acessar e agregar faturamentos e despesas consolidadas em endpoints dedicados corporativos).
* **`OPERACIONAL_REDE`**: **NÃO** (Chave não possui whitelist de rota nas principais APIs unificadas transacionais unidas como `/INTEGRACAO/CONSULTAR_VENDA_ITEM_REDE` ou `/INTEGRACAO/VENDA_REDE`, as quais retornam erro técnico 401).
* **`OPERACIONAL_FILIAL`**: **PARCIAL** (Acesso total apenas para as duas filiais autorizadas `5555` e `11495`, restando 8 filiais bloqueadas por filtro nominal de dados na base SQL do ERP).

---

## 7. Respostas Diretas às Dúvidas da Holding (6 Perguntas Esperadas)

### 1. O token tem acesso financeiro de rede?
**Sim.** A API central financeira do WebPosto está perfeitamente disponível e vinculada. Conseguimos extrair despesas e faturas consolidadas de faturamentos indiretos das 10 filiais corporativas de maneira centralizada chamando os endpoints financeiros corporativos de rede.

### 2. O token tem acesso operacional de rede?
**Não.** Os endpoints voltados ao operacional de rede (como listagens integradas de volumes vendidos, encerramentos agregados ou LMC de rede) estão bloqueados a nível de rota HTTP (HTTP 401), invalidando chamadas integradas centralizadoras.

### 3. O token tem acesso operacional por filial?
**Parcialmente.** Há permissão técnica apenas para acessar de forma isolada os dados de vendas (`VENDA_ITEM`), estoque total (`PRODUTO_ESTOQUE`) e litragem física (`ABASTECIMENTO`) das empresas **5555** e **11495**. No entanto, as outras 8 filiais da rede retornam listas vazias na camada de segurança do banco de dados, falhando silenciosamente.

### 4. Quais endpoints respeitam escopo de rede?
Apenas o endpoint financeiro centralizado `/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE` e o mapeamento cadastral de empresas de infraestrutura `/INTEGRACAO/EMPRESAS` respeitam e respondem com o escopo consolidado da holding em lote único.

### 5. Quais endpoints respeitam escopo nominal?
Os endpoints `/INTEGRACAO/VENDA_ITEM`, `/INTEGRACAO/PRODUTO_ESTOQUE`, `/INTEGRACAO/PRODUTO_EMPRESA`, `/INTEGRACAO/CAIXA` e `/INTEGRACAO/ABASTECIMENTO`. Eles exigem o parâmetro `empresaCodigo` como ID de restrição, mas apenas processam dados para o escopo de CNPJs whitelists ligados diretamente à credencial no provedor (no caso, apenas `5555` e `11495`).

### 6. Quais dados precisamos solicitar à Quality Automação?
Precisamos que a Quality altere as permissões do usuário que gerou esta credencial API, vinculando as outras 8 filiais de rede ao seu grupo operacional, ou que ative de uma vez por todas a permissão de rota para as rotas unificadas de rede (`_REDE`).

---

## 8. Documento para Quality Automação — Liberação Operacional

Como ação corretiva obrigatória a ser compartilhada com a Quality, apresentamos abaixo o escopo formal de requisição de liberação operacional e sincronização do ERP de forma limpa e direta:

---

### Solicitativa de Suporte ao Integrador Quality Automação

**Identificação do Cliente**: Grupo Lisboa  
**Canal**: Suporte Técnico - Integração Terceiros API WebPosto  

Prezados,

Durante a homologação técnica da nossa nova interface de Business Intelligence corporativa, detectamos que o Token de Integração em produção possui permissão administrativa corporativa apenas para escopo de consolidação financeira de despesas, mas possui bloqueios de escopo nos endpoints do módulo comercial de combustíveis.

Diante do exposto, solicitamos apoio para as seguintes configurações:

#### 1. Confirmação e Validação do Escopo Atual do Token
Solicitamos confirmação técnica se o token atual ativo possui escopo liberado de forma unificada nas tabelas de banco para:
- **Financeiro Rede**: (Atualmente: SIM)
- **Operacional Rede**: (Atualmente: NÃO - erro HTTP 401)
- **Vendas Rede**: (Atualmente: NÃO - erro HTTP 401)
- **Estoque Rede**: (Atualmente: NÃO)
- **Caixa Rede**: (Atualmente: PARCIAL - limita-se apenas a duas filiais)
- **Abastecimento Rede**: (Atualmente: PARCIAL - limita-se apenas a duas filiais)

#### 2. Liberação e Configuração de Endpoints de Rede
Solicitamos a liberação técnica de acesso em nossa chave de TI (ACL de Plataforma) para os seguintes endpoints unificados corporativos, necessários para calcularmos o market share consolidado e o estoque físico unificado da holding:

- `CONSULTAR_VENDA_ITEM_REDE` (Rota: `/INTEGRACAO/CONSULTAR_VENDA_ITEM_REDE`)
- `CONSULTAR_VENDA_REDE` (Rota: `/INTEGRACAO/VENDA_REDE`)
- `CONSULTAR_ABASTECIMENTO_REDE` (Rota: `/INTEGRACAO/ABASTECIMENTO_REDE`)
- `CONSULTAR_PRODUTO_EMPRESA_REDE` (Rota: `/INTEGRACAO/PRODUTO_EMPRESA_REDE`)
- `CONSULTAR_PRODUTO_ESTOQUE_REDE` (Rota: `/INTEGRACAO/PRODUTO_REDE` / `/INTEGRACAO/ESTOQUE_PERIODO`)

#### 3. Alternativa de Vínculo de Whitelist em Endpoints de Filial Local
Caso a política de segurança da Quality não autorize o uso dos endpoints do prefixo/sufixo `_REDE` consolidados, solicitamos que as seguintes **8 filiais** restantes sejam operacionalmente vinculadas de forma nominal ao escopo cadastral do Token, permitindo que a API local (ex: `/INTEGRACAO/VENDA_ITEM?empresaCodigo=...`) forneça os resultados em vez de retornar dados vazios:

- **5256** (Posto Vip filial 2)
- **5333** (Posto Aliança)
- **5556** (Posto Imperial)
- **5557** (Posto Norte)
- **5559** (Posto Master)
- **5560** (Posto Sul)
- **46433** (Posto Novo Horizonte)
- **74014** (Posto Bela Vista)

A liberação destes dados é essencial para a homologação do módulo operacional de auditoria de litros de combustíveis no nosso dashboard executivo.

Ficamos no aguardo da liberação e do retorno técnico.

Atenciosamente,  
**Equipe de Engenharia de Integração — Grupo Lisboa**
