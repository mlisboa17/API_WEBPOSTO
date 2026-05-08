# 🏗️ Estrutura do Projeto & Como Rodar

**Status:** Pronto após instalar dependências

---

## 📁 Estrutura do Projeto

```
WebPosto_API/
├── src/
│   ├── main.py                    ← App original (complexo)
│   ├── main_minimal.py            ← App que usamos (simples + CRUD)
│   ├── models.py                  ← Validações Pydantic
│   ├── crud.py                    ← Lógica CRUD
│   ├── routes_crud.py             ← Endpoints API
│   ├── infrastructure/
│   │   ├── config/
│   │   │   └── settings.py        ← Configurações
│   │   └── webposto/
│   │       └── client.py          ← Cliente webPosto
│   ├── interfaces/http/
│   │   ├── app.py                 ← Factory FastAPI
│   │   └── routes/                ← Routers existentes
│   └── ...
├── .env                            ← Variáveis ambiente ✅
├── Dockerfile                      ← Imagem Docker (CORRIGIDO)
├── docker-compose.yml              ← Orquestração
├── pyproject.toml                  ← Dependências Python
├── admin-dashboard.html            ← Dashboard CRUD
├── vendas-dashboard.html           ← Dashboard com filtros
└── diagnostico.html                ← Teste de conexão
```

---

## 🔧 Passo-a-Passo: Instalar & Rodar

### **1️⃣ Instalar Dependências** (NECESSÁRIO)

```bash
cd /opt/webposto-api

# Opção A: Com pip (rápido)
pip install fastapi uvicorn pydantic sqlalchemy httpx tenacity pydantic-settings aiosqlite --break-system-packages

# Opção B: Com Poetry (recomendado)
pip install poetry --break-system-packages
poetry install
```

### **2️⃣ Rodar API Localmente (Sem Docker)**

```bash
# Terminal 1: Iniciar API
python -m uvicorn src.main_minimal:app --host 0.0.0.0 --port 5000 --reload

# Você verá:
# INFO:     Uvicorn running on http://0.0.0.0:5000
# INFO:     Application startup complete
```

### **3️⃣ Testar API**

```bash
# Terminal 2: Teste health check
curl http://localhost:5000/health

# Resposta esperada:
# {
#   "status": "healthy",
#   "version": "0.2.0",
#   "webposto_api": "http://web.qualityautomacao.com.br",
#   "empresa": "POSTO VIP - Rio Doce",
#   "cors": "enabled",
#   "timestamp": "2026-04-14T..."
# }
```

### **4️⃣ Abrir Dashboards**

```bash
# Terminal 3: Abrir navegador
open admin-dashboard.html     # Para gerenciar dados
open vendas-dashboard.html    # Para consultas com filtros
open diagnostico.html         # Para testar conexão
```

---

## 🐳 Opção: Rodar com Docker

### **1️⃣ Build da Imagem**

```bash
docker build -t webposto-api:latest .
```

### **2️⃣ Iniciar com Docker Compose**

```bash
docker-compose up -d

# Ou para ver logs:
docker-compose up
```

### **3️⃣ Verificar Status**

```bash
docker-compose ps

# Esperado:
# webposto-redis    running
# webposto-api      running
```

### **4️⃣ Testar API**

```bash
curl http://localhost:5000/health
```

---

## ✅ Checklist de Funcionamento

- [ ] Dependências instaladas (`pip list | grep fastapi`)
- [ ] API respondendo (`curl http://localhost:5000/health`)
- [ ] CORS habilitado (sem erro "Failed to fetch")
- [ ] Health check retorna "healthy"
- [ ] Documentação interativa em `/docs`
- [ ] Dashboard admin abre (`admin-dashboard.html`)
- [ ] Dashboard vendas abre (`vendas-dashboard.html`)
- [ ] Filtros funcionam (aplicar e dados atualizam)
- [ ] Criar título retorna 200 OK
- [ ] Tabela mostra dados carregados

---

## 🆘 Troubleshooting

### Erro: "ModuleNotFoundError: No module named 'fastapi'"

**Solução:**
```bash
pip install fastapi uvicorn pydantic sqlalchemy --break-system-packages
```

### Erro: "Failed to fetch" no navegador

**Verificar:**
1. API está rodando? `curl http://localhost:5000/health`
2. CORS está habilitado? (deve retornar no health check)
3. Porta correta? (5000, não 8000)

### Erro: "Connection refused"

**Verificar:**
```bash
# Se rodando localmente
python -m uvicorn src.main_minimal:app --port 5000

# Se rodando Docker
docker-compose up -d
docker logs webposto-api
```

### Erro: "sqlite3.OperationalError: no such table"

**Solução:** Banco de dados será criado automaticamente na primeira execução.

---

## 📊 Endpoints Disponíveis

### Financeiro
- `GET /api/v1/financeiro` — Listar títulos
- `POST /api/v1/financeiro` — Criar título
- `PUT /api/v1/financeiro/{id}` — Editar título
- `DELETE /api/v1/financeiro/{id}` — Deletar título

### Caixa
- `GET /api/v1/caixa` — Listar movimentos
- `POST /api/v1/caixa` — Criar movimento
- `PUT /api/v1/caixa/{id}` — Editar movimento
- `DELETE /api/v1/caixa/{id}` — Deletar movimento

### Auditoria
- `GET /api/v1/auditoria` — Ver log de operações

### Health
- `GET /health` — Status da API
- `GET /docs` — Swagger UI
- `GET /redoc` — ReDoc

---

## 🎯 Resumo Rápido

### Local (Desenvolvimento)
```bash
# 1. Instalar
pip install fastapi uvicorn pydantic sqlalchemy httpx tenacity pydantic-settings aiosqlite --break-system-packages

# 2. Rodar
python -m uvicorn src.main_minimal:app --port 5000 --reload

# 3. Testar
open admin-dashboard.html
```

### Docker (Produção)
```bash
# 1. Build
docker build -t webposto-api:latest .

# 2. Rodar
docker-compose up -d

# 3. Testar
curl http://localhost:5000/health
```

---

## 🔍 Próximos Passos

1. ✅ Instalar dependências
2. ✅ Rodar API (`python -m uvicorn src.main_minimal:app --port 5000`)
3. ✅ Abrir `diagnostico.html` no navegador
4. ✅ Se OK → Abrir `admin-dashboard.html`
5. ✅ Testar criar/editar/deletar títulos
6. ✅ Abrir `vendas-dashboard.html`
7. ✅ Testar filtros e gráficos

---

**Pronto! Após instalar dependências, tudo funciona! 🚀**
