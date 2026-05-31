# ===== UNIT OF WORK CONCRETA =====

class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory):
        self._session_factory = session_factory
        self.session: Optional[AsyncSession] = None
        self._empresas = None
        self._rateios = None
        self._sync_history = None
        self._outbox = None
        self._eventos = None

    @property
    def empresas(self):
        if self._empresas is None:
            self._empresas = PostgresEmpresaRepository(self.session)
        return self._empresas

    # Implementar os outros repositórios conforme necessário

    async def __aenter__(self):
        self.session = self._session_factory()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def commit(self) -> bool:
        # Salvar OutboxEvents antes do commit
        # Exemplo: self.outbox.salvar_eventos(self.empresas.eventos_nao_commitados)
        # Aqui, apenas commit simples
        try:
            await self.session.commit()
            return True
        except Exception:
            await self.session.rollback()
            return False

    async def rollback(self) -> bool:
        try:
            await self.session.rollback()
            return True
        except Exception:
            return False
"""
Persistence Layer: Repository Interfaces & Models

Define contratos para persistência de domínio em PostgreSQL.
"""

from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy import select, insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.persistence.models import Empresa

from src.domain.entities.empresa import (
    Empresa,
    Rateio,
    DomainEvent,
    EmpresaID
)


# ===== ENUMS =====

class SyncStatusEnum(str, Enum):
    """Status de sincronização."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_FAILED = "partially_failed"


# ===== SYNC HISTORY DOMAIN MODEL =====

class SyncHistory(BaseModel):
    """
    Entity: Histórico de Sincronização.
    
    Fornece auditoria de longo prazo para todas as sincronizações.
    Permite rastreamento de problemas e análise de tendências.
    """
    sync_id: str = Field(default_factory=lambda: str(__import__('uuid').uuid4()))
    empresa_id: str
    status: SyncStatusEnum = SyncStatusEnum.PENDING
    timestamp_inicio: datetime
    timestamp_fim: Optional[datetime] = None
    total_lancamentos_processados: int = 0
    total_rateios_criados: int = 0
    total_divergencias_detectadas: int = 0
    total_erros: int = 0
    duracao_segundos: Optional[float] = None
    mensagem_erro: Optional[str] = None
    detalhes: Dict[str, Any] = Field(default_factory=dict)
    timestamp_criacao: datetime = Field(default_factory=datetime.utcnow)
    timestamp_atualizacao: datetime = Field(default_factory=datetime.utcnow)
    
    def marcar_concluida(self):
        """Marcar sincronização como concluída."""
        self.status = SyncStatusEnum.COMPLETED
        self.timestamp_fim = datetime.utcnow()
        self.duracao_segundos = (
            self.timestamp_fim - self.timestamp_inicio
        ).total_seconds()
        self.timestamp_atualizacao = datetime.utcnow()
    
    def marcar_falha(self, erro: str):
        """Marcar sincronização como falha."""
        self.status = SyncStatusEnum.FAILED
        self.mensagem_erro = erro
        self.timestamp_fim = datetime.utcnow()
        self.duracao_segundos = (
            self.timestamp_fim - self.timestamp_inicio
        ).total_seconds()
        self.timestamp_atualizacao = datetime.utcnow()


# ===== OUTBOX PATTERN =====

class OutboxEvent(BaseModel):
    """
    Entity: Evento armazenado em Outbox.
    
    Implementa o Outbox Pattern para garantir consistência eventual
    entre sincronização de domínio e eventos publicados.
    
    Fluxo:
    1. Evento criado no domínio
    2. Armazenado em Outbox
    3. Transação commitada atomicamente com dados
    4. Event Publisher processa Outbox
    5. Evento publicado e marcado como processado
    """
    outbox_id: str = Field(default_factory=lambda: str(__import__('uuid').uuid4()))
    empresa_id: str
    event_type: str
    event_data: Dict[str, Any]
    timestamp_criacao: datetime = Field(default_factory=datetime.utcnow)
    timestamp_publicacao: Optional[datetime] = None
    processado: bool = False
    tentativas: int = 0
    max_tentativas: int = 3
    mensagem_erro: Optional[str] = None
    
    # class Config removida (Pydantic V2: use ConfigDict se necessário)


# ===== REPOSITORY INTERFACES (Contratos) =====

class EmpresaRepository(ABC):
    """
    Repository: Persistência de Empresa.
    
    Interface para abstração de dados. Implementações concretas
    devem usar PostgreSQL via SQLAlchemy/Async.
    """
    
    @abstractmethod
    async def obter_por_id(self, empresa_id: str) -> Optional[Empresa]:
        """Recuperar empresa por ID."""
        pass
    
    @abstractmethod
    async def obter_todas(self) -> List[Empresa]:
        """Recuperar todas as empresas."""
        pass
    
    @abstractmethod
    async def persistir(self, empresa: Empresa) -> str:
        """
        Persistir empresa (create/update).
        
        Retorna:
            empresa_id persistido
        """
        pass
    
    @abstractmethod
    async def deletar(self, empresa_id: str) -> bool:
        """Deletar empresa por ID."""
        pass
    
    @abstractmethod
    async def obter_por_tenant(self, tenant_id: str) -> List[Empresa]:
        """Recuperar empresas por tenant."""
        pass


class RateioRepository(ABC):
    """Repository: Persistência de Rateio."""
    
    @abstractmethod
    async def obter_por_id(self, rateio_id: str) -> Optional[Rateio]:
        """Recuperar rateio por ID."""
        pass
    
    @abstractmethod
    async def obter_por_empresa(self, empresa_id: str) -> List[Rateio]:
        """Recuperar rateios de uma empresa."""
        pass
    
    @abstractmethod
    async def persistir(self, rateio: Rateio) -> str:
        """Persistir rateio."""
        pass
    
    @abstractmethod
    async def obter_por_lancamento(self, lancamento_id: str) -> Optional[Rateio]:
        """Recuperar rateio por ID de lançamento."""
        pass


class SyncHistoryRepository(ABC):
    """Repository: Persistência de Histórico de Sincronização."""
    
    @abstractmethod
    async def criar(self, sync: SyncHistory) -> str:
        """Criar novo histórico de sincronização."""
        pass
    
    @abstractmethod
    async def obter_por_id(self, sync_id: str) -> Optional[SyncHistory]:
        """Recuperar histórico por ID."""
        pass
    
    @abstractmethod
    async def obter_por_empresa(self, empresa_id: str, 
                               limit: int = 100) -> List[SyncHistory]:
        """Recuperar histórico de sincronizações de uma empresa."""
        pass
    
    @abstractmethod
    async def atualizar(self, sync: SyncHistory) -> bool:
        """Atualizar histórico de sincronização."""
        pass
    
    @abstractmethod
    async def obter_ultimas(self, limit: int = 50) -> List[SyncHistory]:
        """Recuperar últimas sincronizações."""
        pass


class OutboxRepository(ABC):
    """Repository: Persistência de Outbox (Eventos não processados)."""
    
    @abstractmethod
    async def adicionar_evento(self, event: OutboxEvent) -> str:
        """Adicionar evento ao Outbox."""
        pass
    
    @abstractmethod
    async def obter_nao_processados(self) -> List[OutboxEvent]:
        """Recuperar eventos não processados."""
        pass
    
    @abstractmethod
    async def marcar_processado(self, outbox_id: str) -> bool:
        """Marcar evento como processado."""
        pass
    
    @abstractmethod
    async def incrementar_tentativas(self, outbox_id: str) -> int:
        """Incrementar contador de tentativas."""
        pass
    
    @abstractmethod
    async def limpar_processados(self, dias: int = 7) -> int:
        """Limpar eventos processados com mais de X dias."""
        pass


class EventRepository(ABC):
    """Repository: Persistência de Eventos de Domínio."""
    
    @abstractmethod
    async def persistir_evento(self, evento: DomainEvent, 
                              empresa_id: str) -> str:
        """Persistir evento de domínio."""
        pass
    
    @abstractmethod
    async def obter_por_empresa(self, empresa_id: str,
                               desde: Optional[datetime] = None) -> List[DomainEvent]:
        """Recuperar eventos de uma empresa."""
        pass
    
    @abstractmethod
    async def obter_por_tipo(self, event_type: str) -> List[DomainEvent]:
        """Recuperar eventos por tipo."""
        pass
    
    @abstractmethod
    async def contar_por_empresa(self, empresa_id: str) -> int:
        """Contar eventos de uma empresa."""
        pass


# ===== UNIT OF WORK PATTERN =====

class UnitOfWork(ABC):
    """
    Unit of Work: Coordena múltiplos repositórios em transação única.
    
    Implementa transações atômicas para garantir consistência eventual.
    """
    
    @property
    @abstractmethod
    def empresas(self) -> EmpresaRepository:
        """Repositório de empresas."""
        pass
    
    @property
    @abstractmethod
    def rateios(self) -> RateioRepository:
        """Repositório de rateios."""
        pass
    
    @property
    @abstractmethod
    def sync_history(self) -> SyncHistoryRepository:
        """Repositório de histórico de sincronização."""
        pass
    
    @property
    @abstractmethod
    def outbox(self) -> OutboxRepository:
        """Repositório de Outbox."""
        pass
    
    @property
    @abstractmethod
    def eventos(self) -> EventRepository:
        """Repositório de eventos."""
        pass
    
    @abstractmethod
    async def __aenter__(self):
        """Context manager entry (iniciar transação)."""
        pass
    
    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit (commit/rollback)."""
        pass
    
    @abstractmethod
    async def commit(self) -> bool:
        """Commitarmudar transação."""
        pass
    
    @abstractmethod
    async def rollback(self) -> bool:
        """Fazer rollback da transação."""
        pass


# ===== IMPLEMENTAÇÃO CONCRETA =====

class PostgresEmpresaRepository:
    def _to_domain(self, model) -> 'Empresa':
        """
        Converte o modelo SQLAlchemy Empresa para a entidade de domínio Empresa.
        Preserva Value Objects e Decimals.
        """
        from src.domain.entities.empresa import Empresa as EmpresaDomain, EmpresaID, CentroCusto as CentroCustoDomain, CentroCustoID, RateiConfiguracao
        # Mapear centros de custo
        centros_custo = []
        if hasattr(model, 'centros_custo') and model.centros_custo:
            for cc in model.centros_custo:
                centros_custo.append(CentroCustoDomain(
                    centro_custo_id=CentroCustoID(valor=cc.centro_custo_id),
                    nome=cc.nome,
                    percentual_padrao=cc.percentual_padrao,
                    ativo=True if hasattr(cc, 'ativo') else True,
                    timestamp_criacao=getattr(cc, 'timestamp_criacao', datetime.now(timezone.utc))
                ))
        config_rateio = RateiConfiguracao(
            empresa_id=model.empresa_id,
            tipo_rateio=model.config_tipo_rateio,
            validar_soma_100=model.validar_soma_100,
            timestamp_criacao=getattr(model, 'timestamp_criacao', datetime.now(timezone.utc))
        )
        return EmpresaDomain(
            empresa_id=EmpresaID(valor=model.empresa_id),
            nome=model.nome,
            centros_custo=centros_custo,
            config_rateio=config_rateio,
            rateios=[],
            eventos_nao_commitados=[],
            timestamp_criacao=getattr(model, 'timestamp_criacao', datetime.now(timezone.utc))
        )

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, empresa_id: str) -> Optional[Empresa]:
        from src.infrastructure.persistence.models import Empresa as EmpresaModel
        from sqlalchemy.orm import selectinload
        stmt = (
            select(EmpresaModel)
            .options(selectinload(EmpresaModel.centros_custo))
            .where(EmpresaModel.empresa_id == empresa_id)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            return self._to_domain(model)
        return None

    async def save(self, empresa: Empresa) -> None:
        self.session.add(empresa)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise

    async def save_batch(self, empresas: list[Empresa]) -> None:
        from src.infrastructure.persistence.models import Empresa as EmpresaModel
        if not empresas:
            return
        # Prepara os dados para inserção
        values = [
            {k: getattr(e, k) for k in EmpresaModel.__table__.columns.keys()} for e in empresas
        ]
        update_columns = {
            col: col for col in EmpresaModel.__table__.columns
            if col.name != "empresa_id"
        }
        stmt = (
            pg_insert(EmpresaModel)
            .values(values)
            .on_conflict_do_update(
                index_elements=[EmpresaModel.empresa_id],
                set_=update_columns
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()
