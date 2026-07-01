# LOGOS LEGACY ARCHIVE PLAN

**Data:** 2026-06-27  
**Hotfix:** REPO-TRUTH-01  
**Objetivo:** Plano de consolidação do repositório

---

## 🎯 OBJETIVO

Limpar e organizar o repositório para eliminar confusão entre projetos oficiais, experimentais e legacy.

---

## 📋 PLANO DE AÇÃO

### Fase 1: Renomear Projetos Não-Oficiais

#### 1.1 Renomear `dashboard-v2/` para `_experimental_react_dashboard/`

**Razão:** 
- Nome "dashboard-v2" sugere "versão 2" oficial
- Na verdade é um projeto experimental não implementado
- Prefixo `_experimental_` deixa claro o status

**Comando:**
```powershell
Rename-Item -Path "dashboard-v2" -NewName "_experimental_react_dashboard"
```

**Impacto:**
- Nenhum sistema em produção afetado
- Projeto não está sendo usado
- Apenas renomeação para clareza

---

#### 1.2 Renomear `index.html` (raiz) para `demo_webposto_api.html`

**Razão:**
- `index.html` na raiz pode confundir com entrypoint do sistema
- É apenas uma página de demonstração/landing
- Novo nome deixa claro o propósito

**Comando:**
```powershell
Rename-Item -Path "index.html" -NewName "demo_webposto_api.html"
```

**Impacto:**
- Nenhum sistema em produção afetado
- Página demo não é usada em produção

---

#### 1.3 Avaliar `logos-webposto-gateway/`

**Razão:**
- Parece ser um gateway/serviço auxiliar ou deprecado
- Precisa de avaliação para confirmar status

**Ação:**
- Investigar se ainda está em uso
- Se deprecado: renomear para `_legacy_gateway/`
- Se ativo: documentar propósito

---

### Fase 2: Criar Estrutura Clara

#### 2.1 Estrutura Proposta

```
WebPosto_API/
│
├── frontend/                          ✅ OFICIAL (Produção)
│   ├── index.html
│   ├── app.js
│   ├── pages/
│   ├── components/
│   └── services/
│
├── src/                               ✅ OFICIAL (Backend)
│   ├── main.py
│   ├── interfaces/
│   ├── services/
│   └── infrastructure/
│
├── _experimental/                     📁 PASTA NOVA
│   └── react_dashboard/               ← dashboard-v2 movido
│       ├── src/
│       ├── package.json
│       └── README.md (explicar status)
│
├── _legacy/                           📁 PASTA NOVA
│   ├── gateway/                       ← logos-webposto-gateway movido (se deprecado)
│   └── demo_webposto_api.html         ← index.html movido
│
├── docs/                              📁 CONSOLIDAR DOCS
│   ├── architecture/
│   ├── api/
│   └── user-guides/
│
├── README.md                          ✅ ATUALIZAR
├── .env.example                       ✅ CRIAR
├── RUNBOOK.md                         ✅ CRIAR
└── package.json                       ✅ ATUALIZAR com script único
```

---

### Fase 3: Documentação

#### 3.1 Atualizar `README.md`

**Conteúdo Novo:**
```markdown
# LOGOS SPACE — WebPosto API Integration

## 🎯 Sistema Oficial

**Frontend:** `frontend/` (Vanilla JavaScript)  
**Backend:** `src/main.py` (FastAPI)  
**Porta:** 8040  
**URL:** http://127.0.0.1:8040/app/financial

## 🚀 Quick Start

```bash
# 1. Ativar ambiente virtual
.\.venv\Scripts\Activate.ps1

# 2. Iniciar servidor
python -m uvicorn src.main:app --host 127.0.0.1 --port 8040 --reload

# 3. Acessar
# http://127.0.0.1:8040/app/financial
```

## 📂 Estrutura

- `frontend/` - LOGOS Dashboard (produção)
- `src/` - Backend FastAPI (produção)
- `_experimental/` - Projetos experimentais (não usar)
- `_legacy/` - Código deprecado (arquivado)

## ⚠️ NÃO USAR

- `_experimental/react_dashboard/` - Projeto não implementado
- `_legacy/` - Código deprecado

## 📚 Documentação

- [Runbook Oficial](./RUNBOOK.md)
- [Arquitetura](./docs/architecture/)
- [API Catalog](./API_CATALOG.md)
```

---

#### 3.2 Criar `RUNBOOK.md`

**Conteúdo:**
```markdown
# LOGOS RUNBOOK OFICIAL

## Sistema

**Nome:** LOGOS SPACE  
**Versão:** 1.0  
**Frontend:** frontend/ (Vanilla JS)  
**Backend:** src/main.py (FastAPI)  

## Como Rodar Localmente

### Pré-requisitos

- Python 3.9+
- Ambiente virtual configurado
- Variáveis de ambiente (.env)

### Comandos

```bash
# Ativar venv
.\.venv\Scripts\Activate.ps1

# Iniciar servidor
python -m uvicorn src.main:app --host 127.0.0.1 --port 8040 --reload

# Acessar
http://127.0.0.1:8040/app/financial
```

## Variáveis de Ambiente

Criar `.env` com:

```env
DATABASE_URL=...
WEBPOSTO_API_KEY=...
SUPABASE_URL=...
SUPABASE_KEY=...
API_PORT=8040
```

## Deploy

[Instruções de deploy aqui]

## Troubleshooting

### Problema: Porta 8040 ocupada

```bash
# Windows
netstat -ano | findstr :8040
taskkill /PID <PID> /F
```

### Problema: Módulo não encontrado

```bash
pip install -r requirements.txt
```
```

---

#### 3.3 Criar `.env.example`

**Conteúdo:**
```env
# Backend Configuration
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
WEBPOSTO_API_KEY=your_api_key_here
API_PORT=8040

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Environment
ENVIRONMENT=development
DEBUG=true

# Frontend (se usar dashboard-v2 no futuro)
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
```

---

#### 3.4 Criar README em `_experimental/react_dashboard/`

**Conteúdo:**
```markdown
# Experimental React Dashboard

⚠️ **ESTE PROJETO NÃO ESTÁ IMPLEMENTADO**

## Status

Este é um projeto experimental React/Vite que foi iniciado mas nunca desenvolvido.

- ❌ Apenas template Vite padrão
- ❌ Nenhum componente do LOGOS implementado
- ❌ Não usar para desenvolvimento

## Sistema Oficial

O sistema LOGOS oficial está em:

```
../frontend/  (Vanilla JavaScript)
```

## Propósito Futuro

Este projeto pode ser retomado no futuro para migração do LOGOS para React, mas atualmente está pausado.

## Como Testar (apenas template)

```bash
npm install
npm run dev
# Abrirá template Vite padrão em http://localhost:5173
```

**Nota:** Isso NÃO é o LOGOS, apenas um template Vite vazio.
```

---

### Fase 4: Atualizar Scripts

#### 4.1 Criar script único no `package.json` raiz

**Editar `package.json` na raiz:**

```json
{
  "name": "webposto-api",
  "version": "1.0.0",
  "description": "API de Integração WebPosto e Frontend LOGOS",
  "scripts": {
    "start": "echo 'Iniciando LOGOS...' && python -m uvicorn src.main:app --host 127.0.0.1 --port 8040 --reload",
    "dev": "npm run start",
    "test:e2e": "playwright test",
    "test:e2e:finance": "playwright test e2e/finance_center"
  },
  "devDependencies": {
    "@playwright/test": "^1.51.0",
    "@types/node": "^22.13.0",
    "typescript": "^5.8.0"
  },
  "dependencies": {
    "@supabase/ssr": "^0.12.0",
    "@supabase/supabase-js": "^2.108.2"
  }
}
```

**Agora o comando será:**
```bash
npm start
# ou
npm run dev
```

---

### Fase 5: Consolidar Documentação

#### 5.1 Mover documentos para estrutura organizada

```
docs/
├── architecture/
│   ├── ARCHITECTURE_BASELINE_2.0.md
│   ├── DASHBOARD_CATALOG.md
│   └── API_CATALOG.md
│
├── reports/
│   ├── sprints/
│   │   ├── SPRINT_23_RELATORIO_FINAL.md
│   │   └── ...
│   ├── hotfixes/
│   │   ├── LOGOS_APP_ENTRYPOINT_FIX.md
│   │   ├── LOGOS_REPOSITORY_INVENTORY.md
│   │   └── ...
│   └── features/
│       ├── copilot/
│       ├── benchmark/
│       └── fiscal/
│
└── guides/
    ├── RUNBOOK.md
    ├── DEPLOYMENT.md
    └── TROUBLESHOOTING.md
```

---

## 🗑️ O QUE ARQUIVAR

### Arquivar (mover para `_legacy/`):

1. **demo_webposto_api.html** (ex-index.html)
   - Página de demonstração não usada em produção

2. **logos-webposto-gateway/** (se confirmado como deprecado)
   - Gateway antigo substituído

3. **Documentos antigos de sprints** (opcional)
   - Mover para `docs/reports/sprints/archive/`

---

### Não Arquivar (manter):

1. **frontend/** - Sistema oficial em produção
2. **src/** - Backend oficial em produção
3. **Documentação ativa** - Docs relevantes
4. **.env, .gitignore** - Configurações

---

## 📋 CHECKLIST DE EXECUÇÃO

### Pré-Renomeação:

- [ ] Backup do repositório completo
- [ ] Confirmar que nenhum CI/CD aponta para `dashboard-v2/`
- [ ] Confirmar que nenhum script usa `index.html` da raiz

### Renomeações:

- [ ] Renomear `dashboard-v2/` → `_experimental/react_dashboard/`
- [ ] Renomear `index.html` → `_legacy/demo_webposto_api.html`
- [ ] Avaliar `logos-webposto-gateway/` (se deprecado → `_legacy/gateway/`)

### Documentação:

- [ ] Atualizar `README.md` raiz
- [ ] Criar `RUNBOOK.md`
- [ ] Criar `.env.example`
- [ ] Criar README em `_experimental/react_dashboard/`
- [ ] Mover documentação para `docs/`

### Scripts:

- [ ] Atualizar `package.json` raiz com script único
- [ ] Testar `npm start` funciona
- [ ] Testar `npm run dev` funciona

### Git:

- [ ] Commit todas as mudanças
- [ ] Tag de versão: `v1.0-repository-cleanup`
- [ ] Push para repositório

---

## ✅ RESULTADO ESPERADO

Após execução do plano:

1. **Clareza:** Óbvio qual é o projeto oficial
2. **Sem Confusão:** Projetos experimentais claramente marcados
3. **Documentação:** README claro e atualizado
4. **Comando Único:** `npm start` para rodar o LOGOS
5. **Estrutura Limpa:** Legacy e experimental separados

---

## 🎯 CRITÉRIO DE SUCESSO

- [ ] ✅ Desenvolvedor novo consegue identificar projeto oficial em 30 segundos
- [ ] ✅ Comando `npm start` funciona
- [ ] ✅ README.md está atualizado e claro
- [ ] ✅ Projetos experimentais estão em `_experimental/`
- [ ] ✅ Projetos legacy estão em `_legacy/`
- [ ] ✅ Sem arquivos soltos na raiz (exceto essenciais)

---

**[PLANO DE CONSOLIDAÇÃO APROVADO]**

**Data:** 2026-06-27  
**Impacto:** Baixo (apenas organização, sem mudanças em produção)  
**Tempo Estimado:** 2-3 horas
