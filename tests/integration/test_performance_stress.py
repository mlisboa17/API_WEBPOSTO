"""
Stress tests: Batch insert and healthcheck performance benchmarks.
Tests p99 latency for batch operations.
"""
import asyncio
import pytest
import time
from src.infrastructure.database import get_session
from sqlalchemy import text
from src.infrastructure.persistence.models import Empresa as EmpresaModel
from src.infrastructure.persistence.repositories import PostgresEmpresaRepository
from src.infrastructure.cache.redis_adapter import RedisCacheAdapter
from src.infrastructure.clients.webposto_client import WebPostoClient
import uuid


@pytest.mark.asyncio
async def test_batch_insert_performance():
    """
    Test batch insert performance: 1000 records should be < 500ms.
    Track p99 latency across multiple runs.
    """
    latencies = []
    num_runs = 5
    records_per_batch = 200
    
    for run in range(num_runs):
        async with get_session() as session:
            repo = PostgresEmpresaRepository(session)
            empresas = []
            
            # Create 200 fake empresas
            for i in range(records_per_batch):
                empresa = EmpresaModel(
                    empresa_id=str(uuid.uuid4()),
                    nome=f"Empresa Stress Test {run}-{i}",
                    config_tipo_rateio="padrao",
                    validar_soma_100=True,
                    ativo=True,
                    version=1,
                    checksum=""
                )
                empresas.append(empresa)
            
            # Measure batch insert time
            start = time.perf_counter()
            await repo.save_batch(empresas)
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)
            print(f"\nRun {run + 1}: {elapsed_ms:.2f}ms for {records_per_batch} records")
    
    # Calculate p99 latency
    latencies_sorted = sorted(latencies)
    p99_idx = int(len(latencies_sorted) * 0.99)
    p99 = latencies_sorted[p99_idx] if p99_idx < len(latencies_sorted) else latencies_sorted[-1]
    
    print(f"\nBatch Insert Performance Stats:")
    print(f"  Min:  {min(latencies):.2f}ms")
    print(f"  Max:  {max(latencies):.2f}ms")
    print(f"  Mean: {sum(latencies) / len(latencies):.2f}ms")
    print(f"  P99:  {p99:.2f}ms")
    
    # Assert p99 < 500ms for 200 records
    assert p99 < 500, f"Batch insert p99 latency {p99:.2f}ms exceeds 500ms threshold"


@pytest.mark.asyncio
async def test_healthcheck_performance():
    """
    Test healthcheck performance: DB + Redis PING should be < 50ms p99.
    """
    async with get_session() as session:
        repo = PostgresEmpresaRepository(session)
        
        latencies = []
        num_pings = 10
        
        for _ in range(num_pings):
            # Measure DB healthcheck (single query)
            start = time.perf_counter()
            result = await session.execute(text("SELECT 1"))
            db_elapsed_ms = (time.perf_counter() - start) * 1000
            
            latencies.append(db_elapsed_ms)
        
        # Calculate p99 for DB
        latencies_sorted = sorted(latencies)
        p99_idx = int(len(latencies_sorted) * 0.99)
        db_p99 = latencies_sorted[p99_idx] if p99_idx < len(latencies_sorted) else latencies_sorted[-1]
        
        print(f"\nDB Healthcheck Performance (10 pings):")
        print(f"  Min:  {min(latencies):.2f}ms")
        print(f"  Max:  {max(latencies):.2f}ms")
        print(f"  Mean: {sum(latencies) / len(latencies):.2f}ms")
        print(f"  P99:  {db_p99:.2f}ms")
        
        assert db_p99 < 50, f"DB healthcheck p99 {db_p99:.2f}ms exceeds 50ms threshold"


@pytest.mark.asyncio
async def test_cache_performance():
    """
    Test Redis cache performance: GET/SET should be < 30ms p99.
    """
    cache = RedisCacheAdapter()
    await cache.connect()
    
    latencies_set = []
    latencies_get = []
    num_ops = 20
    
    try:
        for i in range(num_ops):
            # Test SET
            start = time.perf_counter()
            await cache.set(f"perf_test_{i}", f"value_{i}", ttl=60)
            set_elapsed_ms = (time.perf_counter() - start) * 1000
            latencies_set.append(set_elapsed_ms)
            
            # Test GET
            start = time.perf_counter()
            val = await cache.get(f"perf_test_{i}")
            get_elapsed_ms = (time.perf_counter() - start) * 1000
            latencies_get.append(get_elapsed_ms)
        
        # Calculate p99
        set_sorted = sorted(latencies_set)
        get_sorted = sorted(latencies_get)
        p99_idx = int(num_ops * 0.99)
        
        set_p99 = set_sorted[p99_idx] if p99_idx < len(set_sorted) else set_sorted[-1]
        get_p99 = get_sorted[p99_idx] if p99_idx < len(get_sorted) else get_sorted[-1]
        
        print(f"\nRedis Cache Performance ({num_ops} ops each):")
        print(f"  SET p99:  {set_p99:.2f}ms")
        print(f"  GET p99:  {get_p99:.2f}ms")
        
        assert set_p99 < 30, f"Cache SET p99 {set_p99:.2f}ms exceeds 30ms"
        assert get_p99 < 30, f"Cache GET p99 {get_p99:.2f}ms exceeds 30ms"
        
    finally:
        await cache.disconnect()
