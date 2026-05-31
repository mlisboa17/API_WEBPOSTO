"""
Integration Tests: Infrastructure Layer

Testa integração entre componentes de infraestrutura.
"""

import pytest
from decimal import Decimal
from datetime import datetime

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.domain.entities.empresa import (
    Empresa, EmpresaID, CentroCusto, CentroCustoID,
    RateiConfiguracao, Rateio, RateioID, RateioCentroCusto,
    ValorMonetario, SincronizacaoFactory
)
from src.infrastructure.persistence.postgresql.models import Base
from src.infrastructure.persistence.postgresql.repositories import (
    PostgresEmpresaRepository,
    PostgresSyncHistoryRepository,
    PostgresUnitOfWork
)
from src.infrastructure.persistence.repositories import SyncHistory, SyncStatusEnum
from src.infrastructure.webposto.client import WebPostoClient


@pytest.fixture
async def db_session():
    """Fixture para sessão de banco de dados em testes."""
    # Usar SQLite em memória para testes
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    
    # Criar tabelas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with session_factory() as session:
        yield session
    
    await engine.dispose()


class TestPostgresRepositories:
    """Testar implementações PostgreSQL dos Repositories."""
    
    @pytest.mark.asyncio
    async def test_empresa_repository_persistir_e_recuperar(self, db_session):
        """Testar persistência e recuperação de empresa."""
        repo = PostgresEmpresaRepository(db_session)
        
        # Criar empresa de domínio
        config = RateiConfiguracao(
            empresa_id="emp_001",
            tipo_rateio="proporcional",
            validar_soma_100=True
        )
        
        empresa = SincronizacaoFactory.criar_empresa(
            empresa_id="emp_001",
            nome="Empresa Teste Infra",
            config=config
        )
        
        # Adicionar centro de custo
        cc = CentroCusto(
            centro_custo_id=CentroCustoID(valor="cc_001"),
            nome="Centro Operações",
            percentual_padrao=Decimal("100.00")
        )
        empresa.adicionar_centro_custo(cc)
        
        # Persistir
        empresa_id = await repo.persistir(empresa)
        
        assert empresa_id == "emp_001"
        
        # Recuperar
        empresa_recuperada = await repo.obter_por_id(empresa_id)
        
        assert empresa_recuperada is not None
        assert empresa_recuperada.nome == "Empresa Teste Infra"
        assert len(empresa_recuperada.centros_custo) == 1
    
    @pytest.mark.asyncio
    async def test_sync_history_repository_criar_e_atualizar(self, db_session):
        """Testar SyncHistory - criar e atualizar."""
        repo = PostgresSyncHistoryRepository(db_session)
        
        # Criar histórico
        sync = SyncHistory(
            empresa_id="emp_001",
            timestamp_inicio=datetime.utcnow(),
            total_lancamentos_processados=100,
            total_rateios_criados=50
        )
        
        sync_id = await repo.criar(sync)
        
        assert sync_id == sync.sync_id
        
        # Recuperar
        sync_recuperado = await repo.obter_por_id(sync_id)
        
        assert sync_recuperado is not None
        assert sync_recuperado.empresa_id == "emp_001"
        assert sync_recuperado.total_rateios_criados == 50
        
        # Marcar como concluído
        sync.marcar_concluida()
        
        atualizado = await repo.atualizar(sync)
        
        assert atualizado is True
        
        # Verificar atualização
        sync_final = await repo.obter_por_id(sync_id)
        
        assert sync_final.status == SyncStatusEnum.COMPLETED
        assert sync_final.duracao_segundos is not None


class TestUnitOfWork:
    """Testar padrão Unit of Work."""
    
    @pytest.mark.asyncio
    async def test_unit_of_work_transacao_atomica(self, db_session):
        """Testar transaction atomicity no UnitOfWork."""
        uow = PostgresUnitOfWork(db_session)
        
        async with uow:
            # Criar empresa
            config = RateiConfiguracao(
                empresa_id="emp_atomic",
                tipo_rateio="proporcional"
            )
            
            empresa = SincronizacaoFactory.criar_empresa(
                empresa_id="emp_atomic",
                nome="Empresa Atomic",
                config=config
            )
            
            # Persistir via UnitOfWork
            await uow.empresas.persistir(empresa)
            
            # Criar SyncHistory
            sync = SyncHistory(
                empresa_id="emp_atomic",
                timestamp_inicio=datetime.utcnow()
            )
            
            await uow.sync_history.criar(sync)
        
        # Verificar que foi commitado
        empresa_recuperada = await uow.empresas.obter_por_id("emp_atomic")
        
        assert empresa_recuperada is not None


class TestWebPostoClient:
    """Testar cliente WebPosto (mock)."""
    
    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Testar inicialização do cliente."""
        client = WebPostoClient(
            base_url="https://api.webposto.com.br",
            api_key="test_key_123"
        )
        
        assert client.base_url == "https://api.webposto.com.br"
        assert client.api_key == "test_key_123"
        
        await client.connect()
        await client.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
