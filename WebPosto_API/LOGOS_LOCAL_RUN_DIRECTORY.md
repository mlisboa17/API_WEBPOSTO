# LOGOS LOCAL RUN DIRECTORY

**Data:** 2026-06-27  
**Versão:** 1.0  

---

## 📂 ESTRUTURA DO PROJETO

```
WebPosto_API/
│
├── dashboard-v2/           ❌ PROJETO EXPERIMENTAL (NÃO USAR)
│   ├── src/
│   │   ├── App.tsx        ← Template Vite padrão
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── frontend/               ✅ LOGOS REAL (PRODUÇÃO)
│   ├── index.html         ← Entrypoint do LOGOS
│   ├── app.js             ← Aplicação principal
│   ├── pages/             ← 40+ páginas do dashboard
│   ├── components/        ← Componentes reutilizáveis
│   ├── services/          ← API clients e utils
│   └── styles.css
│
├── src/                    ✅ BACKEND PYTHON (PRODUÇÃO)
│   ├── main.py            ← Entrypoint do servidor FastAPI
│   ├── interfaces/
│   │   └── http/
│   │       ├── app.py     ← Configuração FastAPI
│   │       └── routes/    ← 50+ rotas de API
│   ├── services/          ← Lógica de negócio
│   ├── domain/            ← Modelos de domínio
│   └── infrastructure/    ← Database, config
│
└── .venv/                  ← Ambiente virtual Python
```

---

## 🚀 COMANDOS DE EXECUÇÃO

### ✅ CORRETO - Rodar o LOGOS Real:

```powershell
# 1. Navegar até a raiz do projeto
cd "c:\Users\mlisb\OneDrive\ProjetosAntigravy\LOGOS SPACE\Api_WebPosto\WebPosto_API"

# 2. Ativar ambiente virtual
.\.venv\Scripts\Activate.ps1

# 3. Iniciar servidor FastAPI
python -m uvicorn src.main:app --host 127.0.0.1 --port 8040 --reload

# 4. Acessar no navegador
# http://127.0.0.1:8040/app/financial
```

### ❌ INCORRETO - NÃO fazer isso:

```powershell
# NÃO rodar Vite no dashboard-v2
cd dashboard-v2
npm run dev  # ← Isso abre o template Vite, não o LOGOS!
```

---

## 🌐 URLs DO PROJETO

| Serviço | URL | Status |
|---------|-----|--------|
| **LOGOS Dashboard** | `http://127.0.0.1:8040/app/financial` | ✅ Produção |
| API Health Check | `http://127.0.0.1:8040/health` | ✅ Produção |
| API Docs (Swagger) | `http://127.0.0.1:8040/docs` | ✅ Produção |
| Template Vite | `http://localhost:5173` | ❌ Experimental |

---

## 🔍 COMO IDENTIFICAR SE ESTÁ RODANDO O PROJETO CORRETO

### ✅ Se estiver no LOGOS correto, você verá:

- Título: **"LOGOS SPACE"**
- Subtítulo: "Cockpit corporativo — finanças, combustíveis, produtos vendidos e fiscal"
- Sidebar com áreas de negócio
- Filtros de data e tenant
- KPIs executivos
- Gráficos interativos
- Tabelas de dados

### ❌ Se estiver no projeto errado, você verá:

- Logos Vite + React
- Texto: "Get started"
- Texto: "Edit src/App.tsx and save to test HMR"
- Botão: "Count is 0"
- Links: "Documentation", "Explore Vite", "Connect with us"

---

## 📦 DEPENDÊNCIAS

### Backend (Python):
- FastAPI
- Uvicorn
- SQLAlchemy
- Pydantic
- httpx
- (ver requirements.txt)

### Frontend (Vanilla JS):
- Nenhuma dependência npm
- Servido diretamente pelo FastAPI
- JavaScript ES6+ modules
- CSS custom

### Experimental (dashboard-v2):
- React 19
- Vite 8
- Tailwind CSS 3
- Supabase JS
- (ver dashboard-v2/package.json)

---

## ⚙️ CONFIGURAÇÃO DO AMBIENTE

### Variáveis de Ambiente (.env):

```env
# Backend Python
DATABASE_URL=...
WEBPOSTO_API_KEY=...
SUPABASE_URL=...
SUPABASE_KEY=...
API_PORT=8040

# Frontend (se usar dashboard-v2 no futuro)
VITE_SUPABASE_URL=...
VITE_SUPABASE_ANON_KEY=...
```

---

## 📝 SCRIPTS DISPONÍVEIS

### Na raiz do projeto:

| Script | Comando | Descrição |
|--------|---------|-----------|
| Servidor Dev | `python -m uvicorn src.main:app --reload --port 8040` | Inicia LOGOS |
| Testes E2E | `npm test:e2e` | Playwright tests |
| Contract Check | `npm run contract-check` | Valida contratos |

### No dashboard-v2 (experimental):

| Script | Comando | Descrição |
|--------|---------|-----------|
| Dev | `npm run dev` | Vite dev server (porta 5173) |
| Build | `npm run build` | Build produção |
| Lint | `npm run lint` | ESLint |

---

## 🎯 DECISÃO ARQUITETURAL

**O LOGOS oficial é:**
- ✅ Vanilla JavaScript (`frontend/`)
- ✅ Servido pelo FastAPI
- ✅ Porta 8040
- ✅ Sem build step
- ✅ Deploy direto

**O dashboard-v2 é:**
- ❌ Projeto experimental
- ❌ Não contém código do LOGOS
- ❌ Pode ser desenvolvido no futuro
- ❌ Atualmente apenas template Vite

---

## 📚 DOCUMENTAÇÃO RELACIONADA

- `ARCHITECTURE_BASELINE_2.0.md` - Arquitetura oficial
- `DASHBOARD_CATALOG.md` - Catálogo de dashboards
- `API_CATALOG.md` - Catálogo de APIs
- `README.md` - Instruções gerais

---

**Última atualização:** 2026-06-27  
**Autor:** Sistema de Documentação LOGOS
