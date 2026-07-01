"""Business validators for the fuel TMS MVP."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from src.domain.tms.schemas import (
    Alerta,
    CompartimentoProgramacao,
    EntregaResumo,
    MobileEventoInput,
    MobileEventoResultado,
    NFE,
    NFEAuditoriaResultado,
    OrdemDescarga,
    ProgramacaoInput,
    ResultadoValidacaoProgramacao,
    SeveridadeAlerta,
    StatusCompartimento,
    StatusViagem,
    ValidarExecucaoOrdemInput,
    Evento,
    OrigemEvento,
)


VOLUME_ALVO_VIAGEM_LITROS = 25000
TOTAL_COMPARTIMENTOS = 5
VOLUME_COMPARTIMENTO_LITROS = 5000


class OrdemDescargaException(Exception):
    """Raised when a delivery execution violates the planned unloading order."""


class ProgramacaoValidator:
    """Validates scheduling rules before a trip can be released."""

    def validar_programacao(
        self, programacao: ProgramacaoInput
    ) -> ResultadoValidacaoProgramacao:
        erros: list[str] = []
        alertas: list[str] = []
        status_compartimentos = {
            compartimento.id: self.status_compartimento(compartimento, programacao)
            for compartimento in programacao.compartimentos
        }

        if self.total_volume(programacao) < VOLUME_ALVO_VIAGEM_LITROS:
            alertas.append("Volume total abaixo de 25.000L")

        if not self.todos_compartimentos_preenchidos(programacao):
            erros.append("Todos os 5 compartimentos devem estar preenchidos")

        if not self.posto_tem_geo(programacao):
            erros.append("Posto sem geolocalizacao")

        if not self.tanque_compativel(programacao):
            erros.append("Produto incompativel com tanque")

        if not self.documentos_validos(programacao):
            erros.append("Documentos criticos invalidos")

        return ResultadoValidacaoProgramacao(
            erros=erros,
            alertas=alertas,
            status_compartimentos=status_compartimentos,
            alertas_laterais=self.gerar_alertas_laterais(programacao, erros, alertas),
        )

    def total_volume(self, programacao: ProgramacaoInput) -> float:
        return sum(
            compartimento.volume_litros
            for compartimento in programacao.compartimentos
            if not compartimento.esta_vazio
        )

    def todos_compartimentos_preenchidos(self, programacao: ProgramacaoInput) -> bool:
        if len(programacao.compartimentos) != TOTAL_COMPARTIMENTOS:
            return False
        return all(
            not compartimento.esta_vazio or compartimento.excecao_vazio_autorizada
            for compartimento in programacao.compartimentos
        )

    def posto_tem_geo(self, programacao: ProgramacaoInput) -> bool:
        postos = {posto.id: posto for posto in programacao.postos}
        for compartimento in programacao.compartimentos:
            if compartimento.posto_id is None:
                continue
            posto = postos.get(compartimento.posto_id)
            if posto is None or not posto.tem_geo:
                return False
        return True

    def tanque_compativel(self, programacao: ProgramacaoInput) -> bool:
        tanques = {tanque.id: tanque for tanque in programacao.tanques}
        for compartimento in programacao.compartimentos:
            if compartimento.tanque_id is None or compartimento.produto_id is None:
                continue
            tanque = tanques.get(compartimento.tanque_id)
            if tanque is None or tanque.produto_id != compartimento.produto_id:
                return False
        return True

    def documentos_validos(self, programacao: ProgramacaoInput) -> bool:
        return all(documento.valido for documento in programacao.documentos_criticos)

    def status_compartimento(
        self, compartimento: CompartimentoProgramacao, programacao: ProgramacaoInput
    ) -> StatusCompartimento:
        if compartimento.esta_vazio:
            return StatusCompartimento.CINZA

        campos_obrigatorios = [
            compartimento.produto_id,
            compartimento.posto_id,
            compartimento.tanque_id,
            compartimento.entrega_id,
        ]
        if any(campo is None for campo in campos_obrigatorios):
            return StatusCompartimento.AMARELO

        tanque = next(
            (item for item in programacao.tanques if item.id == compartimento.tanque_id),
            None,
        )
        posto = next(
            (item for item in programacao.postos if item.id == compartimento.posto_id),
            None,
        )
        if tanque is None or tanque.produto_id != compartimento.produto_id:
            return StatusCompartimento.VERMELHO
        if posto is None or not posto.tem_geo:
            return StatusCompartimento.VERMELHO
        return StatusCompartimento.VERDE

    def gerar_alertas_laterais(
        self,
        programacao: ProgramacaoInput,
        erros: list[str],
        alertas: list[str],
    ) -> list[Alerta]:
        laterais = [
            Alerta(tipo="erro_programacao", mensagem=erro, severidade=SeveridadeAlerta.ERRO)
            for erro in erros
        ]
        laterais.extend(
            Alerta(
                tipo="alerta_programacao",
                mensagem=alerta,
                severidade=SeveridadeAlerta.WARNING,
            )
            for alerta in alertas
        )

        if programacao.janela_suape is None:
            laterais.append(
                Alerta(
                    tipo="janela_suape",
                    mensagem="Janela de Suape nao definida",
                    severidade=SeveridadeAlerta.ERRO,
                )
            )
        else:
            agora = datetime.now(timezone.utc)
            janela = programacao.janela_suape
            if janela.tzinfo is None:
                janela = janela.replace(tzinfo=timezone.utc)
            horas = (janela - agora).total_seconds() / 3600
            if 0 <= horas <= 2:
                laterais.append(
                    Alerta(
                        tipo="janela_suape",
                        mensagem="Janela de Suape em menos de 2 horas",
                        severidade=SeveridadeAlerta.WARNING,
                    )
                )

        laterais.append(
            Alerta(
                tipo="tempo_rota",
                mensagem="Tempo estimado Igarassu-Suape: 1h30 a 2h para 60km",
                severidade=SeveridadeAlerta.INFO,
            )
        )

        if self.total_volume(programacao) < VOLUME_ALVO_VIAGEM_LITROS:
            laterais.append(
                Alerta(
                    tipo="caminhao_incompleto",
                    mensagem="Caminhao abaixo de 25.000L",
                    severidade=SeveridadeAlerta.WARNING,
                )
            )

        if programacao.pedidos_criticos_pendentes > 0:
            laterais.append(
                Alerta(
                    tipo="pedido_critico",
                    mensagem="Existem pedidos criticos pendentes",
                    severidade=SeveridadeAlerta.WARNING,
                )
            )

        if any(tanque.qr_code is None for tanque in programacao.tanques):
            laterais.append(
                Alerta(
                    tipo="tanque_sem_qr",
                    mensagem="Existem tanques sem QR Code",
                    severidade=SeveridadeAlerta.WARNING,
                )
            )

        if any(
            documento.vence_em_dias is not None and 0 <= documento.vence_em_dias <= 30
            for documento in programacao.documentos_criticos
        ):
            laterais.append(
                Alerta(
                    tipo="documento_vencendo",
                    mensagem="Documento critico vencendo em ate 30 dias",
                    severidade=SeveridadeAlerta.WARNING,
                )
            )

        if not programacao.ordem_definida:
            laterais.append(
                Alerta(
                    tipo="ordem_nao_definida",
                    mensagem="Ordem de descarga nao definida",
                    severidade=SeveridadeAlerta.ERRO,
                )
            )

        if not programacao.nfe_vinculada:
            laterais.append(
                Alerta(
                    tipo="nfe_nao_vinculada",
                    mensagem="NF-e ainda nao vinculada a viagem",
                    severidade=SeveridadeAlerta.INFO,
                )
            )

        return laterais


class OrdemDescargaService:
    """Creates and validates unloading order."""

    def sugerir_ordem(self, entregas: list[EntregaResumo]) -> list[UUID]:
        return [entrega.id for entrega in sorted(entregas, key=lambda item: item.rota_index)]

    def validar_execucao(self, payload: ValidarExecucaoOrdemInput) -> bool:
        if not payload.ordem.ordem:
            raise OrdemDescargaException("Ordem de descarga nao definida")
        if payload.entrega_atual != payload.ordem.ordem[0]:
            if payload.autorizado_por and payload.justificativa:
                return True
            raise OrdemDescargaException("Fora da ordem. Requer autorizacao.")
        return True


class NFEAuditoriaService:
    """Generates fiscal/logistics alerts from imported NF-e data."""

    def auditar(self, nfe: NFE) -> NFEAuditoriaResultado:
        alertas: list[Alerta] = []
        if not nfe.placa:
            alertas.append(
                Alerta(
                    tipo="nfe_sem_placa",
                    mensagem="NF-e sem placa informada",
                    severidade=SeveridadeAlerta.WARNING,
                )
            )
        if not nfe.viagem_id:
            alertas.append(
                Alerta(
                    tipo="nfe_sem_vinculo_viagem",
                    mensagem="NF-e sem vinculo com viagem",
                    severidade=SeveridadeAlerta.WARNING,
                )
            )
        if (
            nfe.transportador_esperado
            and nfe.transportador
            and nfe.transportador.strip().lower()
            != nfe.transportador_esperado.strip().lower()
        ):
            alertas.append(
                Alerta(
                    tipo="transportador_inesperado",
                    mensagem="Transportador diferente do esperado",
                    severidade=SeveridadeAlerta.ERRO,
                )
            )
        if nfe.produto_programado and nfe.produto.strip().lower() != nfe.produto_programado.strip().lower():
            alertas.append(
                Alerta(
                    tipo="divergencia_produto",
                    mensagem="Produto da NF-e diverge da programacao",
                    severidade=SeveridadeAlerta.ERRO,
                )
            )
        if nfe.volume_programado is not None and nfe.volume != nfe.volume_programado:
            alertas.append(
                Alerta(
                    tipo="divergencia_volume",
                    mensagem="Volume da NF-e diverge da programacao",
                    severidade=SeveridadeAlerta.ERRO,
                )
            )
        return NFEAuditoriaResultado(alertas=alertas)


def criar_evento_mobile(
    payload: MobileEventoInput,
    status: StatusViagem,
    origem: OrigemEvento = OrigemEvento.APP,
) -> MobileEventoResultado:
    evento = Evento(
        status=status,
        data_hora=datetime.now(timezone.utc),
        usuario_id=payload.usuario_id,
        geo=payload.geo,
        origem=origem,
        observacao=payload.observacao,
    )
    return MobileEventoResultado(status=status, evento=evento)
