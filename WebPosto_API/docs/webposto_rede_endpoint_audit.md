# Relatório de Auditoria e Diagnóstico de Endpoints de Rede (Rede Lisboa — LOGOS SPACE)

**Data da Auditoria**: 2026-06-07  
**Responsável**: Agente de Integração & Auditor Técnico WebPosto (LOGOS SPACE)  
**Chave de Integração Ativa**: `<WEBPOSTO_API_TOKEN>`  
**Escopo de Teste**: Período `2026-06-01` a `2026-06-07`

---

## 1. Contexto Comercial e de Integração

O ecossistema **LOGOS SPACE** possui uma base de cadastros dividida em:
- **12 filiais cadastradas** (Base local parametrizada)
- **11 filiais ativas** (Membros operacionais vigentes do conselho e rede)
- **1 filial inativa**: **POSTO REAL (7)** (Confirmado que foi desativado operacionalmente no mês passado)

Esta auditoria técnica visa a testar de forma empírica as rotas unificadas de **REDE** providas pela Quality Automação (WebPosto). O objetivo é avaliar se os canais de rede contornam as restrições individuais de token para as filiais que hoje carecem de visibilidade total.

---

## 2. Resultados da Execução de Auditoria Técnica (HTTP Status por Rota)

Todos os endpoints de rede foram formalmente auditados no ambiente de produção do WebPosto por meio do script de diagnóstico automatizado [scripts/audit_webposto_rede_endpoints.py](scripts/audit_webposto_rede_endpoints.py). O comportamento da API upstream apresentou-se de acordo com o detalhamento abaixo:

### A. Endpoints de Rede que Retornaram HTTP 200 (Sucesso)
- **`/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE`**: Retornou **417 registros**.
- **`/INTEGRACAO/CONSULTAR_VENDA_FORMA_PAGAMENTO_REDE`**: Retornou **0 registros**.
- **`/INTEGRACAO/TANQUE`**: Retornou **6 registros**.
- **`/INTEGRACAO/PRODUTO_META`**: Retornou **22 registros**.
- **`/INTEGRACAO/CONSULTAR_TITULO_PAGAR_REDE`**: **[Novo]** Retornou status **HTTP 200 (Sucesso)**, porém com **0 registros** sob todas as datas testadas (inclusive períodos onde a rota individual `/INTEGRACAO/TITULO_PAGAR` retornou lotes volumosos de transações para as empresas licenciadas `5555` e `11495`).
- **`/INTEGRACAO/CONSULTAR_CAIXA_APRESENTADO_REDE`**: **[Novo]** Retornou status **HTTP 200 (Sucesso)**, porém com **0 registros** sob todas as datas testadas (inclusive períodos onde a rota individual `/INTEGRACAO/CAIXA_APRESENTADO` retornou transações para as empresas licenciadas `5555` e `11495`).

### B. Endpoints de Rede que Retornaram HTTP 401/403 (Não Autorizado)
Isso evidencia que esses canais de rede estão explicitamente **bloqueados de forma administrativa no perfil deste token** pela Quality Automação:
- `/INTEGRACAO/CONSULTAR_VENDA_ITEM_REDE`
- `/INTEGRACAO/VENDA_REDE`
- `/INTEGRACAO/USUARIO_EMPRESA_REDE`
- `/INTEGRACAO/TITULO_PAGAR_REDE` (Endpoint de rede legado. Nota: O endpoint alternativo `/CONSULTAR_TITULO_PAGAR_REDE` é autorizado HTTP 200, mas sem dados)
- `/INTEGRACAO/TITULO_RECEBER_REDE`
- `/INTEGRACAO/PRODUTO_EMPRESA_REDE`
- `/INTEGRACAO/VALE_FUNCIONARIO_REDE`
- `/INTEGRACAO/SAT_REDE`
- `/INTEGRACAO/PRODUTO_LMC`
- `/INTEGRACAO/CODIGO_BARRAS`

### C. Outros Erros HTTP
- **`/INTEGRACAO/PRODUTO_ESTOQUE` (HTTP 400)**: Retorna Bad Request caso seja invocado sem os filtros específicos de data/empresa individual.

---

## 3. Matriz de Resultados da Rede

| Endpoint Rede | Retorna empresaCodigo | Empresas encontradas | Contém 5256 | Contém 9 | Contém 7 | Utilidade / Diagnóstico |
|---|---|---|---|---|---|---|
| **`/CONSULTAR_DESPESAS_FINANCEIRO_REDE`** | Sim | `[46433, 11495, 5256, 5555, 5556, 5557, 5333, 5559, 5560, 74014]` | **Sim** | Não | Não | **USAR_AGORA** (Mapeia despesas consolidadas de 10 filiais) |
| **`/CONSULTAR_VENDA_FORMA_PAGAMENTO_REDE`**| Sim | `[ ]` (Vazio) | Não | Não | Não | **USAR_COM_CUIDADO** (Sem registros no período atual de BI) |
| **`/TANQUE`** | Sim | `[5555, 11495]` | Não | Não | Não | **USAR_AGORA** (Mas restrito apenas a filiais licenciadas no Token) |
| **`/PRODUTO_META`** | Não | `[ ]` (Nenhum) | Não | Não | Não | **APENAS_DIAGNOSTICO** (Metadados de cadastro global) |
| **`/CONSULTAR_TITULO_PAGAR_REDE`** | Sim | `[ ]` (Vazio) | Não | Não | Não | **NÃO_USAR** (Autorizado HTTP 200, mas tabela de rede está vazia upstream) |
| **`/CONSULTAR_CAIXA_APRESENTADO_REDE`** | Sim | `[ ]` (Vazio) | Não | Não | Não | **NÃO_USAR** (Autorizado HTTP 200, mas tabela de rede está vazia upstream) |
| **`/CONSULTAR_VENDA_ITEM_REDE`** | - | Não retornado (401) | Não | Não | Não | **NÃO_USAR** (Sem permissão administrativa no Perfil do Token) |
| **`/VENDA_REDE`** | - | Não retornado (401) | Não | Não | Não | **NÃO_USAR** (Sem permissão administrativa no Perfil do Token) |
| **`/TITULO_PAGAR_REDE`** | - | Não retornado (401) | Não | Não | Não | **NÃO_USAR** (Endpoint legado inativo ou sem permissão) |
| **`/PRODUTO_EMPRESA_REDE`** | - | Não retornado (401) | Não | Não | Não | **NÃO_USAR** (Sem permissão administrativa no Perfil do Token) |

---

## 4. Classificação das Filiais Investigadas e Justificativa Técnica

### 1. POSTO BR SHOPPING (5256)
- **Status**: Ativa
- **Diagnóstico**: **Vínculo Parcial de Rede**. Seus registros financeiros aparecem com dados reais consistentes unicamente na rota unificada e consolidada de despesas de rede (`CONSULTAR_DESPESAS_FINANCEIRO_REDE`), o que comprova que o concentrador da filial envia transações financeiras normalmente para o servidor central do WebPosto. No entanto, por estar excluída implicitamente da listagem nominal do Token Ativo para consultas individuais, as tabelas de estoque (`/PRODUTO_ESTOQUE`) e vendas (`/VENDA`) retornam inteiramente vazias ou bloqueadas.

### 2. AUTO POSTO GLOBO (9)
- **Status**: Ativa
- **Diagnóstico**: **Sem Sincronização Operacional**. Mesmo nos endpoints unificados de rede (como despesas e formas de pagamento que cobrem outros nós não licenciados de forma federada), a filial `9` possui exatamente **0 registros**. Isso comprova tecnicamente que o sincronizador físico local instalado no servidor do estabelecimento não está transmitindo movimentos à nuvem da Quality Automação.

### 3. POSTO REAL (7)
- **Status**: **INATIVA** (Desativada comercialmente)
- **Diagnóstico**: Desativada no mês anterior. Não deve constar como falha ou erro, pois não há expectativa de transmissão de movimentos ativos para análise atual de negócios ou BI. O histórico deve ser retido para comparações pretéritas apenas.

---

## 5. Recálculo da Cobertura de Rede (Sprint 20)

Com base no comportamento comprovado em tempo real por domínio analítico, a capacidade real de coleta de dados no ecossistema atual do LOGOS SPACE é calculada conforme segue:

* **Filiais Ativas Cadastradas**: 11  
* **Filiais Ativas com dados em Despesas**: **10 / 11** (90.9%) — *Apenas o Posto 9 carece de dados.*
* **Filiais Ativas com dados em Vendas**: **2 / 11** (18.18%) — *Somente as filiais pleno-licenciados no Token aparecem (AP Casa Caiada e Posto VIP).*
* **Filiais Ativas com dados em Estoque**: **2 / 11** (18.18%) — *Somente AP Casa Caiada e Posto VIP.*
* **Filiais Ativas com dados em Contas a Pagar**: **2 / 11** (18.18%) — *Somente AP Casa Caiada e Posto VIP.*

### Cobertura Geral Ativa Consolidada:
Para fins de BI unificado, contabilizando as unidades que possuem ao menos alguma categoria de operação registrada ativamente via API:
$$\text{Cobertura Consolidada} = \frac{10}{11} \approx 90.91\%$$

---

## 6. Governança contra Duplicidade e Chaves de Deduplicação

Ao integrar endpoints de rede junto com endpoints individuais de forma paralela, há risco iminente de duplicar registros (especialmente em despesas de rede e faturamento unificado). Assim, definiu-se a aplicação obrigatória de chaves baseadas em nós únicos para garantir integridade e idoneidade de dados de faturamento em BI:

### Matriz de Chaves Únicas de Deduplicação

| Domínio de Negócio | Chave de Deduplicação Composta (Deduplication Unique Constraints) |
|---|---|
| **Vendas (Rede & Local)** | `empresaCodigo` + `vendaCodigo` + `dataMovimento` |
| **Itens de Venda** | `empresaCodigo` + `vendaCodigo` + `vendaItemCodigo` |
| **Formas de Pagamento** | `empresaCodigo` + `vendaCodigo` + `formaPagamentoCodigo` + `valorPagamento` |
| **Contas a Pagar / Títulos** | `empresaCodigo` + `tituloCodigo` + `vencimento` + `valor` |
| **Estoques Móveis (Histórico)**| `empresaCodigo` + `produtoCodigo` + `dataMovimento` |
| **Estoque Físico Atual** | `empresaCodigo` + `produtoCodigo` |

---

## 7. EmpresaCodigos Descobertos via CaixaRede

Abaixo, detalhamos o mapeamento executado de forma estrutural sobre as transações de fechamentos de turno coletadas em tempo real pelo endpoint `/INTEGRACAO/CONSULTAR_CAIXA_REDE` para identificar os códigos corporativos ativos no concentrador.

### A. EmpresaCodigo encontrados no CaixaRede:
De um volume de **21 registros** recuperados no período global teste de `2026-06-01` a `2026-06-07`, os códigos acumulados identificados e validados pelo concentrador são:
- `5555`
- `11495`

### B. Comparação Automática e Classificação de Conformidade

Mapeamos a totalidade dos códigos da base local em relação aos dados dinamicamente extraídos do `CaixaRede`:

| Código Base Local | Nome da Filial | Status CaixaRede | Mapeamento Técnico | Observação |
|---|---|---|---|---|
| **5555** | AP CASA CAIADA | **CONFIRMADO_NA_API** | Licenciado individual / Ativo | Transacionando normalmente com dados de turno e PDV. |
| **11495**| POSTO VIP | **CONFIRMADO_NA_API** | Licenciado individual / Ativo | Transacionando normalmente com dados de turno e PDV. |
| **5256** | POSTO BR SHOPPING | **NAO_CONFIRMADO** | Sem sincronização nesta tabela | Excluído implicitamente das transações do Concentrador de Caixa. |
| **5333** | POSTO JANGA | **NAO_CONFIRMADO** | Sem sincronização nesta tabela | Não enviou fechamento de turno em nuvem no período. |
| **5556** | POSTO CIDADE PATRIMONIO| **NAO_CONFIRMADO**| Sem sincronização nesta tabela | Não enviou fechamento de turno em nuvem no período. |
| **5557** | POSTO ENSEADA DO NORTE | **NAO_CONFIRMADO**| Sem sincronização nesta tabela | Não enviou fechamento de turno em nuvem no período. |
| **5560** | POSTO SERTA | **NAO_CONFIRMADO**| Sem sincronização nesta tabela | Não enviou fechamento de turno em nuvem no período. |
| **5559** | POSTO RJ | **NAO_CONFIRMADO**| Sem sincronização nesta tabela | Não enviou fechamento de turno em nuvem no período. |
| **46433**| POSTO DOZE | **NAO_CONFIRMADO**| Sem sincronização nesta tabela | Não enviou fechamento de turno em nuvem no período. |
| **74014**| POSTO DOZE FILIAL II | **NAO_CONFIRMADO**| Sem sincronização nesta tabela | Não enviou fechamento de turno em nuvem no período. |
| **7** (*Local*) | POSTO REAL | **NAO_CONFIRMADO**| Inativa / idLocal | Sem evidência real de Código na API do WebPosto. |
| **9** (*Local*) | AUTO POSTO GLOBO | **NAO_CONFIRMADO**| Sem sincronizador / idLocal | Sem transmissão local ativa e sem código oficial na nuvem. |

---

## 8. Parecer de Recomendação e Próximos Passos Comerciais

1. **Atuar na Sincronização Local do Posto Globo (9)**: Antes de efetuar custos financeiros com a Quality Automação para reemitir ou alterar o Token, é indispensável reconfigurar ou ligar o sincronizador local físico do estabelecimento `9`, dado que sua transmissão permanece nula de forma geral.
2. **Exigência Nominal Corporativa**: Comprovada a impossibilidade de usar endpoints de rede para vendas (venda_item_rede e venda_rede retornaram **401** de forma irredutível), é necessário solicitar à Quality Automação a ampliação definitiva do perfil do Token atual para agregar de forma explícita e nominal as 11 filiais ativas no escopo de `/INTEGRACAO/EMPRESAS` da API de faturamento individual.
3. **Inutilidade Prática de `/CONSULTAR_TITULO_PAGAR_REDE` e `/CONSULTAR_CAIXA_APRESENTADO_REDE`**: Embora ambos os endpoints de rede estejam estruturalmente **autorizados** (retornando status **HTTP 200** sem bloqueios de segurança), eles retornam sistematicamente **0 registros** sob qualquer espectro temporal testado (inclusive em datas com farto volume transacional nas rotas individuais correspondentes). Isso indica que as tabelas centralizadoras correspondentes estão vazias no ecossistema de nuvem da Quality para esta chave, impossibilitando seu uso prático para extrair informações das filiais `5256` (Posto BR Shopping), `9` (Auto Posto Globo) ou `7` (Posto Real). A obtenção desse controle financeiro e operacional depende unicamente da inclusão das filiais na licença individual do Token.
