# 📊 MAPEAMENTO COMPLETO — ENDPOINT /INTEGRACAO/ABASTECIMENTO

## 📋 Resumo Executivo

**Endpoint:** `GET /INTEGRACAO/ABASTECIMENTO`  
**Autenticação:** Query param `CHAVE=<WEBPOSTO_API_TOKEN>`  
**Filtros:** `dataInicial` e `dataFinal` (YYYY-MM-DD)  
**Status HTTP:** 200 OK ✅  
**Estrutura:** JSON array de objetos dentro de `resultados[]`  
**Paginação:** Utiliza `ultimoCodigo` para carregamento progressivo  

---

## 📊 Estatísticas da Amostra (04/03 a 04/10/2026)

| Métrica | Valor |
|---------|-------|
| **Total de Registros** | 200 (amostra do endpoint) |
| **Quantidade Total** | 1.373,03 litros |
| **Faturamento Total** | R$ 9.515,55 |
| **Ticket Médio** | R$ 47,58 |
| **Produtos Únicos** | 2 códigos |
| **Bicos Utilizados** | 10 bombas |

---

## 🔍 ESTRUTURA DOS CAMPOS

### 📍 Campos de Identificação

| Campo | Tipo | Obrigatório | Exemplo | Descrição |
|-------|------|-------------|---------|-----------|
| `codigo` | Integer | ✅ | `360379500` | Identificador único do abastecimento |
| `abastecimentoCodigo` | Integer | ✅ | `360379500` | Mesmo que `codigo` (redundância) |
| `vendaItemCodigo` | Integer | ✅ | `730031529` | ID da venda associada |
| `empresaCodigo` | Integer | ✅ | `11495` | Código da filial (POSTO VIP) |

### 🕐 Campos de Data/Hora

| Campo | Tipo | Obrigatório | Exemplo | Descrição |
|-------|------|-------------|---------|-----------|
| `dataFiscal` | String (YYYY-MM-DD) | ✅ | `"2026-04-03"` | Data fiscal do abastecimento |
| `horaFiscal` | String (HH:MM:SS) | ✅ | `"00:10:40"` | Hora fiscal (ECF) |
| `dataHoraAbastecimento` | ISO8601 | ✅ | `"2026-04-03T00:10:05-03:00"` | Timestamp completo com timezone |

### ⛽ Campos de Combustível/Produto

| Campo | Tipo | Obrigatório | Exemplo | Descrição |
|-------|------|-------------|---------|-----------|
| `codigoProduto` | String | ✅ | `"1257884"` | Código do produto (combustível) |
| `quantidade` | Float | ✅ | `2.0` | Litros abastecidos (2 casas decimais) |
| `codigoBico` | Integer | ✅ | `42902` | ID da bomba/bico usado |

### 💰 Campos de Preço/Valor

| Campo | Tipo | Obrigatório | Exemplo | Descrição |
|-------|------|-------------|---------|-----------|
| `valorUnitario` | Float | ✅ | `7.39` | Preço por litro (tabela) |
| `valorTotal` | Float | ✅ | `14.78` | Total = quantidade × valorUnitario |
| `precoCadastro` | Float | ✅ | `7.39` | Preço de cadastro no sistema |
| `tabelaPrecoA` | Float | ✅ | `7.39` | Preço tabela A (padrão) |
| `tabelaPrecoB` | Float | ✅ | `0.0` | Preço tabela B (alternativa) |
| `tabelaPrecoC` | Float | ✅ | `0.0` | Preço tabela C (alternativa) |

### 👤 Campos de Operador

| Campo | Tipo | Obrigatório | Exemplo | Descrição |
|-------|------|-------------|---------|-----------|
| `codigoFrentista` | Integer | ✅ | `227386` | Código do funcionário/frentista |

### 📱 Campos de ECF/Equipamento

| Campo | Tipo | Obrigatório | Exemplo | Descrição |
|-------|------|-------------|---------|-----------|
| `afericao` | Boolean | ✅ | `false` | Indica aferição do equipamento |
| `encerrante` | Float | ✅ | `234654.5` | Leitura do encerrante (hodômetro) |
| `stringFull` | String | ✅ | `"949303;1;1;1;2..."` | String bruta do ECF (semicolon-delimited) |

### 🚗 Campos Adicionais

| Campo | Tipo | Obrigatório | Exemplo | Descrição |
|-------|------|-------------|---------|-----------|
| `placa` | String/Null | ❌ | `null` | Placa do veículo (quando informada) |

---

## 🎯 MAPEAMENTO DE PRODUTOS

Baseado na amostra analisada (04/03 a 04/10/2026):

| Código | Produto | Frequência | % do Total | Litros | Faturamento |
|--------|---------|-----------|-----------|--------|------------|
| `1257884` | **Gasolina Comum** | 155 | 77,5% | 1.102,71 L | R$ 8.154,11 |
| `1975728` | **Etanol** | 45 | 22,5% | 270,32 L | R$ 1.361,44 |

**Nota:** Gasolina Aditivada (`1260803`) não apareceu nesta amostra (04/03-04/10), mas existe no sistema.

---

## 🔧 BICOS/BOMBAS DISPONÍVEIS

| Código | Frequência | % de Uso | Status |
|--------|-----------|----------|--------|
| `42902` | 62 | 31,0% | Ativo |
| `42905` | 41 | 20,5% | Ativo |
| `42910` | 32 | 16,0% | Ativo |
| `42913` | 16 | 8,0% | Ativo |
| `42911` | 10 | 5,0% | Ativo |
| `42908` | 13 | 6,5% | Ativo |
| `42907` | 9 | 4,5% | Ativo |
| `42904` | 11 | 5,5% | Ativo |
| `46664` | 2 | 1,0% | (Especial) |
| `46700` | 4 | 2,0% | (Especial) |

---

## 📌 REGRAS DE NEGÓCIO IDENTIFICADAS

### 1. **Cálculo de Valor**
```
valorTotal = quantidade × valorUnitario
Exemplo: 2.0 litros × R$ 7,39 = R$ 14,78
```

### 2. **Tabela de Preços**
- `tabelaPrecoA` é o preço padrão (ativo)
- `tabelaPrecoB` e `tabelaPrecoC` são alternativas (geralmente zeradas)
- Pode haver fidelidade ou desconto aplicado (não aparece como campo separado)

### 3. **Encerrante**
- Leitura cumulativa do hodômetro da bomba
- Permite identificar divergências de estoque
- Aumenta monotonicamente

### 4. **Aferição**
- `afericao: false` = Venda normal
- `afericao: true` = Teste/aferição do equipamento (filtrar em relatórios)

### 5. **Rastreabilidade de Operador**
- Todo abastecimento tem `codigoFrentista`
- Permite auditoriar por pessoa

---

## 🔗 INTEGRAÇÃO COM OUTROS ENDPOINTS

O `abastecimentoCodigo` e `vendaItemCodigo` permitem cruzamento com:

- **VENDA** (usar `vendaItemCodigo`)
- **CLIENTE** (se venda tem cliente associado)
- **PRODUTO** (usar `codigoProduto` para detalhes)
- **FUNCIONARIO** (usar `codigoFrentista`)

---

## 📥 EXEMPLO DE PAYLOAD — GET ABASTECIMENTO

### Request
```http
GET /INTEGRACAO/ABASTECIMENTO?CHAVE=<WEBPOSTO_API_TOKEN>&dataInicial=2026-04-03&dataFinal=2026-04-10
```

### Response (HTTP 200)
```json
{
  "ultimoCodigo": 360427100,
  "resultados": [
    {
      "dataFiscal": "2026-04-03",
      "horaFiscal": "00:10:40",
      "codigoBico": 42902,
      "codigoProduto": "1257884",
      "quantidade": 2.0,
      "valorUnitario": 7.39,
      "valorTotal": 14.78,
      "codigoFrentista": 227386,
      "afericao": false,
      "vendaItemCodigo": 730031529,
      "precoCadastro": 7.39,
      "tabelaPrecoA": 7.39,
      "tabelaPrecoB": 0.0,
      "tabelaPrecoC": 0.0,
      "empresaCodigo": 11495,
      "dataHoraAbastecimento": "2026-04-03T00:10:05-03:00",
      "stringFull": "949303;1;1;1;2;1;7,39;14,78;0;03/04/2026 00:10:05;42;0;234652,5;0;1541580,88;234654,5;0;1541595,66;-1;20;-1;F93A90BB;01;0000000000000000;",
      "placa": null,
      "abastecimentoCodigo": 360379500,
      "encerrante": 234654.5,
      "codigo": 360379500
    }
    // ... mais registros
  ]
}
```

---

## 🔄 PAGINAÇÃO

O endpoint retorna **até 200 registros** por request. Para buscar mais:

1. **Primeiro request:** Use `dataInicial` e `dataFinal`
2. **Response contém:** `ultimoCodigo: 360427100`
3. **Próximo request:** Adicione `ultimoCodigo=360427100` para continuar

```http
GET /INTEGRACAO/ABASTECIMENTO?CHAVE=xxx&dataInicial=2026-04-03&dataFinal=2026-04-10&ultimoCodigo=360427100
```

---

## ⚠️ PONTOS IMPORTANTES

### 1. **Não há campo de "Total Vendido por Tipo"**
   - Precisa ser **agregado no dashboard** (não vem do endpoint)
   - Somar `quantidade` e `valorTotal` agrupando por `codigoProduto`

### 2. **Placa pode ser NULL**
   - Nem todos os abastecimentos têm veículo identificado
   - Filtrar com cuidado em relatórios

### 3. **StringFull é redundante**
   - Já tem todos os dados em campos estruturados
   - Manter para auditoria/rastreabilidade do ECF

### 4. **Encerrante vem do ECF**
   - Usar para cálculos de divergência
   - Comparar com relatório de abastecimento do equipamento

### 5. **Dados em Tempo Real**
   - Atualizam conforme abastecimentos ocorrem
   - Considerar cache para dashboards (não fazer refresh a cada segundo)

---

## 📊 DADOS VALIDADOS ✅

| Aspecto | Status | Evidência |
|--------|--------|-----------|
| **Conectividade** | ✅ HTTP 200 | Endpoint responde normalmente |
| **Autenticação** | ✅ Válida | Chave API com acesso total |
| **Dados Reais** | ✅ Produção | 200 registros da Filial POSTO VIP |
| **Data Range** | ✅ Flexível | Filtra por período conforme solicitado |
| **Integridade** | ✅ Consistente | Valores fazem sentido (quantidade × valor = total) |

---

## 🎯 RECOMENDAÇÕES PARA DASHBOARD

### Filtros Essenciais
- ✅ Data inicial/final
- ✅ Tipo de combustível (`codigoProduto`)
- ✅ Operador (`codigoFrentista`)
- ✅ Bico/bomba (`codigoBico`)
- ✅ Faixa de valor

### Estatísticas Críticas
- ✅ Total vendido por combustível (quantidade e valor)
- ✅ Ticket médio
- ✅ Operador com maior faturamento
- ✅ Bico com maior movimento
- ✅ Divergências de encerrante

### Gráficos Recomendados
- 📊 Barras: Vendas por tipo (Gasolina vs Etanol)
- 📊 Pizza: Distribuição de combustíveis
- 📈 Linha: Evolução de vendas por dia
- 📊 Barras: Comparação por operador
- 📊 Barras: Movimento por bico

---

## ✅ PRÓXIMO PASSO

Com este mapeamento validado, você pode:

1. **Criar DASHBOARD ABASTECIMENTO** com:
   - Filtros (data, produto, operador, bico)
   - Cards de estatísticas (total, ticket, maior venda)
   - Gráficos (tipo combustível, evolução, operador)
   - Tabela detalhada com exportação CSV

2. **Implementar validações**:
   - Excluir `afericao: true` dos relatórios
   - Somar corretamente quantidade e valor
   - Manter histórico de encerrante para auditoria

3. **Preparar backend** para:
   - Cache de dados (Redis)
   - Alertas de divergência
   - Relatórios agendados
   - Webhooks para mudanças

---

**Mapeamento finalizado:** 10/04/2026  
**Status:** ✅ **VALIDADO E TESTADO**  
**Próximo:** Criar dashboard_abastecimento.html

