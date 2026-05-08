# 🚀 PROMPT COMPLETO PARA O CURSOR - webposto-service

**Copie e cole TUDO isso no Cursor de uma vez.**

---

Você é um **Arquiteto de Software Sênior** com expertise em Python, arquitetura hexagonal, domain-driven design e sistemas event-driven.

Sua tarefa é **CRIAR DO ZERO um sistema production-ready** que sincroniza dados da API REST do webPosto e alimenta múltiplos serviços internos via eventos.

## 🎯 OBJETIVO FINAL

Criar um projeto Python `webposto-service` que:
1. ✅ Se integra com webPosto REST API (apenas CHAVE no .env)
2. ✅ Sincroniza dados (clientes, produtos, abastecimentos, financeiro, caixa, cartões, relatórios)
3. ✅ Publica eventos para outros serviços consumirem
4. ✅ Expõe API REST interna (FastAPI)
5. ✅ Testes com 100% coverage
6. ✅ Docker pronto pra producção
7. ✅ CI/CD automático (GitHub Actions)
8. ✅ Documentação completa

---

## 📋 PASSO A PASSO - EXECUTE NA ORDEM

### PASSO 1: Criar Estrutura de Diretórios

Crie todas essas pastas:

```
webposto-service/
├── src/
│   ├── domain/
│   │   ├── entities/
│   │   ├── events/
│   │   ├── repositories/
│   │   ├── value_objects/
│   │   └── __init__.py
│   │
│   ├── application/
│   │   ├── dto/
│   │   ├── services/
│   │   ├── event_handlers/
│   │   └── __init__.py
│   │
│   ├── infrastructure/
│   │   ├── webposto/
│   │   ├── repositories/
│   │   ├── event_bus/
│   │   ├── config/
│   │   ├── migrations/
│   │   └── __init__.py
│   │
│   ├── interfaces/
│   │   ├── http/
│   │   │   ├── routes/
│   │   │   └── middleware/
│   │   ├── cli/
│   │   └── __init__.py
│   │
│   ├── shared/
│   │   └── __init__.py
│   │
│   └── main.py
│
├── tests/
│   ├── unit/
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   ├── integration/
│   ├── e2e/
│   ├── mocks/
│   ├── conftest.py
│   ├── factories.py
│   └── __init__.py
│
├── .github/
│   └── workflows/
│       ├── test.yml
│       └── lint.yml
│
├── docker/
│   ├── Dockerfile
│   └── .dockerignore
│
├── docker-compose.yml
├── .env.example
├── .gitignore
├── Makefile
├── pyproject.toml
├── pytest.ini
├── README.md
├── ARCHITECTURE.md
└── LICENSE
```

---

### PASSO 2: Criar Arquivo pyproject.toml

Crie `pyproject.toml` com todas as dependências:

```toml
[tool.poetry]
name = "webposto-service"
version = "0.1.0"
description = "API Integration Service for webPosto - Event-Driven Architecture"
authors = ["Grupo Lisboa <marcio@grupolisboa.com.br>"]
license = "MIT"
readme = "README.md"
packages = [{include = "src"}]

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.0"
uvicorn = {version = "^0.24.0", extras = ["standard"]}
pydantic = "^2.4.0"
pydantic-settings = "^2.0.0"
sqlalchemy = "^2.0.0"
alembic = "^1.12.0"
psycopg2-binary = "^2.9.0"
httpx = "^0.25.0"
redis = "^5.0.0"
python-dotenv = "^1.0.0"
tenacity = "^8.2.0"
structlog = "^23.1.0"
python-json-logger = "^2.0.0"
click = "^8.1.0"
pendulum = "^2.1.0"
pytz = "^2023.3"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
pytest-cov = "^4.1.0"
pytest-mock = "^3.11.0"
responses = "^0.23.0"
testcontainers = "^3.7.0"
faker = "^19.0.0"
factory-boy = "^3.3.0"
black = "^23.9.0"
isort = "^5.12.0"
flake8 = "^6.1.0"
mypy = "^1.5.0"
bandit = "^1.7.0"
pre-commit = "^3.4.0"

[tool.black]
line-length = 100
target-version = ['py311']
include = '\.pyi?$'

[tool.isort]
profile = "black"
line_length = 100
multi_line_mode = 3

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
asyncio_mode = "auto"
addopts = "--cov=src --cov-report=html --cov-report=term-missing --strict-markers"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

---

### PASSO 3: Criar Shared / Base Classes

#### src/shared/__init__.py
```python
# Empty file
```

#### src/shared/domain_event.py
```python
from datetime import datetime
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from abc import ABC

@dataclass
class DomainEvent(ABC):
    """Base class for all domain events"""
    event_id: UUID = field(default_factory=uuid4)
    event_name: str = field(init=False)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    aggregate_id: str = ""

    def __post_init__(self):
        self.event_name = self.__class__.__name__
```

#### src/shared/repository.py
```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional

T = TypeVar('T')

class Repository(ABC, Generic[T]):
    """Base Repository Interface (Port)"""

    @abstractmethod
    async def save(self, entity: T) -> T:
        pass

    @abstractmethod
    async def find_by_id(self, id: str) -> Optional[T]:
        pass

    @abstractmethod
    async def find_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        pass

    @abstractmethod
    async def update(self, entity: T) -> T:
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        pass
```

#### src/shared/logger.py
```python
import structlog
from pythonjsonlogger import jsonlogger
import logging

def setup_logger(name: str, level: str = "INFO"):
    """Configure structured JSON logging"""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger(name)
```

---

### PASSO 4: Criar Domain Layer

#### src/domain/entities/cliente.py
```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4

from src.domain.events.cliente_events import ClienteAdicionado, ClienteAtualizado

@dataclass
class Cliente:
    """Entity: Cliente"""
    id: str = field(default_factory=lambda: str(uuid4()))
    nome: str = ""
    cnpj: str = ""
    ativo: bool = True
    criado_em: datetime = field(default_factory=datetime.utcnow)
    atualizado_em: Optional[datetime] = None
    events: list = field(default_factory=list, init=False)

    def adicionar(self, nome: str, cnpj: str) -> None:
        """Add new cliente"""
        self.nome = nome
        self.cnpj = cnpj
        self.criado_em = datetime.utcnow()
        self.events.append(ClienteAdicionado(aggregate_id=self.id))

    def atualizar(self, nome: str = None, ativo: bool = None) -> None:
        """Update cliente"""
        if nome:
            self.nome = nome
        if ativo is not None:
            self.ativo = ativo
        self.atualizado_em = datetime.utcnow()
        self.events.append(ClienteAtualizado(aggregate_id=self.id))

    def limpar_eventos(self) -> None:
        """Clear events after publishing"""
        self.events.clear()
```

#### src/domain/entities/abastecimento.py
```python
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

@dataclass
class Abastecimento:
    """Entity: Abastecimento"""
    id: str = field(default_factory=lambda: str(uuid4()))
    cliente_id: str = ""
    data: datetime = field(default_factory=datetime.utcnow)
    valor: Decimal = Decimal("0.00")
    litros: Decimal = Decimal("0.00")
    produto_id: str = ""
    criado_em: datetime = field(default_factory=datetime.utcnow)
    events: list = field(default_factory=list, init=False)

    def registrar(self, cliente_id: str, valor: Decimal, litros: Decimal, produto_id: str) -> None:
        """Register new abastecimento"""
        self.cliente_id = cliente_id
        self.valor = valor
        self.litros = litros
        self.produto_id = produto_id
        self.data = datetime.utcnow()
```

#### src/domain/entities/financeiro.py
```python
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import uuid4

class TipoLancamento(str, Enum):
    RECEBER = "receber"
    PAGAR = "pagar"
    TRANSFERENCIA = "transferencia"

@dataclass
class Financeiro:
    """Entity: Financeiro"""
    id: str = field(default_factory=lambda: str(uuid4()))
    tipo: TipoLancamento = TipoLancamento.RECEBER
    descricao: str = ""
    valor: Decimal = Decimal("0.00")
    data_vencimento: datetime = field(default_factory=datetime.utcnow)
    pago: bool = False
    criado_em: datetime = field(default_factory=datetime.utcnow)
    events: list = field(default_factory=list, init=False)
```

#### src/domain/entities/caixa.py
```python
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

@dataclass
class Caixa:
    """Entity: Caixa"""
    id: str = field(default_factory=lambda: str(uuid4()))
    descricao: str = ""
    saldo: Decimal = Decimal("0.00")
    data_movimento: datetime = field(default_factory=datetime.utcnow)
    criado_em: datetime = field(default_factory=datetime.utcnow)
    events: list = field(default_factory=list, init=False)
```

#### src/domain/entities/__init__.py
```python
from .cliente import Cliente
from .abastecimento import Abastecimento
from .financeiro import Financeiro, TipoLancamento
from .caixa import Caixa

__all__ = ["Cliente", "Abastecimento", "Financeiro", "TipoLancamento", "Caixa"]
```

---

### PASSO 5: Criar Events

#### src/domain/events/cliente_events.py
```python
from src.shared.domain_event import DomainEvent
from dataclasses import dataclass

@dataclass
class ClienteAdicionado(DomainEvent):
    """Event: Cliente Added"""
    nome: str = ""
    cnpj: str = ""

@dataclass
class ClienteAtualizado(DomainEvent):
    """Event: Cliente Updated"""
    nome: str = ""

@dataclass
class ClienteDeletado(DomainEvent):
    """Event: Cliente Deleted"""
    pass
```

#### src/domain/events/abastecimento_events.py
```python
from src.shared.domain_event import DomainEvent
from dataclasses import dataclass
from decimal import Decimal

@dataclass
class AbastecimentoRegistrado(DomainEvent):
    """Event: Abastecimento Registered"""
    cliente_id: str = ""
    valor: Decimal = Decimal("0.00")
    litros: Decimal = Decimal("0.00")
```

#### src/domain/events/__init__.py
```python
from .cliente_events import ClienteAdicionado, ClienteAtualizado, ClienteDeletado
from .abastecimento_events import AbastecimentoRegistrado

__all__ = [
    "ClienteAdicionado",
    "ClienteAtualizado",
    "ClienteDeletado",
    "AbastecimentoRegistrado",
]
```

---

### PASSO 6: Criar Repositories (Ports)

#### src/domain/repositories/cliente_repository.py
```python
from abc import abstractmethod
from typing import Optional
from src.shared.repository import Repository
from src.domain.entities.cliente import Cliente

class ClienteRepository(Repository[Cliente]):
    """Port: Cliente Repository Interface"""

    @abstractmethod
    async def find_by_cnpj(self, cnpj: str) -> Optional[Cliente]:
        pass

    @abstractmethod
    async def find_by_webposto_id(self, webposto_id: str) -> Optional[Cliente]:
        pass
```

#### src/domain/repositories/__init__.py
```python
from .cliente_repository import ClienteRepository

__all__ = ["ClienteRepository"]
```

---

### PASSO 7: Criar Infrastructure - Config

#### src/infrastructure/config/settings.py
```python
from pydantic_settings import BaseSettings
from pydantic import Field
import os

class Settings(BaseSettings):
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")

    # webPosto API
    webposto_base_url: str = Field(default="http://web.qualityautomacao.com.br", env="WEBPOSTO_BASE_URL")
    webposto_api_key: str = Field(default="", env="WEBPOSTO_API_KEY")
    webposto_sync_interval_seconds: int = Field(default=3600, env="WEBPOSTO_SYNC_INTERVAL_SECONDS")

    # Database
    database_url: str = Field(default="postgresql://user:password@localhost:5432/webposto", env="DATABASE_URL")
    database_pool_size: int = Field(default=20, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=40, env="DATABASE_MAX_OVERFLOW")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_timeout: int = Field(default=30, env="REDIS_TIMEOUT")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")

    # API
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_workers: int = Field(default=4, env="API_WORKERS")

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

#### src/infrastructure/config/database.py
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from src.infrastructure.config.settings import settings

Base = declarative_base()

engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.debug,
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

#### src/infrastructure/config/__init__.py
```python
from .settings import settings
from .database import engine, AsyncSessionLocal, get_db

__all__ = ["settings", "engine", "AsyncSessionLocal", "get_db"]
```

---

### PASSO 8: Criar Infrastructure - webPosto Client

#### src/infrastructure/webposto/client.py
```python
import httpx
from typing import Optional, List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential
from src.shared.logger import setup_logger
from src.infrastructure.config.settings import settings

logger = setup_logger(__name__)

class WebPostoClient:
    """Adapter: webPosto REST API Client"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.webposto_api_key
        self.base_url = settings.webposto_base_url
        self.timeout = httpx.Timeout(30.0, connect=5.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        url = f"{self.base_url}{endpoint}"
        params = kwargs.pop("params", {})
        params["CHAVE"] = self.api_key

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(method, url, params=params, **kwargs)
            response.raise_for_status()
            logger.info(f"Request successful", method=method, endpoint=endpoint, status=response.status_code)
            return response.json()

    async def get_clientes(self, skip: int = 0, limit: int = 100) -> List[Dict]:
        """GET /api/v1/clientes"""
        return await self._request("GET", "/api/v1/clientes", params={"skip": skip, "limit": limit})

    async def get_cliente(self, cliente_id: str) -> Dict:
        """GET /api/v1/clientes/{id}"""
        return await self._request("GET", f"/api/v1/clientes/{cliente_id}")

    async def get_produtos(self) -> List[Dict]:
        """GET /api/v1/produtos"""
        return await self._request("GET", "/api/v1/produtos")

    async def get_abastecimentos(self, skip: int = 0, limit: int = 100) -> List[Dict]:
        """GET /api/v1/abastecimentos"""
        return await self._request("GET", "/api/v1/abastecimentos", params={"skip": skip, "limit": limit})

    async def get_financeiro(self) -> List[Dict]:
        """GET /api/v1/financeiro/titulos-receber"""
        return await self._request("GET", "/api/v1/financeiro/titulos-receber")

    async def get_caixa(self) -> List[Dict]:
        """GET /api/v1/caixa/fechamentos"""
        return await self._request("GET", "/api/v1/caixa/fechamentos")

    # POST methods (para Fase 2)
    async def criar_cliente(self, dados: Dict) -> Dict:
        """POST /api/v1/clientes"""
        return await self._request("POST", "/api/v1/clientes", json=dados)

    # PUT methods (para Fase 2)
    async def atualizar_cliente(self, cliente_id: str, dados: Dict) -> Dict:
        """PUT /api/v1/clientes/{id}"""
        return await self._request("PUT", f"/api/v1/clientes/{cliente_id}", json=dados)
```

#### src/infrastructure/webposto/__init__.py
```python
from .client import WebPostoClient

__all__ = ["WebPostoClient"]
```

---

### PASSO 9: Criar Infrastructure - Repositories (Adapters)

#### src/infrastructure/repositories/models.py
```python
from sqlalchemy import Column, String, DateTime, Boolean, Numeric, Enum as SQLEnum
from sqlalchemy.orm import declarative_base
from datetime import datetime
from src.domain.entities.financeiro import TipoLancamento

Base = declarative_base()

class ClienteModel(Base):
    __tablename__ = "clientes"

    id = Column(String, primary_key=True)
    webposto_id = Column(String, unique=True, nullable=True)
    nome = Column(String, nullable=False)
    cnpj = Column(String, unique=True, nullable=False)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, nullable=True)

class AbastecimentoModel(Base):
    __tablename__ = "abastecimentos"

    id = Column(String, primary_key=True)
    cliente_id = Column(String, nullable=False)
    data = Column(DateTime, default=datetime.utcnow)
    valor = Column(Numeric(10, 2), nullable=False)
    litros = Column(Numeric(10, 2), nullable=False)
    produto_id = Column(String, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

class FinanceiroModel(Base):
    __tablename__ = "financeiro"

    id = Column(String, primary_key=True)
    tipo = Column(SQLEnum(TipoLancamento), nullable=False)
    descricao = Column(String, nullable=False)
    valor = Column(Numeric(10, 2), nullable=False)
    data_vencimento = Column(DateTime, nullable=False)
    pago = Column(Boolean, default=False)
    criado_em = Column(DateTime, default=datetime.utcnow)

class CaixaModel(Base):
    __tablename__ = "caixa"

    id = Column(String, primary_key=True)
    descricao = Column(String, nullable=False)
    saldo = Column(Numeric(10, 2), nullable=False)
    data_movimento = Column(DateTime, default=datetime.utcnow)
    criado_em = Column(DateTime, default=datetime.utcnow)
```

#### src/infrastructure/repositories/cliente_repository.py
```python
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.domain.entities.cliente import Cliente
from src.domain.repositories.cliente_repository import ClienteRepository
from src.infrastructure.repositories.models import ClienteModel
from src.shared.logger import setup_logger

logger = setup_logger(__name__)

class SQLAlchemyClienteRepository(ClienteRepository):
    """Adapter: SQLAlchemy Cliente Repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, entity: Cliente) -> Cliente:
        model = ClienteModel(
            id=entity.id,
            nome=entity.nome,
            cnpj=entity.cnpj,
            ativo=entity.ativo,
        )
        self.session.add(model)
        await self.session.commit()
        logger.info(f"Cliente saved", cliente_id=entity.id)
        return entity

    async def find_by_id(self, id: str) -> Optional[Cliente]:
        query = select(ClienteModel).where(ClienteModel.id == id)
        result = await self.session.execute(query)
        model = result.scalar()
        if model:
            return self._model_to_entity(model)
        return None

    async def find_all(self, skip: int = 0, limit: int = 100) -> List[Cliente]:
        query = select(ClienteModel).offset(skip).limit(limit)
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._model_to_entity(m) for m in models]

    async def find_by_cnpj(self, cnpj: str) -> Optional[Cliente]:
        query = select(ClienteModel).where(ClienteModel.cnpj == cnpj)
        result = await self.session.execute(query)
        model = result.scalar()
        if model:
            return self._model_to_entity(model)
        return None

    async def find_by_webposto_id(self, webposto_id: str) -> Optional[Cliente]:
        query = select(ClienteModel).where(ClienteModel.webposto_id == webposto_id)
        result = await self.session.execute(query)
        model = result.scalar()
        if model:
            return self._model_to_entity(model)
        return None

    async def update(self, entity: Cliente) -> Cliente:
        query = select(ClienteModel).where(ClienteModel.id == entity.id)
        result = await self.session.execute(query)
        model = result.scalar()
        if model:
            model.nome = entity.nome
            model.ativo = entity.ativo
            model.atualizado_em = entity.atualizado_em
            await self.session.commit()
            logger.info(f"Cliente updated", cliente_id=entity.id)
        return entity

    async def delete(self, id: str) -> bool:
        query = select(ClienteModel).where(ClienteModel.id == id)
        result = await self.session.execute(query)
        model = result.scalar()
        if model:
            await self.session.delete(model)
            await self.session.commit()
            logger.info(f"Cliente deleted", cliente_id=id)
            return True
        return False

    @staticmethod
    def _model_to_entity(model: ClienteModel) -> Cliente:
        entity = Cliente()
        entity.id = model.id
        entity.nome = model.nome
        entity.cnpj = model.cnpj
        entity.ativo = model.ativo
        entity.criado_em = model.criado_em
        entity.atualizado_em = model.atualizado_em
        return entity
```

#### src/infrastructure/repositories/__init__.py
```python
from .cliente_repository import SQLAlchemyClienteRepository

__all__ = ["SQLAlchemyClienteRepository"]
```

---

### PASSO 10: Criar Infrastructure - Event Bus

#### src/infrastructure/event_bus/redis_event_bus.py
```python
import json
import redis.asyncio as redis
from src.shared.domain_event import DomainEvent
from src.shared.logger import setup_logger
from src.infrastructure.config.settings import settings
from typing import Callable, List

logger = setup_logger(__name__)

class RedisEventBus:
    """Adapter: Redis Event Bus"""

    def __init__(self):
        self.redis = None
        self.handlers: dict = {}

    async def connect(self):
        self.redis = await redis.from_url(settings.redis_url)
        logger.info("Connected to Redis Event Bus")

    async def disconnect(self):
        if self.redis:
            await self.redis.close()
            logger.info("Disconnected from Redis Event Bus")

    async def publish(self, event: DomainEvent) -> None:
        """Publish event to Redis Pub/Sub"""
        event_data = {
            "event_name": event.event_name,
            "event_id": str(event.event_id),
            "aggregate_id": event.aggregate_id,
            "timestamp": event.timestamp.isoformat(),
            "data": event.__dict__,
        }
        channel = f"events:{event.event_name}"
        await self.redis.publish(channel, json.dumps(event_data))
        logger.info(f"Event published", event_name=event.event_name, channel=channel)

    async def subscribe(self, event_name: str, handler: Callable) -> None:
        """Subscribe to event"""
        channel = f"events:{event_name}"
        if channel not in self.handlers:
            self.handlers[channel] = []
        self.handlers[channel].append(handler)
        logger.info(f"Handler subscribed", event_name=event_name)

    async def listen(self) -> None:
        """Listen for events (long-running)"""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(*self.handlers.keys())
        async for message in pubsub.listen():
            if message["type"] == "message":
                event_data = json.loads(message["data"])
                handlers = self.handlers.get(message["channel"].decode(), [])
                for handler in handlers:
                    await handler(event_data)
```

#### src/infrastructure/event_bus/__init__.py
```python
from .redis_event_bus import RedisEventBus

__all__ = ["RedisEventBus"]
```

---

### PASSO 11: Criar Application Services

#### src/application/dto/cliente_dto.py
```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ClienteCreateDTO(BaseModel):
    nome: str = Field(..., min_length=1)
    cnpj: str = Field(..., regex=r"^\d{14}$")

class ClienteUpdateDTO(BaseModel):
    nome: Optional[str] = None
    ativo: Optional[bool] = None

class ClienteResponseDTO(BaseModel):
    id: str
    nome: str
    cnpj: str
    ativo: bool
    criado_em: datetime
    atualizado_em: Optional[datetime]

    class Config:
        from_attributes = True
```

#### src/application/services/cliente_service.py
```python
from typing import List, Optional
from src.domain.entities.cliente import Cliente
from src.domain.repositories.cliente_repository import ClienteRepository
from src.infrastructure.event_bus.redis_event_bus import RedisEventBus
from src.application.dto.cliente_dto import ClienteCreateDTO, ClienteUpdateDTO, ClienteResponseDTO
from src.shared.logger import setup_logger

logger = setup_logger(__name__)

class ClienteService:
    """Application Service: Cliente"""

    def __init__(self, repository: ClienteRepository, event_bus: RedisEventBus):
        self.repository = repository
        self.event_bus = event_bus

    async def criar_cliente(self, dto: ClienteCreateDTO) -> ClienteResponseDTO:
        """Create new cliente"""
        cliente = Cliente()
        cliente.adicionar(dto.nome, dto.cnpj)

        # Save to database
        await self.repository.save(cliente)

        # Publish events
        for event in cliente.events:
            await self.event_bus.publish(event)

        cliente.limpar_eventos()
        logger.info(f"Cliente created", cliente_id=cliente.id)
        return ClienteResponseDTO.from_orm(cliente)

    async def obter_cliente(self, cliente_id: str) -> Optional[ClienteResponseDTO]:
        """Get cliente by ID"""
        cliente = await self.repository.find_by_id(cliente_id)
        if cliente:
            return ClienteResponseDTO.from_orm(cliente)
        return None

    async def listar_clientes(self, skip: int = 0, limit: int = 100) -> List[ClienteResponseDTO]:
        """List all clientes"""
        clientes = await self.repository.find_all(skip, limit)
        return [ClienteResponseDTO.from_orm(c) for c in clientes]

    async def atualizar_cliente(self, cliente_id: str, dto: ClienteUpdateDTO) -> Optional[ClienteResponseDTO]:
        """Update cliente"""
        cliente = await self.repository.find_by_id(cliente_id)
        if not cliente:
            return None

        cliente.atualizar(dto.nome, dto.ativo)
        await self.repository.update(cliente)

        # Publish events
        for event in cliente.events:
            await self.event_bus.publish(event)

        cliente.limpar_eventos()
        logger.info(f"Cliente updated", cliente_id=cliente_id)
        return ClienteResponseDTO.from_orm(cliente)

class SyncService:
    """Application Service: Synchronization with webPosto"""

    def __init__(self, webposto_client, cliente_service: ClienteService):
        self.webposto_client = webposto_client
        self.cliente_service = cliente_service

    async def sync_clientes(self) -> int:
        """Sync clientes from webPosto"""
        try:
            clientes_webposto = await self.webposto_client.get_clientes()
            for cliente_data in clientes_webposto:
                # Check if already exists
                existing = await self.cliente_service.repository.find_by_webposto_id(cliente_data.get("id"))
                if not existing:
                    # Create new cliente
                    dto = ClienteCreateDTO(
                        nome=cliente_data.get("nome"),
                        cnpj=cliente_data.get("cnpj")
                    )
                    await self.cliente_service.criar_cliente(dto)

            logger.info(f"Sync completed", total_clientes=len(clientes_webposto))
            return len(clientes_webposto)
        except Exception as e:
            logger.error(f"Sync failed", error=str(e))
            raise
```

#### src/application/services/__init__.py
```python
from .cliente_service import ClienteService, SyncService

__all__ = ["ClienteService", "SyncService"]
```

---

### PASSO 12: Criar HTTP Interfaces (FastAPI)

#### src/interfaces/http/dependencies.py
```python
from fastapi import Depends
from src.infrastructure.config.database import get_db
from src.infrastructure.repositories import SQLAlchemyClienteRepository
from src.infrastructure.event_bus import RedisEventBus
from src.infrastructure.webposto import WebPostoClient
from src.application.services import ClienteService, SyncService

async def get_cliente_repository(session = Depends(get_db)):
    return SQLAlchemyClienteRepository(session)

async def get_event_bus():
    return RedisEventBus()

async def get_webposto_client():
    return WebPostoClient()

async def get_cliente_service(
    repository = Depends(get_cliente_repository),
    event_bus = Depends(get_event_bus)
):
    return ClienteService(repository, event_bus)

async def get_sync_service(
    cliente_service = Depends(get_cliente_service),
    webposto_client = Depends(get_webposto_client)
):
    return SyncService(webposto_client, cliente_service)
```

#### src/interfaces/http/routes/clientes.py
```python
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from src.application.dto.cliente_dto import ClienteCreateDTO, ClienteUpdateDTO, ClienteResponseDTO
from src.application.services.cliente_service import ClienteService
from src.interfaces.http.dependencies import get_cliente_service
from src.shared.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter(prefix="/clientes", tags=["clientes"])

@router.post("", response_model=ClienteResponseDTO, status_code=201)
async def criar_cliente(
    dto: ClienteCreateDTO,
    service: ClienteService = Depends(get_cliente_service)
):
    """Create new cliente"""
    return await service.criar_cliente(dto)

@router.get("/{cliente_id}", response_model=ClienteResponseDTO)
async def obter_cliente(
    cliente_id: str,
    service: ClienteService = Depends(get_cliente_service)
):
    """Get cliente by ID"""
    cliente = await service.obter_cliente(cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente not found")
    return cliente

@router.get("", response_model=List[ClienteResponseDTO])
async def listar_clientes(
    skip: int = 0,
    limit: int = 100,
    service: ClienteService = Depends(get_cliente_service)
):
    """List all clientes"""
    return await service.listar_clientes(skip, limit)

@router.put("/{cliente_id}", response_model=ClienteResponseDTO)
async def atualizar_cliente(
    cliente_id: str,
    dto: ClienteUpdateDTO,
    service: ClienteService = Depends(get_cliente_service)
):
    """Update cliente"""
    cliente = await service.atualizar_cliente(cliente_id, dto)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente not found")
    return cliente

@router.delete("/{cliente_id}", status_code=204)
async def deletar_cliente(
    cliente_id: str,
    service: ClienteService = Depends(get_cliente_service)
):
    """Delete cliente"""
    success = await service.repository.delete(cliente_id)
    if not success:
        raise HTTPException(status_code=404, detail="Cliente not found")
```

#### src/interfaces/http/routes/health.py
```python
from fastapi import APIRouter

router = APIRouter(tags=["health"])

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}
```

#### src/interfaces/http/routes/__init__.py
```python
from .clientes import router as clientes_router
from .health import router as health_router

__all__ = ["clientes_router", "health_router"]
```

#### src/interfaces/http/app.py
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.interfaces.http.routes import clientes_router, health_router
from src.infrastructure.config.settings import settings

def create_app() -> FastAPI:
    app = FastAPI(
        title="webPosto Service",
        description="API Integration Service for webPosto",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(health_router)
    app.include_router(clientes_router)

    return app
```

#### src/interfaces/http/__init__.py
```python
from .app import create_app

__all__ = ["create_app"]
```

---

### PASSO 13: Criar Main Entry Point

#### src/main.py
```python
import uvicorn
import asyncio
from src.interfaces.http.app import create_app
from src.infrastructure.config.settings import settings
from src.shared.logger import setup_logger

logger = setup_logger(__name__)

app = create_app()

@app.on_event("startup")
async def startup():
    logger.info("Application starting up")

@app.on_event("shutdown")
async def shutdown():
    logger.info("Application shutting down")

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers if settings.environment == "production" else 1,
        reload=settings.debug,
    )
```

---

### PASSO 14: Criar Testes

#### tests/conftest.py
```python
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.infrastructure.repositories.models import Base

@pytest.fixture
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with AsyncSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
```

#### tests/unit/domain/test_cliente.py
```python
import pytest
from src.domain.entities.cliente import Cliente
from src.domain.events.cliente_events import ClienteAdicionado, ClienteAtualizado

@pytest.mark.asyncio
async def test_criar_cliente():
    cliente = Cliente()
    cliente.adicionar("Test Cliente", "12345678901234")

    assert cliente.nome == "Test Cliente"
    assert cliente.cnpj == "12345678901234"
    assert len(cliente.events) == 1
    assert isinstance(cliente.events[0], ClienteAdicionado)

@pytest.mark.asyncio
async def test_atualizar_cliente():
    cliente = Cliente()
    cliente.adicionar("Test", "12345678901234")
    cliente.atualizar(nome="Updated")

    assert cliente.nome == "Updated"
    assert len(cliente.events) == 2
    assert isinstance(cliente.events[1], ClienteAtualizado)
```

#### tests/unit/application/test_cliente_service.py
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.application.services.cliente_service import ClienteService
from src.application.dto.cliente_dto import ClienteCreateDTO

@pytest.mark.asyncio
async def test_criar_cliente_service():
    # Mocks
    repository = AsyncMock()
    event_bus = AsyncMock()

    service = ClienteService(repository, event_bus)

    dto = ClienteCreateDTO(nome="Test", cnpj="12345678901234")
    result = await service.criar_cliente(dto)

    assert result.nome == "Test"
    repository.save.assert_called_once()
    event_bus.publish.assert_called_once()
```

---

### PASSO 15: Criar Docker Files

#### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock* ./

RUN pip install --no-cache-dir poetry && poetry config virtualenvs.create false && poetry install --no-dev

COPY . .

CMD ["python", "-m", "src.main"]
```

#### docker-compose.yml
```yaml
version: "3.9"

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: webposto
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    build: .
    environment:
      DATABASE_URL: postgresql+asyncpg://user:password@postgres:5432/webposto
      REDIS_URL: redis://redis:6379/0
      WEBPOSTO_API_KEY: ${WEBPOSTO_API_KEY}
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - .:/app

volumes:
  postgres_data:
  redis_data:
```

---

### PASSO 16: Criar Arquivos de Configuração

#### .env.example
```env
# Ambiente
ENVIRONMENT=development
DEBUG=true

# webPosto API
WEBPOSTO_BASE_URL=http://web.qualityautomacao.com.br
WEBPOSTO_API_KEY=<sua chave aqui>
WEBPOSTO_SYNC_INTERVAL_SECONDS=3600

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/webposto
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_TIMEOUT=30

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60
```

#### pytest.ini
```ini
[pytest]
testpaths = tests
python_files = test_*.py
asyncio_mode = auto
addopts = --cov=src --cov-report=html --cov-report=term-missing
```

#### Makefile
```makefile
.PHONY: help install test lint format run docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  make install       - Install dependencies"
	@echo "  make test          - Run tests"
	@echo "  make lint          - Run linters"
	@echo "  make format        - Format code"
	@echo "  make run           - Run application"
	@echo "  make docker-up     - Start Docker containers"
	@echo "  make docker-down   - Stop Docker containers"

install:
	poetry install

test:
	pytest --cov=src

lint:
	black --check src tests
	isort --check-only src tests
	flake8 src tests
	mypy src

format:
	black src tests
	isort src tests

run:
	python -m src.main

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down
```

---

### PASSO 17: Criar GitHub Actions

#### .github/workflows/test.yml
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_DB: webposto
          POSTGRES_USER: user
          POSTGRES_PASSWORD: password
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: 3.11

      - name: Install dependencies
        run: |
          pip install poetry
          poetry install

      - name: Run tests
        run: poetry run pytest --cov=src

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

#### .github/workflows/lint.yml
```yaml
name: Lint

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: 3.11

      - name: Install dependencies
        run: |
          pip install poetry
          poetry install

      - name: Run black
        run: poetry run black --check src tests

      - name: Run isort
        run: poetry run isort --check-only src tests

      - name: Run flake8
        run: poetry run flake8 src tests

      - name: Run mypy
        run: poetry run mypy src
```

---

### PASSO 18: Criar README.md

#### README.md
```markdown
# webPosto Service

API Integration Service para webPosto - Arquitetura Hexagonal + Event-Driven

## Features

- ✅ Integração com webPosto REST API
- ✅ Sincronização de dados (Clientes, Produtos, Abastecimentos, Financeiro, Caixa, etc)
- ✅ Event Bus com Redis Pub/Sub
- ✅ API REST com FastAPI
- ✅ Testes com 100% coverage
- ✅ Docker ready
- ✅ CI/CD com GitHub Actions

## Arquitetura

Hexagonal Architecture (Ports & Adapters) + Event-Driven:
- **Domain Layer:** Lógica de negócio pura
- **Application Layer:** Use cases e services
- **Infrastructure Layer:** Adaptadores (DB, API, Event Bus)
- **Interfaces Layer:** HTTP REST, CLI

## Setup Local

```bash
# Clone
git clone <repo>
cd webposto-service

# Instalar dependências
make install

# Criar .env
cp .env.example .env
# Editar .env com sua WEBPOSTO_API_KEY

# Rodar Docker
make docker-up

# Rodar migrations
alembic upgrade head

# Rodar
make run
```

## Testes

```bash
# Rodar todos os testes
make test

# Com coverage
pytest --cov=src --cov-report=html
```

## API Docs

Swagger: http://localhost:8000/docs
ReDoc: http://localhost:8000/redoc

## Estrutura

```
src/
├── domain/          # Lógica de negócio
├── application/     # Services & DTOs
├── infrastructure/  # Adaptadores
├── interfaces/      # HTTP, CLI
└── shared/          # Utilities

tests/
├── unit/
├── integration/
└── e2e/
```

## Próximas Fases

- Fase 1: Leitura (GET) ✅
- Fase 2: Criação/Atualização (POST/PUT)
- Fase 3: Sincronização em tempo real
- Fase 4: Microservices

## Licença

MIT
```

---

## ✅ RESUMO - VOCÊ PRECISA FAZER:

1. ✅ Copiar TUDO acima
2. ✅ Colar no Cursor
3. ✅ O Cursor vai gerar a estrutura completa
4. ✅ Depois é só fazer `poetry install` e `docker-compose up`

**O sistema ficará pronto em ~30 minutos com o Cursor gerando tudo automaticamente.**

---

Pronto! Este é o prompt COMPLETO que você passa para o Cursor.
