**SOLICITAÇÃO TÉCNICA**

**Permissões de Acesso --- API REST webPosto**

**Contato Técnico:** marcio\@grupolisboa.com.br

**Data:** 08/04/2026

**Organização:** Grupo Lisboa

1. Escopo Técnico
=================

Solicitamos geração de chave de integração do tipo **API Integração**
(API REST v1) com permissões de leitura em **TODOS** os módulos
operacionais disponibilizados, conforme especificado na documentação
\"Utilizando API REST\".

1.1 Clarificação: Diferença entre Chave BI (atual) e API REST (solicitada)
--------------------------------------------------------------------------

**Chave BI (Atualmente em seu poder --- criada internamente):**

-   Acesso limitado a relatórios de Business Intelligence

-   NÃO fornece acesso aos endpoints operacionais (Clientes, Produtos,
    Abastecimentos, Financeiro, Caixa, etc.)

-   Limitado para leitura de subconjuntos específicos de dados
    analíticos

**API REST (Solicitada neste documento):**

-   Acesso completo aos módulos operacionais (Clientes, Produtos,
    Abastecimentos, Financeiro, Movimentos de Caixa, Caixa, Cartões,
    Relatórios)

-   Permissões de leitura (GET) em todos os endpoints documentados
    abaixo (Fase 1)

-   Permissões de escrita (POST/PUT) para operações de criação e
    atualização (Fase 2 --- imediata após validação da Fase 1)

-   Necessária para automação operacional completa do Grupo Lisboa

2. Módulos e Endpoints Solicitados
==================================

2.1 Módulo: Clientes
--------------------

  **Endpoint**                   **Método**
  ------------------------------ ------------
  /api/v1/clientes               GET
  /api/v1/clientes/{id}          GET
  /api/v1/clientes/{id}/frota    GET
  /api/v1/clientes/grupos        GET
  /api/v1/clientes/{id}/prazos   GET

2.2 Módulo: Produtos
--------------------

  **Endpoint**                       **Método**
  ---------------------------------- ------------
  /api/v1/produtos                   GET
  /api/v1/produtos/{id}/precos       GET
  /api/v1/produtos/{id}/inventario   GET
  /api/v1/produtos/tributos/icms     GET

2.3 Módulo: Abastecimentos
--------------------------

-   /api/v1/abastecimentos

```{=html}
<!-- -->
```
-   GET (com filtros de data)

```{=html}
<!-- -->
```
-   /api/v1/abastecimentos/{id}

```{=html}
<!-- -->
```
-   GET

2.4 Módulo: Financeiro (Prioridade Alta)
----------------------------------------

  **Endpoint**                                        **Método**
  --------------------------------------------------- ------------
  /api/v1/financeiro/titulos-receber                  GET
  /api/v1/financeiro/titulos-pagar                    GET
  /api/v1/financeiro/transferencias                   GET
  /api/v1/financeiro/lancamentos-contabeis            GET
  /api/v1/financeiro/plano-contas                     GET
  /api/v1/financeiro/movimentos-conta                 GET
  /api/v1/financeiro/exclusoes                        GET
  /integracao/financeiro\_exclusao                    GET
  /integracao/financeiro\_exclusao/retorno-paginado   GET

2.5 Módulo: Movimentos de Caixa (Prioridade Alta)
-------------------------------------------------

-   /integracao/movimento\_conta

```{=html}
<!-- -->
```
-   GET (listagem de movimentos de conta)

```{=html}
<!-- -->
```
-   /integracao/movimento\_conta/retorno-paginado

```{=html}
<!-- -->
```
-   GET (retorno paginado)

2.6 Módulo: Caixa (Prioridade Alta)
-----------------------------------

-   /api/v1/caixa/fechamentos

```{=html}
<!-- -->
```
-   GET (listagem de fechamentos por período)

```{=html}
<!-- -->
```
-   /api/v1/caixa/movimentos

```{=html}
<!-- -->
```
-   GET (movimentações detalhadas)

```{=html}
<!-- -->
```
-   /api/v1/caixa/saldos

```{=html}
<!-- -->
```
-   GET (saldos atualizados por caixa)

```{=html}
<!-- -->
```
-   /integracao/caixa\_rede

```{=html}
<!-- -->
```
-   GET (listagem de caixas da rede)

```{=html}
<!-- -->
```
-   /integracao/caixa\_rede/retorno-paginado

```{=html}
<!-- -->
```
-   GET (retorno paginado)

```{=html}
<!-- -->
```
-   /integracao/caixa\_apresentado\_rede

```{=html}
<!-- -->
```
-   GET (caixas apresentados na rede)

```{=html}
<!-- -->
```
-   /integracao/caixa\_apresentado\_rede/retorno-paginado

```{=html}
<!-- -->
```
-   GET (retorno paginado)

2.7 Módulo: Cartões de Crédito
------------------------------

-   /api/v1/cartoes/administradoras

-   /api/v1/cartoes/pagamentos

-   /api/v1/cartoes/autorizacoes

2.8 Módulo: Relatórios
----------------------

-   /api/v1/relatorios/vendas-produto

-   /api/v1/relatorios/vendas-combustivel

-   /api/v1/relatorios/resumo-vendas

-   /api/v1/relatorios/estoque

3. Especificações Técnicas da Integração
========================================

**Arquitetura:** Cliente Python 3.11+ com biblioteca requests

**Protocolo:** HTTP/HTTPS com autenticação via query parameter CHAVE

**Padrão de Resposta:** JSON com status codes HTTP (200, 204, 400, 403,
404, 500+)

**Retry:** Backoff exponencial em 429, 500, 502, 503, 504

**Tratamento de Erro:** Exceções tipadas (AuthError, BadRequestError,
ServerError)

4. Plano de Implementação
=========================

4.1 Fase 1: Validação (GET)
---------------------------

-   Ativar permissões de leitura em todos os módulos acima

-   Testar conectividade em cada endpoint via Swagger

-   Validar formatos de resposta JSON

4.2 Fase 2: Escrita (POST/PUT)
------------------------------

-   Após validação da Fase 1, solicitar permissões de escrita

-   Implementar operações de criação e atualização

-   Iterar com time Quality para validar formatos de entrada

5. Informações de Contato
=========================

**Email Técnico:** marcio\@grupolisboa.com.br

**Documentação Referência:** Utilizando API REST (webPosto Confluence)
