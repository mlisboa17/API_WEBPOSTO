# 🎨 Dashboard de Apresentação — Guia Rápido

**Status:** ✅ Pronto para Usar  
**Arquivo:** `admin-dashboard.html`  
**Compatibilidade:** Chrome, Firefox, Safari, Edge

---

## ⚡ 3 Passos para Apresentar o Sistema

### **1️⃣ Iniciar a API (Terminal 1)**

```bash
cd /opt/webposto-api

# Se Docker está instalado:
docker-compose up -d

# Ou, se rodando localmente:
python -m uvicorn src.main_minimal:app --host 0.0.0.0 --port 5000 --reload
```

**Aguarde 10 segundos** até a API estar pronta.

**Testar:**
```bash
curl http://localhost:5000/health
```

Deve retornar status `healthy`.

---

### **2️⃣ Abrir o Dashboard (Navegador)**

Abra o arquivo em seu navegador:

```bash
# Mac
open admin-dashboard.html

# Windows
start admin-dashboard.html

# Linux
firefox admin-dashboard.html
```

Ou clique duas vezes no arquivo `admin-dashboard.html`.

---

### **3️⃣ Testar o Sistema (Interativo)**

A dashboard já vem com dados carregados. Você pode:

✅ **Criar novo título:**
- Click no botão **"➕ Novo Título"**
- Preencha os dados (tipo, valor, vencimento, cliente)
- Click em **"💾 Salvar"**
- Veja o novo título aparecer na tela em tempo real

✅ **Editar um título:**
- Clique no botão **"✏️ Editar"** em qualquer card
- Altere os dados
- Salve

✅ **Deletar um título:**
- Clique no botão **"🗑️ Deletar"**
- Confirme a deleção
- O título desaparece da tela

✅ **Criar movimento de caixa:**
- Click na aba **"📦 Caixa"**
- Click em **"➕ Novo Movimento"**
- Preencha dados
- Salve

✅ **Ver auditoria:**
- Click na aba **"📋 Auditoria"**
- Veja o log completo de quem fez o quê
- Use filtros para buscar operações específicas

---

## 🎯 Recursos da Dashboard

### Dashboard Visual
```
┌─────────────────────────────────────────────┐
│  💰 webPosto Admin                          │
│  Conectado com API Real                     │
├─────────────────────────────────────────────┤
│                                             │
│  Status Cards (Atualizados em tempo real)   │
│  ├─ 💵 Total a Receber: R$ 13.200,00       │
│  ├─ 💳 Total a Pagar: R$ 9.950,00          │
│  ├─ 📦 Saldo em Caixa: R$ 12.300,00        │
│  └─ 📋 Operações Auditadas: 42             │
│                                             │
├─ Abas ─────────────────────────────────────┤
│  [💰 Financeiro] [📦 Caixa] [📋 Auditoria] │
│                                             │
│  Financeiro (Cards Grid)                    │
│  ┌──────────────────┐  ┌──────────────────┐ │
│  │ Título 1         │  │ Título 2         │ │
│  │ R$ 1.500,00      │  │ R$ 2.000,00      │ │
│  │ [✏️ Edit] [🗑 Del]│  │ [✏️ Edit] [🗑 Del]│ │
│  └──────────────────┘  └──────────────────┘ │
│                                             │
└─────────────────────────────────────────────┘
```

### Funcionalidades

| Recurso | Descrição |
|---------|-----------|
| **Cards Responsivos** | Design moderno com gradientes |
| **Tempo Real** | Auto-refresh a cada 30 segundos |
| **Validação** | Campos obrigatórios, tipos seguros |
| **Paginação** | Até 100 registros por vez |
| **Filtros** | Por tipo, status, tabela, operação |
| **Auditoria** | Log completo de todas operações |
| **Alertas** | Feedback visual de sucesso/erro |
| **Responsivo** | Funciona em mobile, tablet, desktop |

---

## 🎨 O Que Você Vai Ver

### Aba: Financeiro
- **Cards visuais** com cada título
- Mostra: Tipo (RECEBER/PAGAR), Valor, Vencimento, Status, Dias
- Botões: Editar, Deletar
- **Status Cards** mostrando Total a Receber e Total a Pagar

### Aba: Caixa
- **Cards visuais** com cada movimento
- Mostra: Tipo (VENDA/SAQUE), Valor, Saldo, Operador
- Botões: Editar, Deletar
- **Status Card** mostrando Saldo Total em Caixa

### Aba: Auditoria
- **Tabela completa** com log de operações
- Mostra: Data/Hora, Operação (CREATE/UPDATE/DELETE), Tabela, ID, Usuário, Motivo
- **Filtros**: Por tabela e operação
- Cores: Verde (CREATE), Azul (UPDATE), Vermelho (DELETE)

---

## 💡 Exemplos de Apresentação

### Exemplo 1: Criar e Deletar um Título

```
1. Click "➕ Novo Título"
2. Preencha:
   - Tipo: "A Receber"
   - Valor: "1500.00"
   - Vencimento: "2026-05-14"
   - Descrição: "Venda de produtos"
   - Cliente: "Cliente ABC Ltda"
3. Click "💾 Salvar"
4. ✅ Novo card aparece na tela
5. Click "🗑️ Deletar"
6. ✅ Card desaparece (com auditoria registrada)
```

### Exemplo 2: Atualizar um Título para "Pago"

```
1. Click "✏️ Editar" em qualquer título
2. Mude:
   - Status: "Pago"
3. Click "💾 Salvar"
4. ✅ Card atualizado em tempo real
5. Abra "📋 Auditoria"
6. ✅ Veja a operação registrada
```

### Exemplo 3: Criar Movimento de Caixa

```
1. Click na aba "📦 Caixa"
2. Click "➕ Novo Movimento"
3. Preencha:
   - Caixa #: "1"
   - Tipo: "VENDA"
   - Valor: "250.50"
   - Descrição: "Venda combustível"
   - Operador: "João"
4. Click "💾 Salvar"
5. ✅ Movimento aparece como card
6. Status Card mostra Saldo Total atualizado
```

---

## 🔄 Fluxo de Dados (Tempo Real)

```
Ação no Dashboard
       ↓
[Validação Pydantic]
       ↓
[Request HTTP → API REST]
       ↓
[CRUD + Auditoria]
       ↓
[Registro Salvo]
       ↓
[Response JSON]
       ↓
[Dashboard Atualiza]
       ↓
Alert de Sucesso
```

Tudo em **< 1 segundo**!

---

## 🎯 Pontos Fortes para Apresentar

✅ **Interface Moderna**
- Design profissional com gradientes
- Cards responsivos e interativos
- Feedback visual instantâneo

✅ **Dados Reais**
- Conecta direto com webPosto API
- Sem mock data — tudo é real
- Auditoria de todas operações

✅ **CRUD Completo**
- Create, Read, Update, Delete
- Validação em tempo real
- Integração perfeita

✅ **Rastreabilidade**
- Log de auditoria mostra quem fez o quê
- IP, usuário, timestamp, motivo
- Valores antes/depois

✅ **Performance**
- Carregamento rápido (< 1s)
- Auto-refresh a cada 30s
- Sem lentidão

---

## 🆘 Troubleshooting

### Problema: "API não conecta"
**Solução:**
```bash
# Verificar se API está rodando
curl http://localhost:5000/health

# Se falhar, iniciar:
docker-compose up -d

# Aguardar 10 segundos
sleep 10
```

### Problema: "Dashboard não carrega dados"
**Solução:**
1. Abrir Console do navegador (F12)
2. Procurar por erros vermelhos
3. Verificar se CORS está ativado na API

### Problema: "Botão de criar não funciona"
**Solução:**
1. Preencher TODOS os campos obrigatórios (com *)
2. Valores negativos rejeitados automaticamente
3. Nomes devem ter 3+ caracteres

---

## 📱 Compatibilidade

| Navegador | Status |
|-----------|--------|
| Chrome | ✅ Perfeito |
| Firefox | ✅ Perfeito |
| Safari | ✅ Funciona |
| Edge | ✅ Funciona |
| Mobile (iOS/Android) | ✅ Responsivo |

---

## 🚀 Próximos Passos Após Apresentação

1. **Deploy em Produção:**
   - Copiar `admin-dashboard.html` para servidor web
   - Abrir em https://seu-dominio.com/admin

2. **Integrar com Sistema:**
   - Usar API REST endpoints
   - Python/JavaScript SDK
   - Webhooks para eventos

3. **Customização:**
   - Cores da empresa
   - Logo customizado
   - Campos adicionais

---

## 📞 Dúvidas?

Todos os dados são **reais** e vêm direto do webPosto API!

A auditoria registra **tudo** — quem fez, quando fez, de onde fez e por quê.

---

**Pronto para apresentar! 🎉**

Abra `admin-dashboard.html` no navegador e comece a testar!
