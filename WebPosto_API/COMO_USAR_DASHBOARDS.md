# 📊 Guia de Uso — Dashboards webPosto

**3 Dashboards Disponíveis:**

---

## 1️⃣ **diagnostico.html** — Verificar Conexão API

**Para quem está com erro "Failed to fetch"**

```bash
# Abrir arquivo
open diagnostico.html
```

**O que faz:**
- ✅ Testa se API está rodando
- ✅ Verifica CORS habilitado
- ✅ Mostra status de cada endpoint
- ✅ Dá instruções de correção se houver erro

**Se mostrar erro:**
```bash
# Iniciar API
docker-compose up -d

# Aguardar 10 segundos
sleep 10

# Recarregar diagnostico.html no navegador
```

---

## 2️⃣ **admin-dashboard.html** — Gerenciar Dados (CRUD)

**Para criar, editar, deletar títulos e movimentos**

```bash
open admin-dashboard.html
```

**Funcionalidades:**
- ➕ **Criar:** Novo título/movimento com validação
- ✏️ **Editar:** Alterar dados existentes
- 🗑️ **Deletar:** Deletar com auditoria automática
- 📋 **Auditoria:** Ver quem fez o quê

**Abas:**
1. **💰 Financeiro:** Títulos a receber/pagar
2. **📦 Caixa:** Movimentos de caixa
3. **📋 Auditoria:** Log de operações

---

## 3️⃣ **vendas-dashboard.html** — Relatórios com Filtros ⭐ NOVO

**Para análise e consultas com múltiplos filtros**

```bash
open vendas-dashboard.html
```

### 🎯 Filtros Disponíveis

| Filtro | O que faz |
|--------|-----------|
| **Data Início** | Mostrar registros a partir de uma data |
| **Data Fim** | Mostrar registros até uma data |
| **Cliente/Fornecedor** | Filtrar por nome (busca parcial) |
| **Categoria** | Filtrar por Vendas, Compras, Serviços |
| **Status** | Filtrar por Pago, Pendente, Vencido |
| **Valor Mínimo** | Mostrar apenas valores ≥ ao mínimo |
| **Valor Máximo** | Mostrar apenas valores ≤ ao máximo |
| **Tipo** | Filtrar por A Receber ou A Pagar |

### 📊 Visualizações

**4 Gráficos Automáticos:**
1. 📈 **Vendas por Dia** (Linha) — Tendência ao longo do tempo
2. 👥 **Top 5 Clientes** (Barra Horizontal) — Maiores valores por cliente
3. 📊 **Distribuição de Status** (Rosca) — Pago vs Pendente vs Vencido
4. 💰 **RECEBER vs PAGAR** (Barra) — Comparativo de tipos

**4 KPI Cards:**
- 💵 **Total de Vendas** — Soma de todos valores
- 📌 **Tickets** — Quantidade de registros
- 🎯 **Ticket Médio** — Valor médio por registro
- ⚠️ **Pendente** — Valor total vencido

**Tabela Detalhada:**
- Todos os registros filtrados
- Colunas: Data, Descrição, Cliente, Categoria, Tipo, Valor, Status, Vencimento

### 🚀 Como Usar

**Exemplo 1: Vendas do Mês de Abril**
```
1. Abrir vendas-dashboard.html
2. Data Início: 01/04/2026
3. Data Fim: 30/04/2026
4. Click "🔍 Aplicar Filtros"
5. Ver gráficos atualizados + tabela
```

**Exemplo 2: Top Clientes com Débito**
```
1. Status: "Pendente"
2. Tipo: "A Receber"
3. Click "🔍 Aplicar Filtros"
4. Ver clientes com maior pendência
5. Click "📥 Exportar CSV" para salvar
```

**Exemplo 3: Vendas Acima de R$ 5.000**
```
1. Valor Mínimo: 5000
2. Tipo: "A Receber"
3. Click "🔍 Aplicar Filtros"
4. Ver apenas grandes vendas
```

**Exemplo 4: Análise por Período e Categoria**
```
1. Data Início: 01/04/2026
2. Data Fim: 14/04/2026
3. Categoria: "Vendas"
4. Click "🔍 Aplicar Filtros"
5. Gráficos mostram apenas vendas desse período
```

### 📥 Exportar Relatório

```bash
# Click no botão "📥 Exportar CSV"
# Baixa arquivo: relatorio-vendas-2026-04-14.csv

# Abrir no Excel/Sheets para análises adicionais
```

---

## 🔄 Fluxo Completo de Trabalho

```
1. DIAGNOSTICO
   └─ Abrir diagnostico.html
   └─ Verificar se API está OK
   └─ Se erro: Iniciar docker-compose

2. GERENCIAR DADOS
   └─ Abrir admin-dashboard.html
   └─ Criar/editar/deletar títulos
   └─ Ver auditoria de operações

3. ANALISAR VENDAS
   └─ Abrir vendas-dashboard.html
   └─ Aplicar filtros
   └─ Ver gráficos
   └─ Exportar relatório
```

---

## 💡 Dicas & Atalhos

### Filtros Úteis Pré-configurados

**Vendas Vencidas:**
- Status: Vencido
- Tipo: A Receber
- Click Aplicar

**Contas a Pagar:**
- Status: Pendente
- Tipo: A Pagar
- Click Aplicar

**Maiores Clientes (Últimos 30 dias):**
- Data Início: 30 dias atrás (automático)
- Data Fim: Hoje (automático)
- Ordenar por Valor Máximo
- Click Aplicar

**Análise de Fluxo de Caixa:**
- Abrir tanto RECEBER quanto PAGAR
- Comparar no gráfico "RECEBER vs PAGAR"
- Exportar ambos relatórios

### Atalhos de Teclado

- `Ctrl+F` — Buscar na página
- `Ctrl+P` — Imprimir relatório
- `Ctrl+S` — Salvar página (screenshot)

---

## 🆘 Troubleshooting

### Erro: "Failed to fetch"

**Solução:**
1. Abrir `diagnostico.html` primeiro
2. Verificar qual teste falhou
3. Se API: `docker-compose up -d`
4. Aguardar 10 segundos
5. Recarregar a dashboard

### Filtros não funcionam

**Verificar:**
- Todos os campos foram preenchidos?
- Datas estão no formato correto? (DD/MM/YYYY)
- Valor está em números? (sem R$, sem vírgulas)
- Click no botão "🔍 Aplicar Filtros"?

### Gráficos em branco

**Verificar:**
- Há dados carregados? (Ver tabela abaixo)
- Os filtros retornaram registros?
- Recarregar página (F5)

### Exportar não funciona

**Solução:**
1. Aplicar filtros primeiro
2. Click em "📥 Exportar CSV"
3. Arquivo deve baixar automaticamente
4. Se não baixar: verificar se pop-ups estão bloqueados

---

## 📋 Checklist — Antes de Apresentar

- [ ] API está rodando (`docker-compose up -d`)
- [ ] Diagnóstico OK (`diagnostico.html`)
- [ ] Dados carregam (`admin-dashboard.html`)
- [ ] Relatórios funcionam (`vendas-dashboard.html`)
- [ ] Filtros retornam resultados
- [ ] Gráficos renderizam corretamente
- [ ] Exportação de CSV funciona

---

## 🎯 Casos de Uso Real

### Caso 1: Análise de Fluxo de Caixa

**Presidente quer saber:** "Quanto temos a receber vs a pagar?"

```
1. Abrir vendas-dashboard.html
2. Tipo: A Receber
3. Status: Pendente
4. Ver Total em KPI card
5. Repetir com Tipo: A Pagar
6. Comparar gráfico "RECEBER vs PAGAR"
```

### Caso 2: Cobrança de Vencidos

**Supervisor quer:** "Quem deve para gente há mais de 30 dias?"

```
1. Abrir vendas-dashboard.html
2. Status: Vencido
3. Tipo: A Receber
4. Click "📥 Exportar CSV"
5. Passar lista para equipe de cobrança
```

### Caso 3: Performance de Vendas

**Gerente quer:** "Como está a venda este mês?"

```
1. Abrir vendas-dashboard.html
2. Data Início: 01/04/2026
3. Data Fim: 30/04/2026
4. Ver gráfico "Vendas por Dia"
5. Ver KPI "Total de Vendas"
6. Analisar "Top 5 Clientes"
```

### Caso 4: Auditoria de Operações

**Diretor quer:** "Quem criou este título? Quando?"

```
1. Abrir admin-dashboard.html
2. Click na aba "📋 Auditoria"
3. Filtrar por Record ID ou Operação
4. Ver quem criou, quando, de onde
```

---

## 🎁 Recursos Extras

### Integração com Sistemas

Se você usa ERP ou outro sistema:

```python
# Python
import requests
import json

# Buscar dados
response = requests.get('http://localhost:5000/api/v1/financeiro')
dados = response.json()['dados']

# Processar/exportar
for item in dados:
    print(f"{item['cliente_fornecedor']}: R$ {item['valor']}")
```

### API REST Endpoints

Todas as dashboards usam estes endpoints:

- `GET /api/v1/financeiro` — Listar títulos
- `GET /api/v1/caixa` — Listar movimentos
- `GET /api/v1/auditoria` — Listar log
- `POST /api/v1/financeiro` — Criar título
- `PUT /api/v1/financeiro/{id}` — Editar título
- `DELETE /api/v1/financeiro/{id}` — Deletar título

Ver `API_CRUD_COMPLETA.md` para detalhes completos.

---

**Tudo pronto! Abra as dashboards e comece a analisar! 📊**
