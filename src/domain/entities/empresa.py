"""
Domain Module: Empresa Aggregate Root

Implementa o modelo de domínio para empresas multi-tenant com centros de custo
e sincronização de dados usando Domain-Driven Design (DDD).

Componentes principais:
1. Agregado Empresa (AggregateRoot)
2. Value Objects (EmpresaID, CentroCustoID, ValorMonetario, etc)
3. Entities (CentroCusto, Rateio)
4. Domain Events (EmpresaCriadaEvent, CentroCustoAdicionadoEvent, etc)
5. Domain Service (ValidadorRateio)
6. Factory Pattern (SincronizacaoFactory)
"""

from typing import List, Optional
from datetime import datetime, timezone
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator
from pydantic import ConfigDict
from typing import ClassVar
import uuid


# ===== DOMAIN EXCEPTIONS =====

class DomainException(Exception):
    """Exceção para violações de invariantes de domínio."""
    pass


# ===== VALUE OBJECTS =====

class EmpresaID(BaseModel):
    """Value Object para ID da Empresa."""
    valor: str = Field(..., min_length=1, max_length=50)


class CentroCustoID(BaseModel):
    """Value Object para ID do Centro de Custo."""
    valor: str = Field(..., min_length=1, max_length=50)


class RateioID(BaseModel):
    """Value Object para ID do Rateio."""
    valor: str = Field(default_factory=lambda: str(uuid.uuid4()))


class ValorMonetario(BaseModel):
    """Value Object para valores monetários com precisão."""
    valor: Decimal = Field(..., decimal_places=2)
    moeda: str = "BRL"
    model_config: ClassVar = ConfigDict(frozen=True)

    @field_validator('valor')
    def validar_valor(cls, v):
        if v < 0:
            raise ValueError("Valor não pode ser negativo")
        return v


class RateioCentroCusto(BaseModel):
    """Value Object para composição de rateio de um centro de custo."""
    centro_custo_id: CentroCustoID
    percentual: Decimal = Field(..., ge=0, le=100, decimal_places=2)
    valor: ValorMonetario


# ===== DOMAIN EVENTS BASE CLASS =====

class DomainEvent(BaseModel):
    """Classe base para eventos de domínio."""
    evento_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str = "domain_event"
    
    model_config: ClassVar = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


# ===== DOMAIN EVENTS =====

class SyncStartedEvent(DomainEvent):
    """Evento: Sincronização iniciada."""
    empresa_id: str
    timestamp_inicio: datetime
    event_type: str = "sync_started"


class DivergenciaCCDetectadaEvent(DomainEvent):
    """Evento: Divergência de centro de custo detectada."""
    empresa_id: str
    lancamento_id: str
    valor_esperado: Decimal
    valor_encontrado: Decimal
    event_type: str = "divergencia_cc_detectada"


class EmpresaCriadaEvent(DomainEvent):
    """Evento: Empresa criada."""
    empresa_id: str
    nome: str = ""
    event_type: str = "empresa_criada"


class CentroCustoAdicionadoEvent(DomainEvent):
    """Evento: Centro de Custo adicionado."""
    empresa_id: str
    cc_id: str
    event_type: str = "centro_custo_adicionado"


class RateioCriadoEvent(DomainEvent):
    """Evento: Rateio criado."""
    empresa_id: str
    rateio_id: str
    lancamento_id: str
    event_type: str = "rateio_criado"


class SincronizacaoConcluidaEvent(DomainEvent):
    """Evento: Sincronização concluída."""
    empresa_id: str
    total_rateios_criados: int
    total_divergencias_detectadas: int
    event_type: str = "sincronizacao_concluida"


# ===== CONFIGURATION =====

class RateiConfiguracao(BaseModel):
    """Configuração de rateio customizada por empresa."""
    empresa_id: str
    tipo_rateio: str = "proporcional"
    validar_soma_100: bool = True
    permitir_centros_ausentes: bool = False
    timestamp_criacao: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ===== ENTITIES =====

class CentroCusto(BaseModel):
    """
    Entity: Centro de Custo.
    Pertence ao Agregado Empresa.
    """
    centro_custo_id: CentroCustoID
    nome: str = Field(..., min_length=1, max_length=100)
    percentual_padrao: Decimal = Field(..., ge=0, le=100, decimal_places=2)
    ativo: bool = True
    timestamp_criacao: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def validar(self) -> bool:
        """Validar integridade do Centro de Custo."""
        if not 0 <= self.percentual_padrao <= 100:
            raise DomainException(f"Percentual inválido: {self.percentual_padrao}")
        if not self.nome.strip():
            raise DomainException("Nome do CC não pode ser vazio")
        return True


class Rateio(BaseModel):
    """
    Entity: Rateio de um Lançamento.
    Pertence ao Agregado Empresa.
    """
    rateio_id: RateioID = Field(default_factory=RateioID)
    lancamento_id: str
    centros_custo: List[RateioCentroCusto]
    valor_total: ValorMonetario
    timestamp_criacao: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def validar_soma(self) -> bool:
        """Validar se soma de rateios = valor_total."""
        if not self.centros_custo:
            raise DomainException("Rateio deve ter pelo menos um centro de custo")
        
        soma_valores = sum(Decimal(str(r.valor.valor)) for r in self.centros_custo)
        valor_total = Decimal(str(self.valor_total.valor))
        
        if abs(soma_valores - valor_total) > Decimal('0.01'):
            raise DomainException(
                f"Soma de rateios ({soma_valores}) ≠ valor_total ({valor_total})"
            )
        return True
    
    def validar_percentuais(self) -> bool:
        """Validar se soma de percentuais = 100%."""
        soma_percentuais = sum(Decimal(str(r.percentual)) for r in self.centros_custo)
        
        if abs(soma_percentuais - Decimal('100')) > Decimal('0.01'):
            raise DomainException(
                f"Soma de percentuais ({soma_percentuais}) ≠ 100%"
            )
        return True


# ===== AGGREGATE ROOT =====

class Empresa(BaseModel):
    """
    Aggregate Root: Empresa.
    
    Representa uma empresa (tenant) com seus centros de custo e lógica de rateio.
    """
    empresa_id: EmpresaID
    nome: str = Field(..., min_length=1, max_length=100)
    centros_custo: List[CentroCusto] = Field(default_factory=list)
    config_rateio: RateiConfiguracao
    rateios: List[Rateio] = Field(default_factory=list)
    eventos_nao_commitados: List[DomainEvent] = Field(default_factory=list)
    timestamp_criacao: datetime = Field(default_factory=datetime.utcnow)
    
    model_config: ClassVar = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
    
    def model_post_init(self, __context):
        """Emitir evento de criação após inicialização."""
        if not self.eventos_nao_commitados:
            self._emit_event(EmpresaCriadaEvent(
                empresa_id=self.empresa_id.valor,
                nome=self.nome
            ))
    
    def adicionar_centro_custo(self, cc: CentroCusto) -> None:
        """Adicionar novo Centro de Custo ao Agregado."""
        if any(c.centro_custo_id.valor == cc.centro_custo_id.valor 
               for c in self.centros_custo):
            raise DomainException(
                f"Centro de Custo '{cc.centro_custo_id.valor}' já existe"
            )
        
        cc.validar()
        self.centros_custo.append(cc)
        
        self._emit_event(CentroCustoAdicionadoEvent(
            empresa_id=self.empresa_id.valor,
            cc_id=cc.centro_custo_id.valor
        ))
    
    def remover_centro_custo(self, cc_id: str) -> None:
        """Remover Centro de Custo do Agregado."""
        inicial_count = len(self.centros_custo)
        self.centros_custo = [
            c for c in self.centros_custo 
            if c.centro_custo_id.valor != cc_id
        ]
        
        if len(self.centros_custo) == inicial_count:
            raise DomainException(f"Centro de Custo '{cc_id}' não encontrado")
    
    def criar_rateio(self, lancamento_id: str, dados_rateio: dict) -> Rateio:
        """Criar novo Rateio dentro do Agregado."""
        centros_rateio = []
        for cc_data in dados_rateio.get('centros_custo', []):
            cc_rateio = RateioCentroCusto(
                centro_custo_id=CentroCustoID(valor=cc_data['cc_id']),
                percentual=Decimal(str(cc_data['percentual'])),
                valor=ValorMonetario(
                    valor=Decimal(str(cc_data['valor'])),
                    moeda=cc_data.get('moeda', 'BRL')
                )
            )
            centros_rateio.append(cc_rateio)
        
        rateio = Rateio(
            lancamento_id=lancamento_id,
            centros_custo=centros_rateio,
            valor_total=ValorMonetario(
                valor=Decimal(str(dados_rateio['valor_total'])),
                moeda=dados_rateio.get('moeda', 'BRL')
            )
        )
        
        rateio.validar_soma()
        rateio.validar_percentuais()
        
        self.rateios.append(rateio)
        
        self._emit_event(RateioCriadoEvent(
            empresa_id=self.empresa_id.valor,
            rateio_id=rateio.rateio_id.valor,
            lancamento_id=lancamento_id
        ))
        
        return rateio
    
    def sincronizar(self, dados_lancamentos: List[dict]) -> dict:
        """Orquestrar sincronização de lançamentos."""
        divergencias_detectadas = []
        rateios_criados = 0
        erros = []
        
        self._emit_event(SyncStartedEvent(
            empresa_id=self.empresa_id.valor,
            timestamp_inicio=datetime.utcnow()
        ))
        
        for lancamento in dados_lancamentos:
            try:
                rateio = self.criar_rateio(
                    lancamento_id=lancamento['id'],
                    dados_rateio=lancamento
                )
                rateios_criados += 1
                
            except DomainException as e:
                divergencias_detectadas.append({
                    'lancamento_id': lancamento.get('id'),
                    'erro': str(e)
                })
                erros.append(str(e))
        
        self._emit_event(SincronizacaoConcluidaEvent(
            empresa_id=self.empresa_id.valor,
            total_rateios_criados=rateios_criados,
            total_divergencias_detectadas=len(divergencias_detectadas)
        ))
        
        return {
            'empresa_id': self.empresa_id.valor,
            'rateios_criados': rateios_criados,
            'divergencias_detectadas': divergencias_detectadas,
            'total_erros': len(erros),
            'sucesso': len(erros) == 0
        }
    
    def obter_centros_custo_ativos(self) -> List[CentroCusto]:
        """Obter todos os CCs ativos."""
        return [cc for cc in self.centros_custo if cc.ativo]
    
    def validar_invariantes(self) -> bool:
        """Validar invariantes de negócio do agregado."""
        if not self.nome.strip():
            raise DomainException("Empresa deve ter nome")
        
        if not self.centros_custo:
            raise DomainException("Empresa deve ter pelo menos 1 CC")
        
        for cc in self.centros_custo:
            cc.validar()
        
        return True
    
    def obter_eventos(self) -> List[DomainEvent]:
        """Obter eventos não-commitados."""
        return self.eventos_nao_commitados.copy()
    
    def limpar_eventos(self) -> None:
        """Limpar eventos não-commitados após persistência."""
        self.eventos_nao_commitados.clear()
    
    def _emit_event(self, event: DomainEvent) -> None:
        """Adicionar evento não-commitado."""
        self.eventos_nao_commitados.append(event)


# ===== DOMAIN SERVICE (IMPORTED) =====
# ValidadorRateio é implementado em src/domain/services/validador_rateio.py


# ===== FACTORY PATTERN =====

class SincronizacaoFactory:
    """Factory: Criar instâncias de Sincronização."""
    
    @staticmethod
    def criar_empresa(empresa_id: str, nome: str, 
                     config: Optional[RateiConfiguracao] = None) -> Empresa:
        """Criar nova Empresa com configuração."""
        if config is None:
            config = RateiConfiguracao(
                empresa_id=empresa_id,
                tipo_rateio="proporcional",
                validar_soma_100=True
            )
        
        empresa = Empresa(
            empresa_id=EmpresaID(valor=empresa_id),
            nome=nome,
            config_rateio=config
        )
        
        return empresa
    
    @staticmethod
    def criar_validador(empresa: Empresa) -> 'ValidadorRateio':
        """Criar ValidadorRateio com configuração da Empresa."""
        from src.domain.services.validador_rateio import ValidadorRateio
        return ValidadorRateio(config=empresa.config_rateio)
