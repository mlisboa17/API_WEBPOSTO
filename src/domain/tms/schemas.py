"""Pydantic schemas and enums for the fuel TMS MVP."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class StatusCompartimento(str, Enum):
    VERDE = "valido"
    AMARELO = "faltando_info"
    VERMELHO = "conflito"
    CINZA = "rascunho"


class StatusViagem(str, Enum):
    RASCUNHO = "rascunho"
    PROGRAMADA = "programada"
    LIBERADA_SUAPE = "liberada_suape"
    NA_BASE = "na_base"
    CARREGADA = "carregada"
    EM_ROTA = "em_rota"
    NO_POSTO = "no_posto"
    DESCARREGANDO = "descarregando"
    ENTREGUE = "entregue"
    FINALIZADA = "finalizada"


class SeveridadeAlerta(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERRO = "erro"


class OrigemEvento(str, Enum):
    MANUAL = "manual"
    APP = "app"
    SISTEMA = "sistema"
    INTEGRACAO = "integracao"


class GeoPoint(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_metros: Optional[float] = Field(default=None, ge=0)


class Alerta(BaseModel):
    tipo: str
    mensagem: str
    severidade: SeveridadeAlerta


class Evento(BaseModel):
    status: StatusViagem
    data_hora: datetime
    usuario_id: UUID
    geo: Optional[GeoPoint] = None
    origem: OrigemEvento
    observacao: Optional[str] = None


class PostoResumo(BaseModel):
    id: UUID
    nome: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    raio_checkin_metros: int = Field(default=300, gt=0)

    @property
    def tem_geo(self) -> bool:
        return self.latitude is not None and self.longitude is not None


class TanqueResumo(BaseModel):
    id: UUID
    posto_id: UUID
    produto_id: UUID
    codigo: str
    qr_code: Optional[str] = None
    ativo: bool = True


class ProdutoResumo(BaseModel):
    id: UUID
    nome: str


class DocumentoCriticoResumo(BaseModel):
    tipo: str
    valido: bool
    vence_em_dias: Optional[int] = None


class EntregaResumo(BaseModel):
    id: UUID
    posto_id: UUID
    rota_index: int = Field(ge=0)
    status: StatusViagem = StatusViagem.PROGRAMADA


class CompartimentoProgramacao(BaseModel):
    id: UUID
    numero: int = Field(ge=1, le=5)
    volume_litros: float = Field(default=5000, ge=0)
    produto_id: Optional[UUID] = None
    posto_id: Optional[UUID] = None
    tanque_id: Optional[UUID] = None
    pedido_id: Optional[UUID] = None
    entrega_id: Optional[UUID] = None
    lacre: Optional[str] = None
    qr_code: Optional[str] = None
    excecao_vazio_autorizada: bool = False

    @property
    def esta_vazio(self) -> bool:
        return self.produto_id is None and self.posto_id is None and self.tanque_id is None


class ProgramacaoInput(BaseModel):
    id: Optional[UUID] = None
    veiculo_id: Optional[UUID] = None
    motorista_id: Optional[UUID] = None
    janela_suape: Optional[datetime] = None
    protocolo_suape: Optional[str] = None
    compartimentos: list[CompartimentoProgramacao] = Field(default_factory=list)
    postos: list[PostoResumo] = Field(default_factory=list)
    tanques: list[TanqueResumo] = Field(default_factory=list)
    documentos_criticos: list[DocumentoCriticoResumo] = Field(default_factory=list)
    pedidos_criticos_pendentes: int = 0
    ordem_definida: bool = False
    nfe_vinculada: bool = False

    @field_validator("compartimentos")
    @classmethod
    def validar_quantidade_compartimentos(
        cls, value: list[CompartimentoProgramacao]
    ) -> list[CompartimentoProgramacao]:
        if len(value) > 5:
            raise ValueError("A programacao aceita no maximo 5 compartimentos")
        return value


class ResultadoValidacaoProgramacao(BaseModel):
    erros: list[str]
    alertas: list[str]
    status_compartimentos: dict[UUID, StatusCompartimento]
    alertas_laterais: list[Alerta]


class OrdemDescarga(BaseModel):
    viagem_id: UUID
    ordem: list[UUID]
    manual: bool


class SugerirOrdemDescargaInput(BaseModel):
    viagem_id: UUID
    entregas: list[EntregaResumo]


class ValidarExecucaoOrdemInput(BaseModel):
    ordem: OrdemDescarga
    entrega_atual: UUID
    autorizado_por: Optional[UUID] = None
    justificativa: Optional[str] = None


class NFE(BaseModel):
    numero: str
    posto_cnpj: str
    produto: str
    volume: float = Field(ge=0)
    transportador: Optional[str] = None
    placa: Optional[str] = None
    viagem_id: Optional[UUID] = None
    produto_programado: Optional[str] = None
    volume_programado: Optional[float] = None
    transportador_esperado: Optional[str] = None


class NFEAuditoriaResultado(BaseModel):
    alertas: list[Alerta]


class MobileEventoInput(BaseModel):
    viagem_id: UUID
    usuario_id: UUID
    geo: Optional[GeoPoint] = None
    observacao: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)


class DescargaIniciarInput(MobileEventoInput):
    entrega_id: UUID
    compartimento_qr: str
    tanque_qr: str
    lacre: str
    produto_compartimento_id: UUID
    produto_tanque_id: UUID
    ordem: OrdemDescarga


class DescargaFinalizarInput(MobileEventoInput):
    entrega_id: UUID
    posto_id: UUID
    tanque_id: UUID
    produto_id: UUID
    compartimento_id: UUID
    volume_programado_litros: float = Field(ge=0)
    volume_descargado_litros: float = Field(ge=0)
    estoque_pos_descarga_litros: float = Field(ge=0)
    foto_veeder_root_url: str


class MobileEventoResultado(BaseModel):
    status: StatusViagem
    evento: Evento
    bloqueado: bool = False
    requer_autorizacao: bool = False
    alertas: list[Alerta] = Field(default_factory=list)
