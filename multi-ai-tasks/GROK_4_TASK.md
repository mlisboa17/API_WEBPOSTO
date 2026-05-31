🔄 GROK 4 - INSTRUÇÕES TÉCNICAS DETALHADAS
==========================================

OBJETIVO PRINCIPAL:
Algorithms & Audit para garantir integridade e performance do sistema.

📊 ESCOPO (20% do projeto):
- 16-24 horas de desenvolvimento
- 4 componentes principais
- 100+ req/seg com P99 <50ms

---

## COMPONENTE 1: Integrity Engine (Hash SHA-256)

ARQUIVO: src/infrastructure/audit/integrity_engine.py

### Classe: IntegrityEngine

```python
class IntegrityEngine:
    """
    Gera e valida hashes SHA-256 para transações.
    
    Garantias:
    - Um hash único por transação + empresa
    - Detecta alterações de dados
    - Rastreável via auditoria
    """
    
    @staticmethod
    def generate_hash(
        empresa_id: str,
        transacao_id: str,
        dados: Dict
    ) -> str:
        """
        Gerar hash SHA-256 determinístico.
        
        Ordem de hashing:
        1. empresa_id
        2. transacao_id
        3. dados (JSON ordenado)
        4. timestamp
        
        Retorna: hex string (64 chars)
        """
        conteudo = {
            "empresa_id": empresa_id,
            "transacao_id": transacao_id,
            "dados": dados,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Serializar determinísticamente (sorted keys)
        json_str = json.dumps(conteudo, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    @staticmethod
    def validar_integridade(
        hash_esperado: str,
        hash_calculado: str
    ) -> bool:
        """Comparar hashes com timing-safe comparison."""
        import hmac
        return hmac.compare_digest(hash_esperado, hash_calculado)
    
    @staticmethod
    def registrar_hash(
        empresa_id: str,
        transacao_id: str,
        hash_value: str,
        tipo: str  # "lancamento", "rateio", etc
    ) -> HashTransacao:
        """Registrar hash em MongoDB para auditoria."""
        pass
```

---

## COMPONENTE 2: Anomaly Detector

ARQUIVO: src/infrastructure/audit/anomaly_detector.py

### Classe: AnomalyDetector

```python
class AnomalyDetector:
    """
    Detecta anomalias comparando performance entre empresas.
    
    Alertas:
    1. Lancamento sem Centro de Custo
    2. Desvio de performance >15% vs média
    3. Rateio inconsistente (soma ≠ 100%)
    4. Token inválido ou expirado
    """
    
    def __init__(self, 
                 prometheus_client,
                 mongo_connection):
        self.prometheus = prometheus_client
        self.mongo = mongo_connection
    
    async def detectar_lancamentos_sem_cc(
        self,
        empresa_id: str
    ) -> List[Anomalia]:
        """
        Encontrar lancamentos que não têm Centro de Custo.
        
        Query MongoDB:
        db.lancamentos.find({
            "empresa_id": empresa_id,
            "centros_custo": {"$size": 0}
        })
        
        Retorna: Lista de anomalias
        """
        pass
    
    async def detectar_desvios_performance(
        self,
        janela_tempo: timedelta = timedelta(hours=1)
    ) -> List[Anomalia]:
        """
        Comparar tempo de resposta entre empresas.
        
        Algoritmo:
        1. Recuperar métricas Prometheus (últimas N horas)
        2. Calcular média geral
        3. Para cada empresa: se (tempo_resp - média) > 15% → Anomalia
        4. Retornar anomalias
        
        Exemplo:
        - Empresa 1: 150ms (média)
        - Empresa 2: 200ms (desvio +33% → ANOMALIA)
        """
        pass
    
    async def detectar_rateios_inconsistentes(
        self,
        empresa_id: str
    ) -> List[Anomalia]:
        """
        Verificar se soma de percentuais = 100%.
        
        Query:
        db.lancamentos.aggregate([
            {"$match": {"empresa_id": empresa_id}},
            {"$unwind": "$rateios"},
            {"$group": {
                "_id": "$lancamento_id",
                "soma_percentual": {"$sum": "$rateios.percentual"}
            }},
            {"$match": {"soma_percentual": {"$ne": 100}}}
        ])
        """
        pass
    
    async def alertar_anomalia(self, anomalia: Anomalia):
        """Enviar alerta (log, Prometheus, etc)."""
        logger.warning(f"ANOMALIA DETECTADA: {anomalia}")
        ANOMALIAS_COUNTER.labels(
            tipo=anomalia.tipo,
            empresa_id=anomalia.empresa_id
        ).inc()
```

---

## COMPONENTE 3: Audit Engine

ARQUIVO: src/infrastructure/audit/audit_engine.py

### Classe: AuditEngine

```python
class AuditEngine:
    """
    Registra auditoria centralizada com:
    - Isolamento por empresa
    - Rastreabilidade completa
    - Hash de integridade
    """
    
    def __init__(self, mongo_connection):
        self.mongo = mongo_connection
        self.auditoria_collection = mongo_connection.db.auditoria
    
    async def registrar_operacao(
        self,
        operacao: Operacao
    ) -> str:
        """
        Registrar operação completa.
        
        Campos:
        - auditoria_id: UUID único
        - empresa_id: Isolamento por tenant
        - usuario_id: Quem fez
        - motivo: Por que fez
        - operacao: GET/POST/PUT/DELETE
        - valor_antes: Estado anterior
        - valor_depois: Estado novo
        - hash_antes: SHA-256 antes
        - hash_depois: SHA-256 depois
        - ip_origem: IP da requisição
        - timestamp: Quando
        - status: sucesso/erro
        """
        
        registro = RegistroAuditoria(
            auditoria_id=str(uuid.uuid4()),
            empresa_id=operacao.empresa_id,
            usuario_id=operacao.usuario_id,
            motivo=operacao.motivo,
            operacao=operacao.operacao,
            valor_antes=operacao.valor_antes,
            valor_depois=operacao.valor_depois,
            hash_antes=operacao.hash_antes,
            hash_depois=operacao.hash_depois,
            ip_origem=operacao.ip_origem,
            timestamp=datetime.utcnow(),
            status="sucesso"
        )
        
        result = await self.auditoria_collection.insert_one(
            registro.model_dump()
        )
        
        return str(result.inserted_id)
    
    async def recuperar_auditoria(
        self,
        empresa_id: str,
        filtros: Dict = None
    ) -> List[RegistroAuditoria]:
        """
        Recuperar registros de auditoria com filtros.
        
        Filtros opcionais:
        - usuario_id
        - operacao (GET, POST, etc)
        - data_inicio, data_fim
        - status (sucesso, erro)
        """
        pass
```

---

## COMPONENTE 4: Adaptive Cache Manager

ARQUIVO: src/infrastructure/caching/adaptive_cache.py

### Classe: AdaptiveCacheManager

```python
class AdaptiveCacheManager:
    """
    Cache estratégico que prioriza endpoints críticos.
    
    Estratégia:
    - Endpoints críticos: TTL 3600s, P1
    - Endpoints frequentes: TTL 300s, P2
    - Endpoints raros: TTL 60s, P3
    """
    
    def __init__(self, valkey_master, valkey_cluster):
        self.master = valkey_master  # Non-cluster ops
        self.cluster = valkey_cluster  # High-volume caching
    
    async def get(self, 
                  empresa_id: str,
                  endpoint: str) -> Optional[Dict]:
        """
        Recuperar do cache.
        
        Prioridade:
        1. Cluster (alta latência/alta concorrência)
        2. Master (backup)
        """
        cache_key = f"{empresa_id}:{endpoint}"
        
        # Tentar cluster
        value = await self.cluster.get(cache_key)
        if value:
            CACHE_HITS_COUNTER.labels(empresa_id=empresa_id).inc()
            return json.loads(value)
        
        # Tentar master
        value = await self.master.get(cache_key)
        if value:
            CACHE_HITS_COUNTER.labels(empresa_id=empresa_id).inc()
            return json.loads(value)
        
        # Cache miss
        CACHE_MISSES_COUNTER.labels(empresa_id=empresa_id).inc()
        return None
    
    async def set(self,
                  empresa_id: str,
                  endpoint: str,
                  value: Dict,
                  ttl_segundos: int = None):
        """
        Armazenar no cache com TTL adaptativo.
        
        TTL automático baseado em prioridade:
        - /abastecimentos: 3600s (P1)
        - /financeiro: 3600s (P1)
        - /clientes: 300s (P2)
        - /outros: 60s (P3)
        """
        if not ttl_segundos:
            ttl_segundos = self._get_ttl_for_endpoint(endpoint)
        
        cache_key = f"{empresa_id}:{endpoint}"
        cache_value = json.dumps(value)
        
        await self.cluster.setex(
            cache_key,
            ttl_segundos,
            cache_value
        )
    
    @staticmethod
    def _get_ttl_for_endpoint(endpoint: str) -> int:
        """Retorna TTL baseado no endpoint."""
        criticos = ["/abastecimentos", "/financeiro"]
        frequentes = ["/clientes", "/vendas"]
        
        if any(e in endpoint for e in criticos):
            return 3600
        elif any(e in endpoint for e in frequentes):
            return 300
        return 60
```

---

## TESTE DE CARGA: 3 Empresas Simultâneas

ARQUIVO: tests/load/test_load_3_tenants.py

```python
async def test_load_3_tenants_100_req_sec():
    """
    Simular:
    - 3 empresas
    - 51 endpoints cada
    - 100 req/seg por empresa (300 total)
    - Duração: 60 segundos
    - Métricas esperadas: P99 <50ms, zero erros
    """
    
    empresas = ["tenant_1", "tenant_2", "tenant_3"]
    endpoints = get_all_51_endpoints()
    
    async def workload():
        for _ in range(6000):  # 100 req/sec × 60 sec
            empresa = random.choice(empresas)
            endpoint = random.choice(endpoints)
            
            start = time.time()
            response = await client.request(
                "GET",
                f"/api/{endpoint}",
                headers={"X-Empresa-ID": empresa}
            )
            duration_ms = (time.time() - start) * 1000
            
            assert response.status_code == 200
            LATENCIES.append(duration_ms)
    
    # Executar workload
    await asyncio.gather(*[workload() for _ in range(10)])
    
    # Validar resultados
    p99 = numpy.percentile(LATENCIES, 99)
    assert p99 < 50, f"P99 = {p99}ms > 50ms"
    assert len(LATENCIES) == 6000
    assert error_count == 0
```

---

## VALIDAÇÃO DE SUCESSO

✅ Hash SHA-256 único por transação
✅ Anomalias detectadas com >95% acurácia
✅ Teste de carga passando (100+ req/seg)
✅ Cache strategy reduzindo latência 90%
✅ P99 <50ms em pico de carga
✅ Zero perda de auditoria
✅ Taxa de erro <0.1%

---

## PRÓXIMA ETAPA (Integração Final)

Quando GROK terminar:
1. Disponibilizar IntegrityEngine para CLAUDE usar em Rateios
2. Disponibilizar AnomalyDetector para monitoramento
3. Integração total: GEMINI + CLAUDE + GROK
4. Teste end-to-end com 3 tenants

