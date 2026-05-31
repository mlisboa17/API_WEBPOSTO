#!/usr/bin/env python3
"""
TASK ALLOCATION PARA IAs DO VS CODE
====================================

Este arquivo documenta a divisão de tarefas paralelas para:
- GEMINI 2.0 (Performance & Infraestrutura)
- CLAUDE 3.7 (Domínio & Lógica de Negócio)
- GROK 4 (Algoritmos & Resiliência)

Cada IA deve trabalhar independentemente em seus arquivos,
com mínimo acoplamento entre camadas.
"""

import json
from datetime import datetime

TASK_ALLOCATION = {
    "project": "Logos WebPosto Gateway API",
    "port": 8050,
    "version": "1.0.0-alpha",
    "date": datetime.now().isoformat(),
    
    "tasks": [
        {
            "id": "GEMINI_2.0",
            "agent": "GEMINI 2.0",
            "expertise": "Performance, Infraestrutura & Porta 8050",
            "status": "COMPLETO",
            "files": [
                "src/main.py",
                "src/infrastructure/database.py",
                "src/presentation/routes.py",
                "docker-compose.yml",
                "Dockerfile",
                "requirements.txt"
            ],
            "deliverables": {
                "completed": [
                    "✅ FastAPI escuta porta 8050 com lifespan async",
                    "✅ SQLite assíncrono (aiosqlite) inicializado",
                    "✅ Endpoint /ready (HTTP 200 sem validação)",
                    "✅ Endpoint /health (SELECT 1 rápido)",
                    "✅ Dockerfile Multi-stage Python 3.12-slim",
                    "✅ docker-compose.yml com Valkey + healthchecks"
                ]
            },
            "acceptance_criteria": {
                "port_binding": "Obrigatória porta 8050 vinculada",
                "healthcheck": "p99 < 5ms no SELECT 1",
                "image_size": "< 150MB",
                "startup_time": "< 5 segundos"
            },
            "deadline": "IMMEDIATE"
        },
        {
            "id": "CLAUDE_3.7",
            "agent": "CLAUDE 3.7",
            "expertise": "Modelagem de Domínio, Exceções & Injeção de Dependência",
            "status": "EM ANDAMENTO",
            "files": [
                "src/domain/entities.py",
                "src/domain/exceptions.py",
                "src/application/fetch_expenses.py",
                "src/infrastructure/repository.py"
            ],
            "tasks": [
                {
                    "task": "Entidades do Domínio",
                    "file": "src/domain/entities.py",
                    "requirements": [
                        "Classe CashExpense com Pydantic v2",
                        "Atributos: id, posto_id, valor (Decimal), descricao, timestamp",
                        "frozen=True para imutabilidade",
                        "Classe PostoCredentials (id, posto_id, api_key, api_secret, status)",
                        "Table=True para mapeamento SQLModel"
                    ]
                },
                {
                    "task": "Exceções Customizadas",
                    "file": "src/domain/exceptions.py",
                    "requirements": [
                        "PostoNaoConfiguradoException (quando ID não está no DB)",
                        "PostoInativoException (quando status != 'ativa')",
                        "WebPostoIntegracaoException (erros HTTP)",
                        "DadosInvalidosException (falhas de validação)",
                        "Cada exceção deve conter contexto relevante"
                    ]
                },
                {
                    "task": "Use Case - FetchExpensesUseCase",
                    "file": "src/application/fetch_expenses.py",
                    "requirements": [
                        "Classe com método async execute()",
                        "Recebe: posto_id, data_consulta, db_session",
                        "Retorna: List[CashExpense]",
                        "Levanta PostoNaoConfiguradoException se credenciais não encontradas",
                        "Orquestra chamadas a repository e client"
                    ]
                },
                {
                    "task": "Repositório de Credenciais",
                    "file": "src/infrastructure/repository.py",
                    "requirements": [
                        "Classe PostoCredentialsRepository",
                        "Método get_by_posto_id(posto_id) -> Optional[PostoCredentials]",
                        "Método get_all_active() -> List[PostoCredentials]",
                        "Usar SQLAlchemy select() assíncrono",
                        "Cache simples no repositório (opcional)"
                    ]
                }
            ],
            "acceptance_criteria": {
                "immutability": "frozen=True obrigatória",
                "dependency_injection": "FastAPI Depends em todos os endpoints",
                "error_handling": "Exceções mapeadas para HTTP status corretos",
                "type_hints": "100% type hints (mypy --strict)",
                "tests": "pytest com cobertura 80%+"
            },
            "deadline": "IMMEDIATE"
        },
        {
            "id": "GROK_4",
            "agent": "GROK 4",
            "expertise": "Algoritmos de Caching, Resiliência & Cliente HTTP",
            "status": "EM ANDAMENTO",
            "files": [
                "src/infrastructure/webposto_client.py",
                "src/infrastructure/cache.py",
                "tests/"
            ],
            "tasks": [
                {
                    "task": "Cliente HTTP Assíncrono",
                    "file": "src/infrastructure/webposto_client.py",
                    "requirements": [
                        "Classe WebPostoClient com httpx.AsyncClient",
                        "Context manager (__aenter__, __aexit__)",
                        "Método async fetch_expenses(credentials, data_consulta)",
                        "Injetar credenciais nos headers X-API-Key, X-API-Secret",
                        "Timeout rígido: máximo 10 segundos",
                        "Parser robusto JSON → List[CashExpense]",
                        "Circuit breaker simples (max 3 tentativas)"
                    ]
                },
                {
                    "task": "Sistema de Cache Local",
                    "file": "src/infrastructure/cache.py",
                    "requirements": [
                        "Classe CacheManager com TTL configurável (default 5 min)",
                        "Índex por MD5(f'{posto_id}_{data.isoformat()}')",
                        "Método get(posto_id, data) -> Optional[Any]",
                        "Método set(posto_id, data, value) -> None",
                        "Método cleanup_expired() -> int",
                        "Limpeza automática ao buscar valores expirados",
                        "Uso mínimo de memória"
                    ]
                },
                {
                    "task": "Suite de Testes",
                    "file": "tests/",
                    "requirements": [
                        "pytest com pytest-asyncio",
                        "Mock do cliente WebPosto",
                        "Validação de timeouts",
                        "Testes de cache (hit, miss, expire)",
                        "Cobertura 80%+ do código",
                        "E2E com docker-compose"
                    ]
                }
            ],
            "acceptance_criteria": {
                "timeout": "Máximo 10 segundos em HTTPX",
                "cache_ttl": "5 minutos configurável",
                "circuit_breaker": "Max 3 tentativas com backoff",
                "memory_usage": "< 50MB para 1000 entradas em cache",
                "test_coverage": ">= 80%",
                "error_recovery": "Nunca travamento por timeout"
            },
            "deadline": "IMMEDIATE"
        }
    ],
    
    "integration_points": {
        "between_GEMINI_and_CLAUDE": [
            "GEMINI fornece FastAPI app",
            "CLAUDE consome via FastAPI Depends"
        ],
        "between_CLAUDE_and_GROK": [
            "CLAUDE define exceções",
            "GROK levanta exceções em client/cache"
        ],
        "between_GROK_and_GEMINI": [
            "GROK usa database.py do GEMINI",
            "GROK retorna dados ao router do GEMINI"
        ]
    },
    
    "parallel_execution_strategy": {
        "phase_1_setup": "Todos em paralelo criam seus arquivos base",
        "phase_2_implementation": "Cada IA implementa seu escopo independente",
        "phase_3_integration": "Testes E2E validam fluxo completo",
        "phase_4_optimization": "Ajustes de performance e segurança"
    },
    
    "validation_commands": {
        "start_api": "docker compose up -d",
        "test_ready": "curl -X GET http://localhost:8050/ready",
        "test_health": "curl -X GET http://localhost:8050/health",
        "run_tests": "pytest tests/ -v --cov=src",
        "check_types": "mypy src/ --strict",
        "code_quality": "ruff check src/",
        "format": "black src/ tests/",
        "stop_api": "docker compose down"
    }
}


if __name__ == "__main__":
    print(json.dumps(TASK_ALLOCATION, indent=2, default=str))
    print("\n" + "="*80)
    print("📋 TASK ALLOCATION SUMMARY")
    print("="*80)
    for task in TASK_ALLOCATION["tasks"]:
        print(f"\n🔷 {task['id']} ({task['status']})")
        print(f"   Agent: {task['agent']}")
        print(f"   Files: {', '.join(task['files'][:2])}...")
        print(f"   Deadline: {task['deadline']}")

