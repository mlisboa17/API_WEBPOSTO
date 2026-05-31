🔄 GEMINI 2.0 - INSTRUÇÕES TÉCNICAS DETALHADAS
================================================

OBJETIVO PRINCIPAL:
Performance & Infrastructure para suportar multi-tenant com 51 endpoints por empresa.

📊 ESCOPO (40% do projeto):
- 24-32 horas de desenvolvimento
- 3 componentes principais
- Isolamento total entre tenants

---

## COMPONENTE 1: Multi-Tenant Vault (Secret Provider)

ARQUIVO: src/infrastructure/adapters/webposto_multi_tenant.py

### Classe Principal: WebPostoMultiTenantClient

```python
class WebPostoMultiTenantClient:
    """
    Cliente assíncrono multi-tenant com vault de secrets.
    
    Features:
    - Isolamento de tokens por tenant
    - Health check de conectividade
    - Prometheus metrics
    - Retry logic com backoff exponencial
    """
    
    def __init__(self, empresa_id: str):
        # 1. Carregar TenantConfig via tenant_registry
        # 2. Inicializar HTTPX client pool (100 max, 20 keep-alive)
        # 3. Setup Prometheus collectors
        # 4. Registrar no ACTIVE_CONNECTIONS_GAUGE
    
    async def discover(self) -> List[str]:
        """
        Descobrir todos os 51 endpoints disponíveis.
        Cachear resultados em Valkey com TTL=3600s.
        
        Retorna: ["GET /abastecimentos", "POST /clientes", ...]
        """
        pass
    
    async def request(self, 
                      method: str, 
                      endpoint: str, 
                      **kwargs) -> Dict:
        """
        Executar requisição HTTP com:
        - Validação de rate limit
        - Retry automático (3x: 1s, 2s, 4s)
        - Headers obrigatórios: X-Usuario, X-Motivo, X-Request-ID
        - Métricas Prometheus
        
        Raise: RateLimitExceededException, TokenExpiredException
        """
        pass
    
    async def health_check(self) -> bool:
        """Validar se token está válido (ping)."""
        pass
```

### Classe Secundária: SecretsVault

```python
class SecretsVault:
    """
    Gerenciador de tokens com:
    - In-memory cache com TTL
    - Rotação de secrets
    - Auditoria de acesso
    """
    
    async def get_token(self, empresa_id: str) -> str:
        """Retorna token válido do tenant."""
        pass
    
    async def rotate_token(self, empresa_id: str, novo_token: str):
        """Rotacionar token com zero-downtime."""
        pass
```

### Classe Secundária: ConnectionPoolManager

```python
class ConnectionPoolManager:
    """
    Gerencia pools de conexão por tenant.
    
    Features:
    - Pool tamanho: 100 conexões max
    - Keep-alive: 20 conexões
    - Timeout: 30s por requisição
    - Rate limit tracking
    """
    
    async def create_pool(self, empresa_id: str) -> httpx.AsyncClient:
        pass
    
    async def get_connection(self, empresa_id: str) -> httpx.AsyncClient:
        pass
```

---

## COMPONENTE 2: Valkey Cluster Setup

ARQUIVO: docker/valkey/valkey.conf + docker-compose.multitenant.yml

### Configuração Valkey Master (não-cluster):
```
port 6379
databases 16
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
appendonly yes
```

### Configuração Valkey Cluster (3 nós):
```
port 6380-6382
cluster-enabled yes
cluster-node-timeout 5000
```

### Use Cases:
1. Cache de endpoints descobertos (TTL 3600s)
2. Cache de responses frequentes (TTL 300s)
3. Rate limit tracking (TTL 60s per request)
4. Session storage (TTL 86400s)

---

## COMPONENTE 3: Health Check Engine

ARQUIVO: src/infrastructure/adapters/webposto_multi_tenant.py

```python
class HealthCheckEngine:
    """
    Valida saúde de todos os tenants simultaneamente.
    
    Executa a cada 60 segundos:
    - Ping em todos os tokens
    - Valida conectividade Valkey
    - Valida conectividade MongoDB
    - Emite métricas Prometheus
    """
    
    async def run_health_check(self) -> Dict[str, HealthStatus]:
        """
        Retorna:
        {
            "empresa_1": {"status": "healthy", "token_valid": True},
            "empresa_2": {"status": "degraded", "token_valid": False}
        }
        """
        pass
```

---

## TESTES OBRIGATÓRIOS

ARQUIVO: tests/integration/multi_tenant/test_gemini_tasks.py

```python
# TEST 1: Connection Pooling
async def test_connection_pool_isolation():
    """Validar que empresa_1 pool não afeta empresa_2"""
    
# TEST 2: Rate Limiting
async def test_rate_limit_enforcement():
    """Simular 150 req/min, verificar se 100 é o limite"""
    
# TEST 3: Token Rotation
async def test_zero_downtime_token_rotation():
    """Rotacionar token sem interromper requisições"""
    
# TEST 4: Health Check
async def test_health_check_all_tenants():
    """Validar saúde de todos os tenants"""
    
# TEST 5: Load Test (100 req/seg per tenant)
async def test_load_100_req_per_sec():
    """Throughput de 100 req/seg mantendo P99 <50ms"""
```

---

## VALIDAÇÃO DE SUCESSO

✅ Latência média <200ms
✅ Cache hit rate >95%
✅ Zero erros de isolamento
✅ Rate limit respeitado
✅ Todos os 51 endpoints descobertos
✅ Health check passando em todos os tenants
✅ P99 latência <50ms em pico

---

## PRÓXIMA ETAPA (Sincronização com CLAUDE 3.7)

Quando GEMINI terminar:
1. Compartilhar interface WebPostoMultiTenantClient
2. CLAUDE usará para fazer requisições na orquestração
3. GROK usará para coletar métricas de performance

