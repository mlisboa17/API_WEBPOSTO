"""SQLAlchemy models for the fuel TMS MVP."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.infrastructure.persistence.postgresql.models import Base


class TMSStatusViagem(str, enum.Enum):
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


class TMSUsuarioORM(Base):
    __tablename__ = "tms_usuarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    perfil = Column(String(50), nullable=False, index=True)
    posto_id = Column(UUID(as_uuid=True), ForeignKey("tms_postos.id"), nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class TMSPostoORM(Base):
    __tablename__ = "tms_postos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String(255), nullable=False, index=True)
    cnpj = Column(String(20), nullable=False, unique=True, index=True)
    razao_social = Column(String(255), nullable=True)
    nome_fantasia = Column(String(255), nullable=True)
    codigo_interno = Column(String(50), nullable=True, index=True)
    endereco = Column(Text, nullable=True)
    cidade = Column(String(120), nullable=True)
    uf = Column(String(2), nullable=False, default="PE")
    bairro = Column(String(120), nullable=True)
    cep = Column(String(20), nullable=True)
    latitude = Column(Numeric(10, 7), nullable=True)
    longitude = Column(Numeric(10, 7), nullable=True)
    raio_checkin_metros = Column(Integer, nullable=False, default=300)
    responsavel_principal = Column(String(255), nullable=True)
    telefone_whatsapp = Column(String(30), nullable=True)
    observacoes = Column(Text, nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tanques = relationship("TMSTanqueORM", back_populates="posto")

    __table_args__ = (
        Index("ix_tms_postos_geo", "latitude", "longitude"),
    )


class TMSProdutoORM(Base):
    __tablename__ = "tms_produtos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String(120), nullable=False, unique=True)
    codigo = Column(String(50), nullable=True, index=True)
    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)


class TMSTanqueORM(Base):
    __tablename__ = "tms_tanques"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    posto_id = Column(UUID(as_uuid=True), ForeignKey("tms_postos.id"), nullable=False, index=True)
    produto_id = Column(UUID(as_uuid=True), ForeignKey("tms_produtos.id"), nullable=False, index=True)
    codigo = Column(String(80), nullable=False)
    capacidade_litros = Column(Numeric(12, 2), nullable=True)
    qr_code = Column(String(255), nullable=False, unique=True)
    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    posto = relationship("TMSPostoORM", back_populates="tanques")
    produto = relationship("TMSProdutoORM")

    __table_args__ = (
        Index("ix_tms_tanques_posto_codigo", "posto_id", "codigo", unique=True),
    )


class TMSBaseOperacionalORM(Base):
    __tablename__ = "tms_bases_operacionais"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String(255), nullable=False)
    tipo = Column(String(50), nullable=False, index=True)
    latitude = Column(Numeric(10, 7), nullable=True)
    longitude = Column(Numeric(10, 7), nullable=True)
    raio_checkin_metros = Column(Integer, nullable=False, default=300)
    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)


class TMSCaminhaoORM(Base):
    __tablename__ = "tms_caminhoes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    placa = Column(String(20), nullable=False, unique=True, index=True)
    nome = Column(String(120), nullable=True)
    capacidade_total_litros = Column(Numeric(12, 2), nullable=False, default=25000)
    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    compartimentos = relationship("TMSCompartimentoORM", back_populates="caminhao")


class TMSCompartimentoORM(Base):
    __tablename__ = "tms_compartimentos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    caminhao_id = Column(UUID(as_uuid=True), ForeignKey("tms_caminhoes.id"), nullable=False, index=True)
    numero = Column(Integer, nullable=False)
    capacidade_litros = Column(Numeric(12, 2), nullable=False, default=5000)
    posicao_fisica = Column(String(80), nullable=True)
    qr_code = Column(String(255), nullable=False, unique=True)
    ultimo_produto_id = Column(UUID(as_uuid=True), ForeignKey("tms_produtos.id"), nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)

    caminhao = relationship("TMSCaminhaoORM", back_populates="compartimentos")
    ultimo_produto = relationship("TMSProdutoORM")

    __table_args__ = (
        Index("ix_tms_compartimentos_caminhao_numero", "caminhao_id", "numero", unique=True),
    )


class TMSMotoristaORM(Base):
    __tablename__ = "tms_motoristas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String(255), nullable=False)
    cpf = Column(String(20), nullable=True, unique=True)
    cnh = Column(String(50), nullable=True)
    cnh_validade = Column(DateTime, nullable=True)
    mopp_validade = Column(DateTime, nullable=True)
    aso_validade = Column(DateTime, nullable=True)
    caminhao_habitual_id = Column(UUID(as_uuid=True), ForeignKey("tms_caminhoes.id"), nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class TMSPoliticaORM(Base):
    __tablename__ = "tms_politicas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chave = Column(String(120), nullable=False, unique=True)
    modo = Column(String(50), nullable=False)
    configuracao = Column(JSON, nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class TMSPedidoORM(Base):
    __tablename__ = "tms_pedidos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    posto_id = Column(UUID(as_uuid=True), ForeignKey("tms_postos.id"), nullable=False, index=True)
    solicitado_por_id = Column(UUID(as_uuid=True), ForeignKey("tms_usuarios.id"), nullable=True)
    data_desejada = Column(DateTime, nullable=False, index=True)
    prioridade = Column(String(30), nullable=False, default="normal", index=True)
    status = Column(String(30), nullable=False, default="solicitado", index=True)
    observacao = Column(Text, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    itens = relationship("TMSItemPedidoORM", back_populates="pedido")


class TMSItemPedidoORM(Base):
    __tablename__ = "tms_itens_pedido"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pedido_id = Column(UUID(as_uuid=True), ForeignKey("tms_pedidos.id"), nullable=False, index=True)
    produto_id = Column(UUID(as_uuid=True), ForeignKey("tms_produtos.id"), nullable=False)
    quantidade_litros = Column(Numeric(12, 2), nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)

    pedido = relationship("TMSPedidoORM", back_populates="itens")


class TMSViagemORM(Base):
    __tablename__ = "tms_viagens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    caminhao_id = Column(UUID(as_uuid=True), ForeignKey("tms_caminhoes.id"), nullable=True, index=True)
    motorista_id = Column(UUID(as_uuid=True), ForeignKey("tms_motoristas.id"), nullable=True, index=True)
    janela_suape = Column(DateTime, nullable=True, index=True)
    protocolo_suape = Column(String(120), nullable=True)
    status = Column(String(40), nullable=False, default=TMSStatusViagem.RASCUNHO.value, index=True)
    ordem_descarga = Column(JSON, nullable=True)
    ordem_manual = Column(Boolean, default=False, nullable=False)
    nfe_vinculada = Column(Boolean, default=False, nullable=False)
    criado_por_id = Column(UUID(as_uuid=True), ForeignKey("tms_usuarios.id"), nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    compartimentos = relationship("TMSCompartimentoViagemORM", back_populates="viagem")
    entregas = relationship("TMSEntregaORM", back_populates="viagem")


class TMSEntregaORM(Base):
    __tablename__ = "tms_entregas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    viagem_id = Column(UUID(as_uuid=True), ForeignKey("tms_viagens.id"), nullable=False, index=True)
    posto_id = Column(UUID(as_uuid=True), ForeignKey("tms_postos.id"), nullable=False, index=True)
    rota_index = Column(Integer, nullable=False, default=0)
    status = Column(String(40), nullable=False, default=TMSStatusViagem.PROGRAMADA.value, index=True)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)

    viagem = relationship("TMSViagemORM", back_populates="entregas")


class TMSCompartimentoViagemORM(Base):
    __tablename__ = "tms_compartimentos_viagem"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    viagem_id = Column(UUID(as_uuid=True), ForeignKey("tms_viagens.id"), nullable=False, index=True)
    compartimento_id = Column(UUID(as_uuid=True), ForeignKey("tms_compartimentos.id"), nullable=False)
    entrega_id = Column(UUID(as_uuid=True), ForeignKey("tms_entregas.id"), nullable=True)
    pedido_id = Column(UUID(as_uuid=True), ForeignKey("tms_pedidos.id"), nullable=True)
    posto_id = Column(UUID(as_uuid=True), ForeignKey("tms_postos.id"), nullable=True)
    tanque_id = Column(UUID(as_uuid=True), ForeignKey("tms_tanques.id"), nullable=True)
    produto_id = Column(UUID(as_uuid=True), ForeignKey("tms_produtos.id"), nullable=True)
    volume_litros = Column(Numeric(12, 2), nullable=False, default=5000)
    lacre = Column(String(120), nullable=True)
    ordem_descarga = Column(Integer, nullable=True)
    excecao_vazio_autorizada = Column(Boolean, default=False, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)

    viagem = relationship("TMSViagemORM", back_populates="compartimentos")

    __table_args__ = (
        Index("ix_tms_comp_viagem_compartimento", "viagem_id", "compartimento_id", unique=True),
    )


class TMSEventoViagemORM(Base):
    __tablename__ = "tms_eventos_viagem"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    viagem_id = Column(UUID(as_uuid=True), ForeignKey("tms_viagens.id"), nullable=False, index=True)
    entrega_id = Column(UUID(as_uuid=True), ForeignKey("tms_entregas.id"), nullable=True, index=True)
    status = Column(String(40), nullable=False, index=True)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("tms_usuarios.id"), nullable=True)
    latitude = Column(Numeric(10, 7), nullable=True)
    longitude = Column(Numeric(10, 7), nullable=True)
    origem = Column(String(30), nullable=False)
    observacao = Column(Text, nullable=True)
    payload = Column(JSON, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class TMSOcorrenciaORM(Base):
    __tablename__ = "tms_ocorrencias"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    viagem_id = Column(UUID(as_uuid=True), ForeignKey("tms_viagens.id"), nullable=True, index=True)
    entrega_id = Column(UUID(as_uuid=True), ForeignKey("tms_entregas.id"), nullable=True)
    tipo = Column(String(80), nullable=False, index=True)
    severidade = Column(String(30), nullable=False, index=True)
    descricao = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default="aberta", index=True)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)


class TMSAutorizacaoExcecaoORM(Base):
    __tablename__ = "tms_autorizacoes_excecao"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    viagem_id = Column(UUID(as_uuid=True), ForeignKey("tms_viagens.id"), nullable=True, index=True)
    entrega_id = Column(UUID(as_uuid=True), ForeignKey("tms_entregas.id"), nullable=True)
    regra = Column(String(120), nullable=False, index=True)
    justificativa = Column(Text, nullable=False)
    autorizado_por_id = Column(UUID(as_uuid=True), ForeignKey("tms_usuarios.id"), nullable=False)
    payload = Column(JSON, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)


class TMSEstoquePostoORM(Base):
    __tablename__ = "tms_estoques_posto"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    posto_id = Column(UUID(as_uuid=True), ForeignKey("tms_postos.id"), nullable=False, index=True)
    produto_id = Column(UUID(as_uuid=True), ForeignKey("tms_produtos.id"), nullable=False, index=True)
    viagem_id = Column(UUID(as_uuid=True), ForeignKey("tms_viagens.id"), nullable=True, index=True)
    entrega_id = Column(UUID(as_uuid=True), ForeignKey("tms_entregas.id"), nullable=True, index=True)
    compartimento_id = Column(UUID(as_uuid=True), ForeignKey("tms_compartimentos.id"), nullable=True)
    tanque_id = Column(UUID(as_uuid=True), ForeignKey("tms_tanques.id"), nullable=True)
    estoque_litros = Column(Numeric(12, 2), nullable=False)
    volume_descargado_litros = Column(Numeric(12, 2), nullable=True)
    origem = Column(String(50), nullable=False, default="manual")
    medido_em = Column(DateTime, nullable=False, index=True)
    responsavel_id = Column(UUID(as_uuid=True), ForeignKey("tms_usuarios.id"), nullable=True)
    foto_veeder_root_depois = Column(String(500), nullable=True)
    observacao = Column(Text, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)


class TMSDocumentoAnexoORM(Base):
    __tablename__ = "tms_documentos_anexos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    viagem_id = Column(UUID(as_uuid=True), ForeignKey("tms_viagens.id"), nullable=True, index=True)
    entrega_id = Column(UUID(as_uuid=True), ForeignKey("tms_entregas.id"), nullable=True)
    tipo = Column(String(80), nullable=False, index=True)
    storage_path = Column(String(500), nullable=False)
    criado_por_id = Column(UUID(as_uuid=True), ForeignKey("tms_usuarios.id"), nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)


class TMSNFeImportadaORM(Base):
    __tablename__ = "tms_nfes_importadas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chave = Column(String(60), nullable=True, unique=True, index=True)
    numero = Column(String(30), nullable=False, index=True)
    serie = Column(String(20), nullable=True)
    posto_cnpj = Column(String(20), nullable=False, index=True)
    emitente_cnpj = Column(String(20), nullable=True, index=True)
    emitente_nome = Column(String(255), nullable=True)
    produto = Column(String(255), nullable=False)
    volume = Column(Numeric(12, 3), nullable=False)
    valor = Column(Numeric(14, 2), nullable=True)
    transportador = Column(String(255), nullable=True, index=True)
    transportador_documento = Column(String(20), nullable=True)
    placa = Column(String(20), nullable=True, index=True)
    uf_placa = Column(String(2), nullable=True)
    viagem_id = Column(UUID(as_uuid=True), ForeignKey("tms_viagens.id"), nullable=True, index=True)
    xml_storage_path = Column(String(500), nullable=True)
    dados_xml = Column(JSON, nullable=True)
    emitida_em = Column(DateTime, nullable=True, index=True)
    importada_em = Column(DateTime, default=datetime.utcnow, nullable=False)
