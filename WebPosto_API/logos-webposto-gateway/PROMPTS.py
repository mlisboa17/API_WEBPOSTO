"""
🚀 PROMPT PARA IAs DO VS CODE - Logos Gateway API (Porta 8050)
================================================================

Este arquivo contém os PROMPTS EXATOS que você deve colar nas suas IAs
(GEMINI 2.0, CLAUDE 3.7, GROK 4) para que começem o desenvolvimento paralelo.

Cada IA tem uma seção com seu contexto específico.

INSTRUÇÕES DE USO:
1. Abra a IA respectiva no seu VS Code
2. Cole o prompt inteiro
3. Execute e acompanhe o progresso

================================================================
"""

# ===== GEMINI 2.0 PROMPT =====
GEMINI_PROMPT = """
🔄 TAREFA GEMINI 2.0: Infraestrutura & Porta 8050 (COMPLETAR VERIFICAÇÃO)

CONTEXTO:
Você está trabalhando em um API Gateway centralizado na porta 8050 para integração
com o WebPosto. Sua responsabilidade é garantir que:

1. FastAPI está configurado OBRIGATORIAMENTE para escutar na porta 8050
2. O banco de dados SQLite assíncrono está funcional
3. Os endpoints /ready e /health estão respondendo corretamente
4. Dockerfile Multi-stage está otimizado
5. docker-compose.yml inicia todos os serviços

ARQUIVOS PARA VERIFICAR/COMPLETAR:
- src/main.py                     → FastAPI + lifespan + porta 8050
- src/infrastructure/database.py  → SQLite assíncrono (aiosqlite)
- src/presentation/routes.py      → Endpoints /ready, /health, /
- docker-compose.yml              → Valkey + healthchecks
- Dockerfile                       → Multi-stage Python 3.12-slim
- requirements.txt                → Dependências exatas

CHECKLIST DE VALIDAÇÃO:
1. Executar: docker compose up -d
2. Validar: curl http://localhost:8050/ready (deve retornar HTTP 200)
3. Validar: curl http://localhost:8050/health (deve retornar HTTP 200 + DB status)
4. Performance: SELECT 1 no health deve ser < 5ms (p99)
5. Imagem Docker deve ser < 150MB

DEADLINE: IMMEDIATE
STATUS: Já foi iniciado - FAVOR VALIDAR E COMPLETAR
"""

# ===== CLAUDE 3.7 PROMPT =====
CLAUDE_PROMPT = """
🔄 TAREFA CLAUDE 3.7: Domínio & Lógica de Negócio (IMPLEMENTAR AGORA)

CONTEXTO:
Você é o responsável pela camada de Domínio e Lógica de Negócio do Logos Gateway.
Sua responsabilidade é implementar:

1. Entidades imutáveis do domínio (CashExpense, PostoCredentials)
2. Exceções customizadas de negócio
3. Casos de uso (Use Cases) com orquestração
4. Repositório de credenciais

PADRÃO OBRIGATÓRIO: DDD (Domain-Driven Design) com Injeção de Dependência FastAPI

ARQUIVOS PARA IMPLEMENTAR:
1. src/domain/entities.py
   - Classe CashExpense: id, posto_id, valor (Decimal), descricao, timestamp
   - Classe PostoCredentials: id, posto_id, api_key, api_secret, status
   - OBRIGATÓRIO: frozen=True para imutabilidade

2. src/domain/exceptions.py
   - PostoNaoConfiguradoException: Quando ID não está no DB local
   - PostoInativoException: Quando status != 'ativa'
   - WebPostoIntegracaoException: Erros HTTP
   - DadosInvalidosException: Falhas de validação

3. src/application/fetch_expenses.py
   - Classe FetchExpensesUseCase
   - Método async execute(posto_id, data_consulta, db_session) -> List[CashExpense]
   - Orquestração: repositório → client → parser

4. src/infrastructure/repository.py
   - Classe PostoCredentialsRepository
   - Método get_by_posto_id(posto_id) -> Optional[PostoCredentials]
   - Usar SQLAlchemy select() assíncrono

PADRÃO DE CÓDIGO ESPERADO:
- 100% type hints (mypy --strict)
- Pydantic v2 com validação
- FastAPI Depends para injeção de dependência
- Exceções específicas por domínio

DEADLINE: IMMEDIATE
COMECE AGORA: Implemente entities.py primeiro, depois exceptions.py
"""

# ===== GROK 4 PROMPT =====
GROK_PROMPT = """
🔄 TAREFA GROK 4: Algoritmos, Cache & Resiliência (IMPLEMENTAR AGORA)

CONTEXTO:
Você é o responsável pela camada de Infraestrutura avançada: cliente HTTP,
cache local, e resiliência. Sua responsabilidade é implementar:

1. Cliente HTTP assíncrono robusto para WebPosto
2. Sistema de cache local em memória com expiração (TTL 5 minutos)
3. Circuit breaker simples e retry com backoff
4. Suite de testes (pytest + asyncio)

PADRÃO OBRIGATÓRIO: Assincronismo puro (async/await) + type hints strict

ARQUIVOS PARA IMPLEMENTAR:

1. src/infrastructure/webposto_client.py
   - Classe WebPostoClient com httpx.AsyncClient
   - Context manager: __aenter__, __aexit__
   - Método async fetch_expenses(credentials, data_consulta) -> List[CashExpense]
   - TIMEOUT RÍGIDO: máximo 10 segundos
   - Parser robusto: JSON → CashExpense
   - Circuit breaker: máximo 3 tentativas com backoff exponencial

2. src/infrastructure/cache.py
   - Classe CacheManager com TTL configurável (default 5 min)
   - Índex por MD5(f"{posto_id}_{data.isoformat()}")
   - Método get(posto_id, data) -> Optional[Any]
   - Método set(posto_id, data, value) -> None
   - Método cleanup_expired() -> int (retorna quantos expirados foram removidos)
   - Usar datetime.utcnow() para comparações

3. tests/test_cache.py e tests/test_webposto_client.py
   - Testes assíncronos com pytest-asyncio
   - Mock do cliente HTTPX
   - Validação de timeout
   - Validação de cache (hit, miss, expire)
   - Cobertura >= 80%

REQUISITOS DE PERFORMANCE:
- HTTPX timeout: máximo 10 segundos
- Cache hit: < 1ms
- Cache cleanup: automático ao buscar valores expirados
- Memória: < 50MB para 1000 entradas
- Recuperação de erro: nunca travamento

DEADLINE: IMMEDIATE
COMECE AGORA: Implemente cache.py primeiro (mais simples), depois webposto_client.py
"""

# ===== INSTRUÇÕES DE COORDENAÇÃO =====
COORDINATION_NOTES = """
📋 INSTRUÇÕES DE COORDENAÇÃO ENTRE IAs

FASE 1: Setup Inicial (Paralelo)
- GEMINI: Valida infraestrutura (docker-compose up -d)
- CLAUDE: Implementa entidades e exceções
- GROK: Implementa cache e preparações

FASE 2: Integração (Paralelo)
- GEMINI: Valida endpoints /ready e /health
- CLAUDE: Implementa use cases e repositório
- GROK: Implementa cliente HTTP e testes

FASE 3: Validação (Sequencial)
- GROK: "Testes passando?"
- CLAUDE: "Casos de uso rodando?"
- GEMINI: "API respondendo na porta 8050?"

FASE 4: Otimização (Paralelo)
- CLAUDE: Type hints strict (mypy)
- GROK: Testes com cobertura 80%+
- GEMINI: Docker image size < 150MB

🎯 PONTO DE ENCONTRO: Arquivo TASK_ALLOCATION.py
Este arquivo contém a alocação completa e pode ser consultado por qualquer IA
para validar que está no caminho correto.

COMANDO PARA VALIDAR TUDO:
docker compose up -d && sleep 2 && \
curl http://localhost:8050/ready && \
curl http://localhost:8050/health && \
pytest tests/ -v --cov=src

Se tudo retornar ✅, o projeto está pronto para staging.
"""

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        agent = sys.argv[1].lower()
        if agent == "gemini":
            print(GEMINI_PROMPT)
        elif agent == "claude":
            print(CLAUDE_PROMPT)
        elif agent == "grok":
            print(GROK_PROMPT)
        elif agent == "coordination":
            print(COORDINATION_NOTES)
        else:
            print("Agente desconhecido. Use: gemini, claude, grok, coordination")
    else:
        print("Prompts disponíveis:")
        print("  python prompts.py gemini       → GEMINI 2.0 prompt")
        print("  python prompts.py claude       → CLAUDE 3.7 prompt")
        print("  python prompts.py grok         → GROK 4 prompt")
        print("  python prompts.py coordination → Notas de coordenação")

