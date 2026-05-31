# 🚀 Logos WebPosto Gateway - Visual Structure Map

## Project Tree (Completo)

```
logos-webposto-gateway/
│
├── 📄 src/
│   ├── __init__.py
│   ├── main.py                              ✅ GEMINI - FastAPI porta 8050
│   │
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── entities.py                      🔄 CLAUDE - CashExpense, PostoCredentials
│   │   └── exceptions.py                    🔄 CLAUDE - Exceções de domínio
│   │
│   ├── application/
│   │   ├── __init__.py
│   │   └── fetch_expenses.py                🔄 CLAUDE - UseCase orquestrador
│   │
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── database.py                      ✅ GEMINI - SQLite assíncrono
│   │   ├── repository.py                    🔄 CLAUDE - Repositório de credenciais
│   │   ├── webposto_client.py               🔄 GROK - Cliente HTTPX
│   │   └── cache.py                         🔄 GROK - Cache com TTL
│   │
│   └── presentation/
│       ├── __init__.py
│       └── routes.py                        ✅ GEMINI - Endpoints /ready, /health
│
├── 📄 tests/
│   ├── __init__.py
│   ├── test_domain.py                       ✅ Testes de entidades
│   └── test_presentation.py                 ✅ Testes de endpoints
│
├── 📄 docker-compose.yml                    ✅ GEMINI - Orquestração
├── 📄 Dockerfile                            ✅ GEMINI - Multi-stage build
├── 📄 .env.example                          ✅ Variáveis de ambiente
├── 📄 .gitignore                            ✅ Git patterns
├── 📄 requirements.txt                      ✅ Dependências Python
├── 📄 pyproject.toml                        ✅ Metadados & ferramentas
├── 📄 README.md                             ✅ Documentação completa
├── 📄 Makefile                              ✅ Commands úteis
│
├── 📄 TASK_ALLOCATION.py                    ✅ Alocação de tarefas
├── 📄 PROMPTS.py                            ✅ Prompts para cada IA
├── 📄 STRUCTURE_SUMMARY.py                  ✅ Este sumário
├── 📄 VISUAL_MAP.md                         📖 Mapa visual (você está aqui)
│
├── 📄 setup.sh                              ✅ Quick setup (Linux/Mac)
└── 📄 setup.bat                             ✅ Quick setup (Windows)
```

---

## 🎨 Fluxo de Dados (Completo)

```
┌─────────────────────────────────────────────────────────────┐
│         CLIENTE (Módulo Logos - Header: X-Posto-ID)         │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
        ┌────────────────────┐
        │   FastAPI Router   │ (src/presentation/routes.py)
        │   Porta 8050 ✅    │
        └────────────┬───────┘
                     │
        ┌────────────▼──────────────┐
        │   /ready (HTTP 200)       │
        │   /health (SELECT 1)      │
        │   /v1/expenses (Handler)  │
        └────────────┬──────────────┘
                     │
                     ▼ (UseCase Injection)
        ┌─────────────────────────────────┐
        │   FetchExpensesUseCase 🔄       │
        │   (application/fetch_expenses)  │
        └────────────┬────────────────────┘
                     │
        ┌────────────▼──────────────────┐
        │   Repositório 🔄              │ ──┐
        │   (infrastructure/repository) │  │
        │   Busca credenciais no DB     │  │
        └────────────┬──────────────────┘  │
                     │                      │
        ┌────────────▼────────────────────┐ │
        │    Cache Hit? 🔄                │ │
        │   (infrastructure/cache.py)    │ │
        │   TTL 5 minutos               │ │
        └────────────┬────────────────────┘ │
                     │                      │
           ┌─────────┴─────────┐            │
           │                   │            │
      HIT  │               MISS│            │
           ▼                   ▼            │
       CACHE                   │            │
      RETURN                   │            │
                       ┌───────▼──────────┐ │
                       │   WebPostoClient │ │
                       │   (infrastructure/│ │
                       │   webposto_client)│ │
                       │   HTTPX + 10s TO │ │
                       └───────┬──────────┘ │
                               │            │
                               ▼            │
                       ┌──────────────────┐ │
                       │  WebPosto API    │ │
                       │ (Externa)        │ │
                       └──────┬───────────┘ │
                              │             │
                              ▼             │
                       ┌──────────────────┐ │
                       │  Parser JSON     │ │
                       │  → CashExpense   │ │
                       └──────┬───────────┘ │
                              │             │
                              ▼             │
                       ┌──────────────────┐ │
                       │  Cache.set()     │◄┘
                       │  (armazena)      │
                       └──────┬───────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │  HTTP 200        │
                       │  + JSON Response │
                       └──────┬───────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │  Cliente Logos   │
                       │  (Dados pronto)  │
                       └──────────────────┘
```

---

## 🔄 Padrão DDD (4 Camadas)

```
┌───────────────────────────────────────────────┐
│  PRESENTATION LAYER (HTTP)                    │ ← FastAPI Routes
├───────────────────────────────────────────────┤
│  APPLICATION LAYER (Use Cases)                │ ← FetchExpensesUseCase
├───────────────────────────────────────────────┤
│  DOMAIN LAYER (Business Rules)                │ ← Entidades + Exceções
├───────────────────────────────────────────────┤
│  INFRASTRUCTURE LAYER (Technical Details)     │ ← Database, HTTP, Cache
└───────────────────────────────────────────────┘
```

**Benefícios**:
- ✅ Isolamento total entre camadas
- ✅ Testes unitários sem mock complexo
- ✅ Fácil manutenção e evolução
- ✅ Código limpo e legível

---

## 🎯 Distribuição de Tarefas (Paralelo)

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  GEMINI 2.0 │    │ CLAUDE 3.7  │    │  GROK 4     │
├─────────────┤    ├─────────────┤    ├─────────────┤
│ ✅ Pronto   │    │ 🔄 Ready    │    │ 🔄 Ready    │
├─────────────┤    ├─────────────┤    ├─────────────┤
│ main.py     │    │ entities.py │    │ cache.py    │
│ database.py │    │ exceptions. │    │ webposto_   │
│ routes.py   │    │ py          │    │ client.py   │
│ docker-     │    │ fetch_      │    │ tests/      │
│ compose.yml │    │ expenses.py │    │             │
│ Dockerfile  │    │ repository. │    │ 🎯 80%+     │
│             │    │ py          │    │ coverage    │
└─────────────┘    └─────────────┘    └─────────────┘
      ║                  ║                   ║
      ╚══════════════════╩═══════════════════╝
       Integração E2E → Validação Completa
```

---

## ✅ Checklist de Validação (Em Ordem)

### FASE 1: Setup (Todos)
```bash
# Windows
setup.bat

# Linux/Mac
bash setup.sh

# Ou manual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### FASE 2: Docker Start (GEMINI)
```bash
docker compose up -d
sleep 2
curl http://localhost:8050/ready   # Deve retornar 200
curl http://localhost:8050/health  # Deve retornar 200
```

### FASE 3: Código (CLAUDE + GROK)
```bash
# CLAUDE implementa entities.py, exceptions.py, fetch_expenses.py, repository.py
# GROK implementa cache.py, webposto_client.py, tests/

# Depois, validar types
make lint                           # ruff + mypy

# Depois, testar
make test                          # pytest
make test-cov                      # com cobertura
```

### FASE 4: E2E (Todos)
```bash
docker compose up -d && sleep 2 && \
curl http://localhost:8050/ready && \
curl http://localhost:8050/health && \
pytest tests/ -v --cov=src

# Se tudo retornar ✅ = PRONTO PARA STAGING
```

---

## 📊 Métricas Esperadas

| Métrica | Target | Status |
|---------|--------|--------|
| Healthcheck Response | < 5ms | 🔄 A validar |
| Cache Hit | < 1ms | 🔄 A implementar |
| Docker Image | < 150MB | ✅ Dockerfile otimizado |
| API Timeout | 10s máximo | 🔄 HTTPX configurado |
| Test Coverage | >= 80% | 🔄 A implementar |
| Type Hints | 100% | 🔄 A validar |
| Startup Time | < 5s | ✅ FastAPI rápido |

---

## 🚀 Velocidade Esperada

```
FASE 1: Setup + Docker     → 5 minutos ✅
FASE 2: CLAUDE impl        → 30 minutos 🔄
FASE 3: GROK impl + tests  → 45 minutos 🔄
FASE 4: Integration        → 15 minutos 🔄
──────────────────────────────────────
TOTAL ESPERADO: ~90 minutos até PRODUCTION-READY
```

---

## 📚 Referências Rápidas

- **FastAPI**: https://fastapi.tiangolo.com/
- **SQLModel**: https://sqlmodel.tiangolo.com/
- **HTTPX**: https://www.python-httpx.org/
- **Pydantic v2**: https://docs.pydantic.dev/latest/
- **pytest**: https://docs.pytest.org/
- **Docker**: https://docs.docker.com/

---

## 🎯 Próximos Passos (Imediato)

1. **GEMINI**: Valide com `docker compose up -d` + `curl`
2. **CLAUDE**: Cole o prompt CLAUDE em seu editor
3. **GROK**: Cole o prompt GROK em seu editor

**E PRONTO! O projeto está 100% estruturado e pronto.**

---

**Criado em**: 2026-05-17  
**Versão**: 1.0.0-alpha  
**Status**: 🚀 PRONTO PARA DESENVOLVIMENTO PARALELO

