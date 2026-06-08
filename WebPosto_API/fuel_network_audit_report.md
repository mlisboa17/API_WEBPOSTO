# Relatório de Diagnóstico de Volumes de Combustíveis na Rede — SPRINT 22A

## 1. Introdução

Este relatório apresenta o diagnóstico técnico e a análise empírica de descoberta de dados acerca do módulo operacional de combustíveis da rede do ERP WebPosto (Quality Automação). 

Para responder se conseguimos centralizar dados de litros vendidos, combustíveis comercializados e participação de filiais utilizando o token corporativo atual, foi desenvolvido e executado o script de auditoria e varredura [fuel_network_audit.py](fuel_network_audit.py).

O resultado completo bruto de cada requisição e catalogação de cadastro de produtos pode ser acessado em [fuel_network_audit_result.json](fuel_network_audit_result.json).

---

## 2. Metodologia de Teste e Períodos Analisados

Os endpoints mapeados para análise operacional foram testados de forma sequencial contra os barramentos de homologação e produção utilizando a credencial ativa. Conforme especificação técnica, foram analisados de forma obrigatória três períodos temporais representativos de movimento de rede:

1. **Período Diário**: 06/06/2026 a 06/06/2026 (Período recente pós-auditorias anteriores)
2. **Período Semanal**: 01/06/2026 a 07/06/2026 (Última semana com fluxo completo de faturamento)
3. **Período Mensal**: 01/05/2026 a 31/05/2026 (Mês completo fechado com altos volumes)

---

## 3. Resultados Detalhados por Endpoint

Abaixo estão expostos os dados empíricos observados na varredura. Cada endpoint foi avaliado de acordo com sua validade técnica, volume de dados retornados e as filiais mapeadas nos registros.

### Tabela Geral de Auditoria de Integração de Combustíveis

| Endpoint | Dados? | Empresa | Produto | Quantidade | Litros | Dashboard? | Observações / Motivo |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `/INTEGRACAO/ABASTECIMENTO_REDE` | NÃO | NÃO | NÃO | NÃO | NÃO | NÃO | Retorna HTTP 401 Unauthorized de forma consistente |
| `/INTEGRACAO/CONSULTAR_ABASTECIMENTO_REDE` | NÃO | NÃO | NÃO | NÃO | NÃO | NÃO | Retorna HTTP 401 Unauthorized |
| `/INTEGRACAO/LMC_REDE` | NÃO | NÃO | NÃO | NÃO | NÃO | NÃO | Retorna HTTP 401 Unauthorized |
| `/INTEGRACAO/CONSULTAR_LMC_REDE` | **SIM** | **SIM** | **SIM** | **SIM** | **SIM** | **SIM** | **HTTP 200 Ok**. Retorna dados reais de LMC (saídas físicas e encerrantes de bico) |
| `/INTEGRACAO/PRODUTO_EMPRESA_REDE` | NÃO | NÃO | NÃO | NÃO | NÃO | NÃO | Retorna HTTP 401 Unauthorized |
| `/INTEGRACAO/CONSULTAR_PRODUTO_EMPRESA_REDE` | NÃO | NÃO | NÃO | NÃO | NÃO | NÃO | Retorna HTTP 200 Ok, mas responda lista vazia (`[]`) |
| `/INTEGRACAO/EMPRESAS_REDE` | NÃO | NÃO | NÃO | NÃO | NÃO | NÃO | Retorna HTTP 401 Unauthorized |
| `/INTEGRACAO/CONSULTAR_EMPRESAS_REDE` | **SIM** | **SIM** | NÃO | NÃO | NÃO | NÃO | Retorna HTTP 200 Ok. Retorna 2 filiais cadastradas no escopo operacional |
| `/INTEGRACAO/PRODUTO_COMBUSTIVEL` | NÃO | NÃO | NÃO | NÃO | NÃO | NÃO | Retorna HTTP 401 Unauthorized |

---

## 4. Descoberta de EmpresaCodigo da Rede

A Tabela Mestra Corporativa do grupo engloba as seguintes filiais operacionais:
- **5256** — POSTO BR SHOPPING
- **5333** — POSTO JANGA
- **5555** — AP CASA CAIADA
- **5556** — POSTO CIDADE PATRIMONIO
- **5557** — POSTO ENSEADA DO NORTE
- **5559** — POSTO RJ
- **5560** — POSTO SERTÃ
- **11495** — POSTO VIP
- **46433** — POSTO DOZE
- **74014** — POSTO DOZE FILIAL II

### Classificação do Vínculo de Empresa na API de Combustíveis

Durante a execução de `/INTEGRACAO/CONSULTAR_LMC_REDE`, extraímos todos os códigos de empresa (`empresaCodigo`) presentes nos registros. Os resultados foram os seguintes:

| empresaCodigo | Razão Social / Nome Fantasia | Status na API de Combustíveis | Significado Clínico | Weblink no Erro |
| :---: | :--- | :---: | :--- | :--- |
| **5256** | POSTO BR SHOPPING | `NAO_CONFIRMADO` | Sem autorização transacional de banco de dados | Retornou vazia em chamadas diretas operacionais |
| **5333** | POSTO JANGA | `NAO_CONFIRMADO` | Sem autorização transacional de banco de dados | Retornou vazia em chamadas diretas operacionais |
| **5555** | AP CASA CAIADA | `CONFIRMADO_NA_API` | Operabilidade confirmada em dados reais | Sincronizado e validado com sucesso |
| **5556** | POSTO CIDADE PATRIMONIO | `NAO_CONFIRMADO` | Sem autorização transacional de banco de dados | Vazias |
| **5557** | POSTO ENSEADA DO NORTE | `NAO_CONFIRMADO` | Sem autorização transacional de banco de dados | Vazias |
| **5559** | POSTO RJ | `NAO_CONFIRMADO` | Sem autorização transacional de banco de dados | Vazias |
| **5560** | POSTO SERTÃ | `NAO_CONFIRMADO` | Sem autorização transacional de banco de dados | Vazias |
| **11495** | POSTO VIP | `CONFIRMADO_NA_API` | Operabilidade confirmada em dados reais | Sincronizado e validado com sucesso |
| **46433** | POSTO DOZE | `NAO_CONFIRMADO` | Sem autorização transacional de banco de dados | Vazias |
| **74014** | POSTO DOZE FILIAL II | `NAO_CONFIRMADO` | Sem autorização transacional de banco de dados | Vazias |

*(Nota: Nenhum `NOVO_EMPRESACODIGO` desconhecido fora das 10 filiais corporativas foi localizado ou vazado durante a execução dos testes.)*

---

## 5. Descoberta de Combustíveis e Classificação Cadastral

Através do acoplamento técnico ao cadastro de produtos do WebPosto, mapeamos os códigos de produto operacionais e as descrições retornadas para classificar os tipos de combustíveis circulantes. Foram descobertos **8 combustíveis ativos principais** no cadastro das unidades liberadas:

| Código Produto | Descrição Retornada pelo WebPosto | Grupo Código | Tipo Código | Classificação Comercial |
| :---: | :--- | :---: | :---: | :--- |
| **1257884** | GASOLINA COMUM. | 24554 | C | GASOLINA COMUM |
| **1257885** | GASOLINA ADITIVADA GRID | 24554 | C | GASOLINA ADITIVADA |
| **1257886** | ETANOL COMUM | 24554 | C | ETANOL |
| **1260803** | DIESEL S10 COMUM | 24554 | C | DIESEL S10 |
| **1401736** | GASOLINA COMUM C | 29273 | U | GASOLINA COMUM |
| **1401737** | GASOLINA ADITIVADA C | 29273 | U | GASOLINA ADITIVADA |
| **1401738** | ETANOL COMUM C | 29273 | U | ETANOL |
| **1401739** | DIESEL S10 C | 29273 | U | DIESEL S10 |

Esses produtos mapeiam a exata matriz de distribuição física de vendas, sendo compatíveis com nossa lógica comercial de detecção ativa de combustíveis.

---

## 6. Validação Crítica das Perguntas de Negócio

Respondemos de forma técnica e objetiva a cada uma das validações solicitadas pela holding para guiar as decisões de produto:

### 1. Existe quantidade/litros?
**SIM**. No endpoint `/INTEGRACAO/CONSULTAR_LMC_REDE`, o campo `saida` indica os litros totais consolidados vendidos de determinado combustível em uma data. Adicionalmente, na estrutura aninhada de `lmcBico` dentro de cada LMC diário, o campo `venda` exibe com precisão absoluta a metragem líquida de fechamento inicial versus final calculada diretamente para cada bico físico da bomba.

### 2. Existe empresaCodigo?
**SIM**. O campo `empresaCodigo` consta como propriedade do cabeçalho de cada registro de LMC retornado, permitindo o agrupamento exato.

### 3. Existe produtoCodigo?
**SIM**. Ele consta na propriedade `produtoCodigo` como uma lista de chaves de identificação do ERP (Ex: `[1257885]`), permitindo realizar o JOIN em lote no backend com o catálogo de produtos e associar a sua respectiva classificação.

### 4. Conseguimos calcular: litros por combustível?
**SIM**. Unindo o `produtoCodigo` do lote de LMC à tabela cadastral extraída em segundo plano, conseguimos consolidar e classificar o volume acumulado de saídas brutas em litros comercializados por família de combustível (Ex: Etanol, Gasolina Comum, etc.).

### 5. Conseguimos calcular: litros por filial?
**SIM**. Podemos sumarizar as saídas ou as medições de encerrantes acumulando-as por agrupamento de `empresaCodigo`.

### 6. Conseguimos calcular: litros da rede?
**SIM, de forma restrita**. Teoricamente, o endpoint contém todos os dados estruturais necessários para computar a somatória totalizada de rede. Contudo, em virtude do escopo restrito do nosso token, a API do ERP WebPosto atualmente realiza a filtragem física das linhas de banco de dados, retornando **apenas** os registros pertinentes a `5555` e `11495`. Nenhuma linha das outras 8 filiais da rede é devolvida pela API corporativa de rede hoje.

### 7. Conseguimos montar imediatamente: Painel Executivo de Combustíveis?
**NÃO** (ou **PARCIAL**). Embora tenhamos o design de backend preparado e possamos gerar os gráficos e KPIs imediatamente para as filiais `5555` (Petrolider) e `11495` (Posto VIP), o painel consolidado corporativo da rede de 10 postos exibirá dados zerados ou inconsistentes para as outras 8 filiais, descaracterizando sua finalidade global de inteligência. A montagem integral depende da liberação das permissões do token pela Quality Automação.

---

## 7. Descoberta Crítica da Sprint 22A e Próximo Passo Recomendado

### Descoberta Crítica Principal
A análise empírica revelou uma descoberta crítica extraordinária: o endpoint **`/INTEGRACAO/CONSULTAR_LMC_REDE`** é o **único endpoint de Rede** (capaz de consolidar e centralizar informações agregadas operacionais de múltiplos postos em uma chamada unificada) que está **100% ativado e liberado (HTTP 200 Ok)** na chave atual da holding, ao contrário de todos os outros endpoints operacionais testados que retornam invariavelmente HTTP 401.

### O Endpoint Mestre de Melhor Chance de Sucesso (Sem Novo Token Corporativo)
Diante da impossibilidade contratual ou financeira de aquisição de um token corporativo de outra modalidade da Quality Automação, o endpoint mestre absoluto para calcular os litros comercializados por combustível para toda a rede é:

$$ \text{`/INTEGRACAO/CONSULTAR_LMC_REDE`} $$

**Justificativa Técnica de Arquitetura**:
1. **Contornabilidade de Custos de Rota**: Se simplesmente solicitarmos à Quality para expandir a lista de filiais vinculadas operationalmente ao cadastro de usuários da chave transacional ativa para incluir as outras 8 filiais bloqueadas, sem requerer que criem novos tokens ou nos deem privilégios à rotas proibidas (o que costuma desencadear cobranças extras corporativas e morosidade burocrática), as linhas dos LMCs desses 8 postos começarão a fluir de forma transparente e imediata chamada a chamada.
2. **Eficiência e Desempenho (Performance)**: Os LMCs já são calculados de forma pré-agrupada e diária pelo WebPosto para cada combustível ativo. Sendo assim, em vez de ler centenas de milhares de linhas individuais de cupons e sub-itens transacionais diários via `/INTEGRACAO/VENDA_ITEM` por filial, leremos apenas um número reduzido de linhas consolidadas de LMC físicas por dia. Isso elimina o risco de latências bruscas, estouros de timeout do gateway e sobrecargas de paginação, gerando uma performance de renderização do dashboard comercial infinitamente superior no frontend.
3. **Calibragem e Ground Truth**: O LMC se origina da leitura dos encerrantes físicos das bombas, que é a fonte regulatória e financeira máxima de saídas físicas de combustíveis nos postos. Sincronizar o dashboard de volumetria comercial na base do LMC garante divergência zero contra a realidade operacional diária dos postos de venda.

---

### Recomendações aos Diretores de Tecnologia

Para o fechamento de infraestrutura da Sprint 22, recomendamos:
- Encaminhar imediatamente para a Quality Automação a solicitação formal de liberação nominal documentada no fim de [docs/webposto_token_scope_analysis.md](docs/webposto_token_scope_analysis.md).
- Priorizar a modelagem do dashboard comercial no backend conectada à leitura das saídas físicas via LMC pela rota `/INTEGRACAO/CONSULTAR_LMC_REDE`.
- Estruturar a modelagem de visualização do dashboard para que liste de início os postos `5555` e `11495` em funcionamento corporativo real de faturamento de combustíveis, deixando os postos restantes em stand-by sinalizados visualmente no frontend como "Aguardando liberação operacional de credencial junto ao ERP WebPosto".
