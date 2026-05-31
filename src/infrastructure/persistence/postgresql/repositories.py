"""
PostgreSQL Repository Implementations: SQLAlchemy async adapters.

Implementa os contratos de Repository usando async SQLAlchemy ORM.
"""

from typing import Optional, List, Tuple
from datetime import datetime
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from decimal import Decimal

from src.domain.entities.empresa import (
    Empresa, EmpresaID, CentroCusto, CentroCustoID,
    Rateio, RateioID, RateioCentroCusto, ValorMonetario,
    RateiConfiguracao, DomainEvent
)
from src.infrastructure.persistence.repositories import (
    EmpresaRepository, RateioRepository, SyncHistoryRepository,
    OutboxRepository, EventRepository, UnitOfWork,
    SyncHistory, OutboxEvent, SyncStatusEnum
)
from .models import (
    Base, EmpresaORM, CentroCustoORM, RateioORM,
    SyncHistoryORM, OutboxEventORM, DomainEventORM
)

logger = logging.getLogger(__name__)


# ===== POSTGRESQL REPOSITORIES =====

class PostgresEmpresaRepository(EmpresaRepository):
    """Implementação PostgreSQL de EmpresaRepository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def obter_por_id(self, empresa_id: str) -> Optional[Empresa]:
        """Recuperar empresa por ID."""
        stmt = select(EmpresaORM).where(EmpresaORM.empresa_id == empresa_id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        
        if not orm:
            return None
        
        return self._orm_para_dominio(orm)
    
    async def obter_todas(self) -> List[Empresa]:
        """Recuperar todas as empresas ativas."""
        stmt = select(EmpresaORM).where(EmpresaORM.ativo == True)
        result = await self.session.execute(stmt)
        orms = result.scalars().all()
        
        return [self._orm_para_dominio(orm) for orm in orms]
    
    async def persistir(self, empresa: Empresa) -> str:
        """Persistir empresa (create/update)."""
        config = empresa.config_rateio
        
        orm = EmpresaORM(
            empresa_id=empresa.empresa_id.valor,
            nome=empresa.nome,
            config_tipo_rateio=config.tipo_rateio,
            validar_soma_100=config.validar_soma_100,
            ativo=True
        )
        
        # Adicionar centros de custo
        for cc in empresa.centros_custo:
            cc_orm = CentroCustoORM(
                centro_custo_id=cc.centro_custo_id.valor,
                empresa_id=empresa.empresa_id.valor,
                nome=cc.nome,
                percentual_padrao=cc.percentual_padrao
            )
            orm.centros_custo.append(cc_orm)
        
        self.session.add(orm)
        await self.session.flush()
        
        logger.info(f"Empresa {empresa.empresa_id.valor} persistida")
        return empresa.empresa_id.valor
    
    async def deletar(self, empresa_id: str) -> bool:
        """Deletar empresa por ID."""
        stmt = select(EmpresaORM).where(EmpresaORM.empresa_id == empresa_id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        
        if not orm:
            return False
        
        await self.session.delete(orm)
        await self.session.flush()
        
        logger.info(f"Empresa {empresa_id} deletada")
        return True
    
    async def obter_por_tenant(self, tenant_id: str) -> List[Empresa]:
        """Recuperar empresas por tenant."""
        # Implementação simplificada: tenant_id = empresa_id prefixado
        stmt = select(EmpresaORM).where(
            EmpresaORM.empresa_id.like(f"{tenant_id}_%")
        )
        result = await self.session.execute(stmt)
        orms = result.scalars().all()
        
        return [self._orm_para_dominio(orm) for orm in orms]
    
    def _orm_para_dominio(self, orm: EmpresaORM) -> Empresa:
        """Converter ORM para entidade de domínio."""
        config = RateiConfiguracao(
            empresa_id=orm.empresa_id,
            tipo_rateio=orm.config_tipo_rateio,
            validar_soma_100=orm.validar_soma_100
        )
        
        centros = [
            CentroCusto(
                centro_custo_id=CentroCustoID(valor=cc.centro_custo_id),
                nome=cc.nome,
                percentual_padrao=cc.percentual_padrao
            )
            for cc in orm.centros_custo
        ]
        
        empresa = Empresa(
            empresa_id=EmpresaID(valor=orm.empresa_id),
            nome=orm.nome,
            centros_custo=centros,
            config_rateio=config
        )
        
        return empresa


class PostgresRateioRepository(RateioRepository):
    """Implementação PostgreSQL de RateioRepository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def obter_por_id(self, rateio_id: str) -> Optional[Rateio]:
        """Recuperar rateio por ID."""
        stmt = select(RateioORM).where(RateioORM.rateio_id == rateio_id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        
        return self._orm_para_dominio(orm) if orm else None
    
    async def obter_por_empresa(self, empresa_id: str) -> List[Rateio]:
        """Recuperar rateios de uma empresa."""
        stmt = select(RateioORM).where(RateioORM.empresa_id == empresa_id)
        result = await self.session.execute(stmt)
        orms = result.scalars().all()
        
        return [self._orm_para_dominio(orm) for orm in orms]
    
    async def persistir(self, rateio: Rateio) -> str:
        """Persistir rateio."""
        detalhes = {
            "centros_custo": [
                {
                    "centro_custo_id": cc.centro_custo_id.valor,
                    "percentual": str(cc.percentual),
                    "valor": str(cc.valor.valor)
                }
                for cc in rateio.centros_custo
            ]
        }
        
        orm = RateioORM(
            rateio_id=rateio.rateio_id.valor,
            empresa_id="",  # Será preenchido pelo contexto
            lancamento_id=rateio.lancamento_id,
            valor_total=rateio.valor_total.valor,
            detalhes=detalhes
        )
        
        self.session.add(orm)
        await self.session.flush()
        
        return rateio.rateio_id.valor
    
    async def obter_por_lancamento(self, lancamento_id: str) -> Optional[Rateio]:
        """Recuperar rateio por lancamento_id."""
        stmt = select(RateioORM).where(RateioORM.lancamento_id == lancamento_id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        
        return self._orm_para_dominio(orm) if orm else None
    
    def _orm_para_dominio(self, orm: RateioORM) -> Rateio:
        """Converter ORM para domínio."""
        centros = []
        if orm.detalhes and "centros_custo" in orm.detalhes:
            for cc_data in orm.detalhes["centros_custo"]:
                cc = RateioCentroCusto(
                    centro_custo_id=CentroCustoID(valor=cc_data["centro_custo_id"]),
                    percentual=Decimal(cc_data["percentual"]),
                    valor=ValorMonetario(valor=Decimal(cc_data["valor"]))
                )
                centros.append(cc)
        
        return Rateio(
            rateio_id=RateioID(valor=orm.rateio_id),
            lancamento_id=orm.lancamento_id,
            centros_custo=centros,
            valor_total=ValorMonetario(valor=orm.valor_total)
        )


class PostgresSyncHistoryRepository(SyncHistoryRepository):
    """Implementação PostgreSQL de SyncHistoryRepository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def criar(self, sync: SyncHistory) -> str:
        """Criar novo histórico de sincronização."""
        orm = SyncHistoryORM(
            sync_id=sync.sync_id,
            empresa_id=sync.empresa_id,
            status=sync.status.value,
            timestamp_inicio=sync.timestamp_inicio,
            timestamp_fim=sync.timestamp_fim,
            total_lancamentos_processados=sync.total_lancamentos_processados,
            total_rateios_criados=sync.total_rateios_criados,
            total_divergencias_detectadas=sync.total_divergencias_detectadas,
            mensagem_erro=sync.mensagem_erro,
            detalhes=sync.detalhes
        )
        
        self.session.add(orm)
        await self.session.flush()
        
        logger.info(f"SyncHistory {sync.sync_id} criado")
        return sync.sync_id
    
    async def obter_por_id(self, sync_id: str) -> Optional[SyncHistory]:
        """Recuperar histórico por ID."""
        stmt = select(SyncHistoryORM).where(SyncHistoryORM.sync_id == sync_id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        
        return self._orm_para_dominio(orm) if orm else None
    
    async def obter_por_empresa(self, empresa_id: str, limit: int = 100) -> List[SyncHistory]:
        """Recuperar histórico de sincronizações de uma empresa."""
        stmt = (
            select(SyncHistoryORM)
            .where(SyncHistoryORM.empresa_id == empresa_id)
            .order_by(SyncHistoryORM.timestamp_inicio.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        orms = result.scalars().all()
        
        return [self._orm_para_dominio(orm) for orm in orms]
    
    async def atualizar(self, sync: SyncHistory) -> bool:
        """Atualizar histórico de sincronização."""
        stmt = select(SyncHistoryORM).where(SyncHistoryORM.sync_id == sync.sync_id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        
        if not orm:
            return False
        
        orm.status = sync.status.value
        orm.timestamp_fim = sync.timestamp_fim
        orm.duracao_segundos = sync.duracao_segundos
        orm.mensagem_erro = sync.mensagem_erro
        orm.timestamp_atualizacao = datetime.utcnow()
        
        await self.session.flush()
        return True
    
    async def obter_ultimas(self, limit: int = 50) -> List[SyncHistory]:
        """Recuperar últimas sincronizações."""
        stmt = (
            select(SyncHistoryORM)
            .order_by(SyncHistoryORM.timestamp_inicio.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        orms = result.scalars().all()
        
        return [self._orm_para_dominio(orm) for orm in orms]
    
    def _orm_para_dominio(self, orm: SyncHistoryORM) -> SyncHistory:
        """Converter ORM para domínio."""
        return SyncHistory(
            sync_id=orm.sync_id,
            empresa_id=orm.empresa_id,
            status=SyncStatusEnum(orm.status),
            timestamp_inicio=orm.timestamp_inicio,
            timestamp_fim=orm.timestamp_fim,
            total_lancamentos_processados=orm.total_lancamentos_processados,
            total_rateios_criados=orm.total_rateios_criados,
            total_divergencias_detectadas=orm.total_divergencias_detectadas,
            duracao_segundos=float(orm.duracao_segundos) if orm.duracao_segundos else None,
            mensagem_erro=orm.mensagem_erro,
            detalhes=orm.detalhes or {}
        )


class PostgresOutboxRepository(OutboxRepository):
    """Implementação PostgreSQL de OutboxRepository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def adicionar_evento(self, event: OutboxEvent) -> str:
        """Adicionar evento ao Outbox."""
        orm = OutboxEventORM(
            outbox_id=event.outbox_id,
            empresa_id=event.empresa_id,
            event_type=event.event_type,
            event_data=event.event_data,
            processado=False,
            tentativas=0
        )
        
        self.session.add(orm)
        await self.session.flush()
        
        return event.outbox_id
    
    async def obter_nao_processados(self) -> List[OutboxEvent]:
        """Recuperar eventos não processados."""
        stmt = select(OutboxEventORM).where(
            OutboxEventORM.processado == False
        ).order_by(OutboxEventORM.timestamp_criacao.asc())
        
        result = await self.session.execute(stmt)
        orms = result.scalars().all()
        
        return [self._orm_para_dominio(orm) for orm in orms]
    
    async def marcar_processado(self, outbox_id: str) -> bool:
        """Marcar evento como processado."""
        stmt = select(OutboxEventORM).where(OutboxEventORM.outbox_id == outbox_id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        
        if not orm:
            return False
        
        orm.processado = True
        orm.timestamp_publicacao = datetime.utcnow()
        await self.session.flush()
        
        return True
    
    async def incrementar_tentativas(self, outbox_id: str) -> int:
        """Incrementar contador de tentativas."""
        stmt = select(OutboxEventORM).where(OutboxEventORM.outbox_id == outbox_id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        
        if not orm:
            return -1
        
        orm.tentativas += 1
        await self.session.flush()
        
        return orm.tentativas
    
    async def limpar_processados(self, dias: int = 7) -> int:
        """Limpar eventos processados com mais de X dias."""
        cutoff_date = datetime.utcnow() - __import__('datetime').timedelta(days=dias)
        
        stmt = select(OutboxEventORM).where(
            (OutboxEventORM.processado == True) &
            (OutboxEventORM.timestamp_publicacao < cutoff_date)
        )
        
        result = await self.session.execute(stmt)
        orms = result.scalars().all()
        
        for orm in orms:
            await self.session.delete(orm)
        
        await self.session.flush()
        return len(orms)
    
    def _orm_para_dominio(self, orm: OutboxEventORM) -> OutboxEvent:
        """Converter ORM para domínio."""
        return OutboxEvent(
            outbox_id=orm.outbox_id,
            empresa_id=orm.empresa_id,
            event_type=orm.event_type,
            event_data=orm.event_data,
            timestamp_criacao=orm.timestamp_criacao,
            timestamp_publicacao=orm.timestamp_publicacao,
            processado=orm.processado,
            tentativas=orm.tentativas
        )


class PostgresEventRepository(EventRepository):
    """Implementação PostgreSQL de EventRepository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def persistir_evento(self, evento: DomainEvent, empresa_id: str) -> str:
        """Persistir evento de domínio."""
        event_id = str(__import__('uuid').uuid4())
        
        orm = DomainEventORM(
            event_id=event_id,
            empresa_id=empresa_id,
            event_type=evento.event_type,
            event_data=evento.model_dump()
        )
        
        self.session.add(orm)
        await self.session.flush()
        
        return event_id
    
    async def obter_por_empresa(
        self,
        empresa_id: str,
        desde: Optional[datetime] = None
    ) -> List[DomainEvent]:
        """Recuperar eventos de uma empresa."""
        stmt = select(DomainEventORM).where(DomainEventORM.empresa_id == empresa_id)
        
        if desde:
            stmt = stmt.where(DomainEventORM.timestamp_criacao >= desde)
        
        stmt = stmt.order_by(DomainEventORM.timestamp_criacao.asc())
        
        result = await self.session.execute(stmt)
        orms = result.scalars().all()
        
        return [DomainEvent(**orm.event_data) for orm in orms]
    
    async def obter_por_tipo(self, event_type: str) -> List[DomainEvent]:
        """Recuperar eventos por tipo."""
        stmt = select(DomainEventORM).where(DomainEventORM.event_type == event_type)
        result = await self.session.execute(stmt)
        orms = result.scalars().all()
        
        return [DomainEvent(**orm.event_data) for orm in orms]
    
    async def contar_por_empresa(self, empresa_id: str) -> int:
        """Contar eventos de uma empresa."""
        stmt = select(func.count(DomainEventORM.event_id)).where(
            DomainEventORM.empresa_id == empresa_id
        )
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0


class PostgresUnitOfWork(UnitOfWork):
    """Implementação PostgreSQL de UnitOfWork."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._empresas: Optional[PostgresEmpresaRepository] = None
        self._rateios: Optional[PostgresRateioRepository] = None
        self._sync_history: Optional[PostgresSyncHistoryRepository] = None
        self._outbox: Optional[PostgresOutboxRepository] = None
        self._eventos: Optional[PostgresEventRepository] = None
    
    @property
    def empresas(self) -> EmpresaRepository:
        if not self._empresas:
            self._empresas = PostgresEmpresaRepository(self.session)
        return self._empresas
    
    @property
    def rateios(self) -> RateioRepository:
        if not self._rateios:
            self._rateios = PostgresRateioRepository(self.session)
        return self._rateios
    
    @property
    def sync_history(self) -> SyncHistoryRepository:
        if not self._sync_history:
            self._sync_history = PostgresSyncHistoryRepository(self.session)
        return self._sync_history
    
    @property
    def outbox(self) -> OutboxRepository:
        if not self._outbox:
            self._outbox = PostgresOutboxRepository(self.session)
        return self._outbox
    
    @property
    def eventos(self) -> EventRepository:
        if not self._eventos:
            self._eventos = PostgresEventRepository(self.session)
        return self._eventos
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
    
    async def commit(self) -> bool:
        try:
            await self.session.commit()
            logger.info("Transaction committed")
            return True
        except Exception as e:
            logger.error(f"Commit failed: {e}")
            await self.session.rollback()
            return False
    
    async def rollback(self) -> bool:
        try:
            await self.session.rollback()
            logger.info("Transaction rolled back")
            return True
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False
