🚀 QUICK START - SISTEMA MULTI-TENANT 3 IAs
============================================

## 📋 SETUP INICIAL (Todos fazem isso)

### 1. Clone e Environment

```bash
git clone . && cd Api_WebPosto
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Copiar .env template

```bash
cp .env.example .env
# Editar .env com credenciais reais (NUNCA fazer commit!)
```

### 3. Iniciar Docker Compose

```bash
# OPÇÃO A: Usar compose multi-tenant (recomendado para 3 IAs)
docker compose -f docker-compose.multitenant.yml up -d

# OPÇÃO B: Usar compose padrão
docker compose up -d

# Aguardar services ficarem healthy (30-60 seg)
docker compose -f docker-compose.multitenant.yml ps
```

### 4. Validar Stack

```bash
# Health checks
curl http://localhost:8000/health          # FastAPI
curl http://localhost:27017 | head         # MongoDB
curl http://localhost:6379 && echo PONG    # Valkey Master
redis-cli -p 6380 cluster info             # Valkey Cluster

# Dashboards
open http://localhost:3000                 # Grafana (admin/admin)
open http://localhost:9090                 # Prometheus
```

---

## 🔄 INSTRUÇÕES POR IA

### 🟦 GEMINI 2.0 (Performance/Infra - 40%)

**Arquivo Principal:** `src/infrastructure/adapters/webposto_multi_tenant.py`

#### INÍCIO RÁPIDO:

```bash
# 1. Ler especificação detalhada
cat multi-ai-tasks/GEMINI_2.0_TASK.md

# 2. Implementar classes (na ordem):
# ├─ SecretsVault
# ├─ ConnectionPoolManager
# ├─ WebPostoMultiTenantClient
# └─ HealthCheckEngine

# 3. Validar com testes
pytest tests/integration/multi_tenant/test_parallel_ias.py::test_gemini_health_check -v
pytest tests/integration/multi_tenant/test_parallel_ias.py::test_gemini_rate_limit_enforcement -v

# 4. Executar load test básico
pytest tests/load/test_load_100_req_per_sec.py -v
```

#### Checkpoints dia 1 (T+24h):
- ✅ `SecretsVault.get_token()` funcionando
- ✅ `ConnectionPoolManager.create_pool()` funcionando  
- ✅ Health check passando
- ✅ >50 req/sec no load test

#### Checkpoints dia 2 (T+48h):
- ✅ Retry logic com backoff exponencial
- ✅ Prometheus metrics coletando
- ✅ Rate limiting enforcement
- ✅ >100 req/sec no load test

#### Entrega Final (T+72h):
- ✅ 100 req/sec sustentado
- ✅ P99 <50ms
- ✅ Cache hit rate >95%
- ✅ Zero erros de isolamento

---

### 🟦 CLAUDE 3.7 (Arquitetura/DDD - 40%)

**Arquivo Principal:** `src/domain/entities/empresa.py`

#### INÍCIO RÁPIDO:

```bash
# 1. Ler especificação detalhada
cat multi-ai-tasks/CLAUDE_3.7_TASK.md

# 2. Implementar classes (na ordem):
# ├─ Value Objects (EmpresaID, CentroCustoID, ValorMonetario)
# ├─ Entities (CentroCusto, Rateio)
# ├─ Domain Events (SyncStartedEvent, DivergenciaCCDetectada)
# ├─ Empresa (AggregateRoot)
# ├─ ValidadorRateio (Domain Service)
# └─ SincronizacaoFactory

# 3. Validar com testes
pytest tests/unit/domain/test_claude_tasks.py -v

# 4. Rodar unit tests completos
pytest tests/unit/ -v --cov=src/domain --cov-report=html
```

#### Checkpoints dia 1 (T+24h):
- ✅ Value Objects criados e imutáveis
- ✅ Empresa AggregateRoot funcionando
- ✅ Domain Events estruturados
- ✅ >80% unit test coverage

#### Checkpoints dia 2 (T+48h):
- ✅ ValidadorRateio implementado
- ✅ Rateio Entity com validações
- ✅ Factory Pattern operacional
- ✅ Integração com WebPostoMultiTenantClient de GEMINI
- ✅ >90% coverage

#### Entrega Final (T+72h):
- ✅ Sincronização paralela funcionando
- ✅ Todas validações de negócio
- ✅ Domain Events emitidos corretamente
- ✅ >90% unit test coverage

---

### 🟦 GROK 4 (Algoritmos/Auditoria - 20%)

**Arquivo Principal:** `src/infrastructure/audit/integrity_engine.py`

#### INÍCIO RÁPIDO:

```bash
# 1. Ler especificação detalhada
cat multi-ai-tasks/GROK_4_TASK.md

# 2. Implementar classes (na ordem):
# ├─ IntegrityEngine (hash SHA-256)
# ├─ AnomalyDetector
# ├─ AuditEngine
# └─ AdaptiveCacheManager

# 3. Validar com testes
pytest tests/integration/multi_tenant/test_parallel_ias.py::test_grok_hash_deterministic -v
pytest tests/integration/multi_tenant/test_parallel_ias.py::test_grok_anomaly_detection -v

# 4. Executar load test de 3 tenants
pytest tests/load/test_load_3_tenants.py -v
```

#### Checkpoints dia 1 (T+24h):
- ✅ IntegrityEngine.generate_hash() determinístico
- ✅ Hash SHA-256 válido
- ✅ AnomalyDetector skeleton pronto
- ✅ AuditEngine registrando em MongoDB

#### Checkpoints dia 2 (T+48h):
- ✅ Anomalias detectadas com >95% acurácia
- ✅ Auditoria completa salvando
- ✅ Adaptive cache strategy funcionando
- ✅ >50 req/sec suportado
- ✅ >80% coverage

#### Entrega Final (T+72h):
- ✅ 300 req/sec (3 tenants × 100 req/sec)
- ✅ P99 <50ms em pico
- ✅ Cache hit rate >95%
- ✅ Taxa de erro <0.1%
- ✅ Zero perda de auditoria

---

## 🔗 PONTOS DE SINCRONIZAÇÃO

### Dia 1 (T+24h) - Fim de expediente

**GEMINI**: Health check passando
**CLAUDE**: Empresa AggregateRoot criada
**GROK**: IntegrityEngine.generate_hash() funcionando

```bash
# Validar tudo
pytest tests/integration/multi_tenant/test_parallel_ias.py -v -k "test_gemini_health_check or test_claude_empresa_creation or test_grok_hash_deterministic"
```

### Dia 2 (T+48h) - Fim de expediente

**GEMINI**: Rate limiting + Prometheus métricas
**CLAUDE**: ValidadorRateio + Factory Pattern
**GROK**: AnomalyDetector + Auditoria completa

```bash
# Validar integrações cruzadas
pytest tests/integration/multi_tenant/test_parallel_ias.py::test_integration_gemini_claude_request_chain -v
pytest tests/integration/multi_tenant/test_parallel_ias.py::test_integration_claude_grok_hash_chain -v
```

### Dia 3 (T+72h) - Go Live!

**GEMINI**: 100 req/sec, P99 <50ms
**CLAUDE**: Sincronização paralela 100% funcional
**GROK**: Load test 3 tenants × 100 req/sec passando

```bash
# Validar flow completo
pytest tests/integration/multi_tenant/test_parallel_ias.py::test_integration_full_flow -v
pytest tests/load/test_load_3_tenants.py -v
```

---

## 📊 MONITORAMENTO EM TEMPO REAL

### Prometheus (http://localhost:9090)

```
# Métricas GEMINI:
webposto_request_duration_seconds
webposto_cache_hits_total
webposto_cache_misses_total
webposto_active_connections

# Métricas GROK:
webposto_anomalias_total
webposto_audit_registros_total
webposto_cache_hit_rate
```

### Grafana (http://localhost:3000)

```
Dashboards importar:
- Performance por Tenant
- Anomalias detectadas
- Auditoria consolidada
- Cache efficiency
```

---

## 🧪 COMANDOS ÚTEIS

```bash
# Logs tempo real (GEMINI)
docker compose -f docker-compose.multitenant.yml logs -f app

# Acessar MongoDB (CLAUDE)
mongo mongodb://admin:senha123@localhost:27017 --authenticationDatabase=admin

# Acessar Valkey (GROK)
redis-cli -p 6379 KEYS "*"
redis-cli -p 6380 cluster nodes

# Rodar testes específicos
pytest tests/ -v -k "gemini"        # Só GEMINI
pytest tests/ -v -k "claude"        # Só CLAUDE  
pytest tests/ -v -k "grok"          # Só GROK
pytest tests/load/ -v               # Testes de carga

# Coverage report
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

---

## 🆘 TROUBLESHOOTING

### Docker não sobe

```bash
# Limpar e recomeçar
docker compose -f docker-compose.multitenant.yml down -v
docker compose -f docker-compose.multitenant.yml up -d

# Verificar logs
docker compose -f docker-compose.multitenant.yml logs
```

### Python imports falhando

```bash
# Adicionar src ao PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Ou instalar em editable mode
pip install -e .
```

### Testes falhando

```bash
# Verificar se stack está healthy
docker compose -f docker-compose.multitenant.yml ps

# Aguardar 60 segundos
sleep 60

# Tentar novamente
pytest tests/integration/multi_tenant/test_parallel_ias.py -v
```

---

## 📞 CONTATO & SINCRONIZAÇÃO

Todas as 3 IAs devem **ler** este arquivo antes de começar.

**Canais de sincronização:**
1. **SYNC_POINTS.md** - Cronograma oficial
2. **Testes em comum** - `tests/integration/multi_tenant/test_parallel_ias.py`
3. **Métricas Prometheus** - Monitoramento em tempo real

Sucesso! 🚀

