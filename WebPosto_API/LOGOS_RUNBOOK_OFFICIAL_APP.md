# LOGOS RUNBOOK OFICIAL APP

**Data:** 2026-06-27  
**Versão:** 1.0  
**Sistema:** LOGOS SPACE

---

## 🎯 SISTEMA OFICIAL

**Nome:** LOGOS SPACE  
**Frontend:** `frontend/` (Vanilla JavaScript)  
**Backend:** `src/main.py` (FastAPI)  
**Porta:** 8040  
**URL:** `http://127.0.0.1:8040/app/financial`

---

## 🚀 QUICK START

### Comando Rápido:

```powershell
cd "c:\Users\mlisb\OneDrive\ProjetosAntigravy\LOGOS SPACE\Api_WebPosto\WebPosto_API"
.\.venv\Scripts\Activate.ps1
python -m uvicorn src.main:app --host 127.0.0.1 --port 8040 --reload
```

**Depois acesse:** `http://127.0.0.1:8040/app/financial`

---

## 📋 PRÉ-REQUISITOS

### Software Necessário:

- ✅ Python 3.9+
- ✅ pip
- ✅ Ambiente virtual Python configurado (`.venv/`)
- ✅ PostgreSQL (para database)
- ✅ Acesso à API WebPosto (credenciais)
- ✅ Acesso ao Supabase (credenciais)

### Verificar Instalação:

```powershell
# Python
python --version  # Deve ser 3.9+

# pip
pip --version

# Ambiente virtual
Test-Path .\.venv  # Deve retornar True
```

---

## 🔧 CONFIGURAÇÃO INICIAL

### 1. Clonar Repositório

```powershell
git clone <url-do-repositorio>
cd WebPosto_API
```

### 2. Criar Ambiente Virtual (se não existir)

```powershell
python -m venv .venv
```

### 3. Ativar Ambiente Virtual

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Windows CMD
.venv\Scripts\activate.bat

# Linux/Mac
source .venv/bin/activate
```

### 4. Instalar Dependências

```powershell
pip install -r requirements.txt
```

### 5. Configurar Variáveis de Ambiente

Criar arquivo `.env` na raiz:

```env
# Backend Configuration
DATABASE_URL=postgresql://user:pass@localhost:5432/logos_db
WEBPOSTO_API_KEY=sua_chave_aqui
WEBPOSTO_API_URL=https://api.webposto.com.br
API_PORT=8040

# Supabase
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua_chave_anon_aqui
SUPABASE_SERVICE_ROLE_KEY=sua_chave_service_role_aqui

# Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Tenant Default (para desenvolvimento)
DEFAULT_TENANT_ID=11495
```

---

## 🏃 EXECUTANDO O SISTEMA

### Modo 1: Desenvolvimento (com auto-reload)

```powershell
# Ativar venv
.\.venv\Scripts\Activate.ps1

# Iniciar servidor
python -m uvicorn src.main:app --host 127.0.0.1 --port 8040 --reload
```

**Saída esperada:**
```
INFO:     Uvicorn running on http://127.0.0.1:8040 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [67890]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

---

### Modo 2: Produção (sem reload)

```powershell
# Ativar venv
.\.venv\Scripts\Activate.ps1

# Iniciar servidor
python -m uvicorn src.main:app --host 0.0.0.0 --port 8040 --workers 4
```

---

### Modo 3: Via Script npm (se configurado)

```powershell
npm start
```

---

## 🌐 ACESSANDO O SISTEMA

### URLs Disponíveis:

| Serviço | URL | Descrição |
|---------|-----|-----------|
| **LOGOS Dashboard** | `http://127.0.0.1:8040/app/financial` | Dashboard principal |
| Health Check | `http://127.0.0.1:8040/health` | Status da API |
| API Docs (Swagger) | `http://127.0.0.1:8040/docs` | Documentação interativa |
| ReDoc | `http://127.0.0.1:8040/redoc` | Documentação alternativa |
| Metrics | `http://127.0.0.1:8040/metrics` | Métricas de monitoramento |

---

## 🔍 VALIDAÇÃO DO SISTEMA

### 1. Verificar Backend Rodando

```powershell
# Testar health check
curl http://127.0.0.1:8040/health
```

**Resposta esperada:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-06-27T15:00:00Z"
}
```

---

### 2. Verificar Frontend Carregando

Abrir navegador em: `http://127.0.0.1:8040/app/financial`

**Deve mostrar:**
- ✅ Título: "LOGOS SPACE"
- ✅ Subtítulo: "Cockpit corporativo — finanças, combustíveis, produtos vendidos e fiscal"
- ✅ Sidebar com navegação
- ✅ Filtros de data e tenant
- ✅ KPIs executivos

**NÃO deve mostrar:**
- ❌ "Get started"
- ❌ Template Vite
- ❌ "Edit src/App.tsx"
- ❌ Página em branco

---

### 3. Verificar Dados Carregando

No navegador (F12 → Console), executar:

```javascript
// Testar conexão com API
fetch('http://127.0.0.1:8040/api/executive/snapshot?dataInicial=2026-06-01&dataFinal=2026-06-27')
  .then(r => r.json())
  .then(d => console.log('Dados:', d))
```

---

## 🗂️ ESTRUTURA DE PASTAS

```
WebPosto_API/
│
├── frontend/                     ← FRONTEND OFICIAL
│   ├── index.html               ← Entrypoint HTML
│   ├── app.js                   ← Aplicação principal
│   ├── styles.css               ← Estilos globais
│   ├── pages/                   ← Páginas do dashboard
│   │   ├── executiveWorkspace.js
│   │   ├── executiveCopilot.js
│   │   ├── benchmark.js
│   │   └── (50+ páginas)
│   ├── components/              ← Componentes reutilizáveis
│   │   ├── navigationShell.js
│   │   ├── filters.js
│   │   └── (15+ componentes)
│   └── services/                ← API clients
│       ├── api.js
│       └── (10+ serviços)
│
├── src/                          ← BACKEND OFICIAL
│   ├── main.py                  ← Entrypoint FastAPI
│   ├── interfaces/
│   │   └── http/
│   │       ├── app.py           ← FastAPI app
│   │       └── routes/          ← 50+ rotas
│   ├── services/                ← Business logic
│   ├── domain/                  ← Domain models
│   └── infrastructure/          ← DB, config, etc.
│
├── .venv/                        ← Ambiente virtual Python
├── .env                          ← Variáveis de ambiente
├── requirements.txt              ← Dependências Python
└── README.md                     ← Documentação
```

---

## ⚙️ CONFIGURAÇÃO AVANÇADA

### Alterar Porta

Editar `src/infrastructure/config/settings.py`:

```python
class Settings(BaseSettings):
    api_port: int = 8040  # Alterar aqui
```

Ou via variável de ambiente:

```env
API_PORT=9000
```

---

### Habilitar Debug

```env
DEBUG=true
LOG_LEVEL=DEBUG
```

---

### Configurar Multi-Tenant

No `.env`:

```env
DEFAULT_TENANT_ID=11495
MULTI_TENANT_ENABLED=true
```

---

## 🐛 TROUBLESHOOTING

### Problema 1: Porta 8040 já em uso

**Sintoma:**
```
ERROR: [Errno 10048] Only one usage of each socket address is normally permitted
```

**Solução:**

```powershell
# Windows - Encontrar processo
netstat -ano | findstr :8040

# Matar processo
taskkill /PID <PID> /F

# Ou alterar porta no .env
API_PORT=8041
```

---

### Problema 2: Módulo não encontrado

**Sintoma:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Solução:**

```powershell
# Verificar venv ativo
Get-Command python  # Deve apontar para .venv

# Reinstalar dependências
pip install -r requirements.txt
```

---

### Problema 3: Variáveis de ambiente não carregando

**Sintoma:**
```
KeyError: 'SUPABASE_URL'
```

**Solução:**

```powershell
# Verificar arquivo .env existe
Test-Path .env  # Deve retornar True

# Verificar conteúdo
Get-Content .env

# Reiniciar servidor após alterar .env
```

---

### Problema 4: Frontend mostra template Vite

**Sintoma:**
- Vê "Get started" na tela
- Template Vite em vez do LOGOS

**Causa:**
- Rodou `npm run dev` no `dashboard-v2/` (projeto errado)

**Solução:**

```powershell
# Parar servidor Vite (CTRL+C)

# Ir para raiz do projeto
cd ..

# Rodar comando correto
python -m uvicorn src.main:app --host 127.0.0.1 --port 8040 --reload

# Acessar URL correta
# http://127.0.0.1:8040/app/financial
```

---

### Problema 5: Dados não carregam (skeleton infinito)

**Causa Possível:**
- RLS bloqueando no Supabase
- Tenant não configurado
- Views não criadas no Supabase

**Solução:**

1. **Verificar views do Supabase:**
   - Executar `dashboard-v2/scripts/create_public_views.sql`

2. **Verificar logs no console (F12):**
   - Procurar erros de API
   - Verificar se queries retornam dados

3. **Usar debug helper:**
   ```javascript
   window.__logosDebugSupabase()
   ```

---

### Problema 6: Erro de conexão com WebPosto API

**Sintoma:**
```
Connection timeout to WebPosto API
```

**Solução:**

```env
# Verificar credenciais no .env
WEBPOSTO_API_KEY=sua_chave_correta_aqui
WEBPOSTO_API_URL=https://api.webposto.com.br

# Testar conexão
curl -H "Authorization: Bearer $WEBPOSTO_API_KEY" $WEBPOSTO_API_URL/health
```

---

## 🧪 TESTES

### Testes E2E (Playwright)

```powershell
# Rodar todos os testes
npm run test:e2e

# Rodar testes específicos
npm run test:e2e:finance
```

---

### Testes Unitários (Python)

```powershell
# Ativar venv
.\.venv\Scripts\Activate.ps1

# Rodar pytest
pytest

# Com coverage
pytest --cov=src
```

---

## 📊 MONITORAMENTO

### Logs

**Localização:** `api.log` (raiz do projeto)

**Ver logs em tempo real:**

```powershell
# Windows
Get-Content api.log -Wait -Tail 50

# Linux/Mac
tail -f api.log
```

---

### Métricas

Acessar: `http://127.0.0.1:8040/metrics`

**Métricas disponíveis:**
- Request count
- Response time
- Error rate
- Active connections

---

## 🔒 SEGURANÇA

### Credenciais

**NUNCA commitar:**
- `.env` (adicionar ao `.gitignore`)
- Chaves API
- Senhas de banco

**Usar `.env.example` para template:**

```env
# .env.example (commitar este)
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
WEBPOSTO_API_KEY=your_key_here
```

---

### RLS (Row Level Security)

O sistema usa RLS do Supabase para multi-tenancy.

**Validar RLS:**

```sql
-- Ver políticas RLS
SELECT * FROM pg_policies WHERE schemaname = 'public';

-- Ver se RLS está habilitado
SELECT relname, relrowsecurity 
FROM pg_class 
WHERE relnamespace = 'public'::regnamespace;
```

---

## 📦 DEPLOY

### Deploy em Produção

[Instruções específicas de deploy aqui]

**Checklist Pré-Deploy:**

- [ ] ✅ Testes passando
- [ ] ✅ Variáveis de ambiente configuradas
- [ ] ✅ Backup do banco
- [ ] ✅ RLS validado
- [ ] ✅ SSL/HTTPS configurado
- [ ] ✅ Logs configurados
- [ ] ✅ Monitoramento ativo

---

## 🆘 SUPORTE

### Documentação

- **Arquitetura:** `ARCHITECTURE_BASELINE_2.0.md`
- **API Catalog:** `API_CATALOG.md`
- **Dashboard Catalog:** `DASHBOARD_CATALOG.md`

### Comandos Úteis

```powershell
# Reiniciar servidor
# CTRL+C para parar, depois rodar novamente

# Limpar cache Python
Get-ChildItem -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force

# Atualizar dependências
pip install --upgrade -r requirements.txt

# Ver portas em uso
netstat -ano | findstr LISTENING
```

---

## ✅ CHECKLIST DE VALIDAÇÃO

Após iniciar o sistema, verificar:

- [ ] ✅ Servidor FastAPI rodando na porta 8040
- [ ] ✅ Health check retorna 200
- [ ] ✅ URL `/app/financial` abre o LOGOS
- [ ] ✅ Sidebar aparece com navegação
- [ ] ✅ Filtros de data funcionam
- [ ] ✅ KPIs carregam (não fica em skeleton infinito)
- [ ] ✅ Console sem erros críticos
- [ ] ✅ Tenant switcher funciona
- [ ] ✅ Dados aparecem nas tabelas

---

**[RUNBOOK OFICIAL APROVADO]**

**Sistema:** LOGOS SPACE  
**Versão:** 1.0  
**Data:** 2026-06-27  
**Comando Principal:** `python -m uvicorn src.main:app --host 127.0.0.1 --port 8040 --reload`  
**URL:** `http://127.0.0.1:8040/app/financial`
