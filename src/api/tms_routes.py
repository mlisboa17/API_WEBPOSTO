"""FastAPI routes for the fuel TMS MVP contracts."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.domain.tms.schemas import (
    Alerta,
    DescargaFinalizarInput,
    DescargaIniciarInput,
    MobileEventoInput,
    MobileEventoResultado,
    NFE,
    NFEAuditoriaResultado,
    OrdemDescarga,
    ProgramacaoInput,
    ResultadoValidacaoProgramacao,
    SeveridadeAlerta,
    StatusViagem,
    SugerirOrdemDescargaInput,
    ValidarExecucaoOrdemInput,
)
from src.domain.tms.services import (
    NFEAuditoriaService,
    OrdemDescargaException,
    OrdemDescargaService,
    ProgramacaoValidator,
    criar_evento_mobile,
)


router = APIRouter(tags=["TMS"])

programacao_validator = ProgramacaoValidator()
ordem_service = OrdemDescargaService()
nfe_service = NFEAuditoriaService()


@router.post("/api/tms/programacoes/validar", response_model=ResultadoValidacaoProgramacao)
async def validar_programacao(payload: ProgramacaoInput) -> ResultadoValidacaoProgramacao:
    return programacao_validator.validar_programacao(payload)


@router.post("/api/tms/alertas", response_model=list[Alerta])
async def gerar_alertas_laterais(payload: ProgramacaoInput) -> list[Alerta]:
    resultado = programacao_validator.validar_programacao(payload)
    return resultado.alertas_laterais


@router.post("/api/tms/ordem-descarga/sugerir", response_model=OrdemDescarga)
async def sugerir_ordem_descarga(payload: SugerirOrdemDescargaInput) -> OrdemDescarga:
    return OrdemDescarga(
        viagem_id=payload.viagem_id,
        ordem=ordem_service.sugerir_ordem(payload.entregas),
        manual=False,
    )


@router.post("/api/tms/ordem-descarga/validar-execucao")
async def validar_execucao_ordem(payload: ValidarExecucaoOrdemInput) -> dict:
    try:
        ordem_service.validar_execucao(payload)
    except OrdemDescargaException as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "mensagem": str(exc),
                "registrar_excecao": True,
                "requer_autorizacao": True,
            },
        ) from exc
    return {"ok": True, "registrar_excecao": payload.entrega_atual != payload.ordem.ordem[0]}


@router.post("/api/tms/nfe/auditar", response_model=NFEAuditoriaResultado)
async def auditar_nfe(payload: NFE) -> NFEAuditoriaResultado:
    return nfe_service.auditar(payload)


@router.post("/viagem/iniciar", response_model=MobileEventoResultado)
async def iniciar_viagem(payload: MobileEventoInput) -> MobileEventoResultado:
    return criar_evento_mobile(payload, StatusViagem.LIBERADA_SUAPE)


@router.post("/checkin/garagem", response_model=MobileEventoResultado)
async def checkin_garagem(payload: MobileEventoInput) -> MobileEventoResultado:
    return criar_evento_mobile(payload, StatusViagem.LIBERADA_SUAPE)


@router.post("/checkin/suape", response_model=MobileEventoResultado)
async def checkin_suape(payload: MobileEventoInput) -> MobileEventoResultado:
    return criar_evento_mobile(payload, StatusViagem.NA_BASE)


@router.post("/carregamento", response_model=MobileEventoResultado)
async def registrar_carregamento(payload: MobileEventoInput) -> MobileEventoResultado:
    return criar_evento_mobile(payload, StatusViagem.CARREGADA)


@router.post("/lacres", response_model=MobileEventoResultado)
async def registrar_lacres(payload: MobileEventoInput) -> MobileEventoResultado:
    resultado = criar_evento_mobile(payload, StatusViagem.CARREGADA)
    if not payload.payload.get("lacres"):
        resultado.alertas.append(
            Alerta(
                tipo="lacres_ausentes",
                mensagem="Informe os lacres dos compartimentos",
                severidade=SeveridadeAlerta.WARNING,
            )
        )
    return resultado


@router.post("/saida", response_model=MobileEventoResultado)
async def registrar_saida(payload: MobileEventoInput) -> MobileEventoResultado:
    return criar_evento_mobile(payload, StatusViagem.EM_ROTA)


@router.post("/chegada-posto", response_model=MobileEventoResultado)
async def registrar_chegada_posto(payload: MobileEventoInput) -> MobileEventoResultado:
    return criar_evento_mobile(payload, StatusViagem.NO_POSTO)


@router.post("/descarga/iniciar", response_model=MobileEventoResultado)
async def iniciar_descarga(payload: DescargaIniciarInput) -> MobileEventoResultado:
    if not payload.compartimento_qr or not payload.tanque_qr:
        raise HTTPException(
            status_code=400,
            detail="QR do compartimento e QR do tanque sao obrigatorios",
        )
    if payload.produto_compartimento_id != payload.produto_tanque_id:
        resultado = criar_evento_mobile(payload, StatusViagem.NO_POSTO)
        resultado.bloqueado = True
        resultado.alertas.append(
            Alerta(
                tipo="produto_tanque_incompativel",
                mensagem="Produto do compartimento incompativel com tanque",
                severidade=SeveridadeAlerta.ERRO,
            )
        )
        return resultado
    try:
        ordem_service.validar_execucao(
            ValidarExecucaoOrdemInput(
                ordem=payload.ordem,
                entrega_atual=payload.entrega_id,
            )
        )
    except OrdemDescargaException:
        resultado = criar_evento_mobile(payload, StatusViagem.NO_POSTO)
        resultado.requer_autorizacao = True
        resultado.alertas.append(
            Alerta(
                tipo="fora_ordem_descarga",
                mensagem="Fora da ordem. Requer autorizacao da Jane",
                severidade=SeveridadeAlerta.WARNING,
            )
        )
        return resultado
    return criar_evento_mobile(payload, StatusViagem.DESCARREGANDO)


@router.post("/descarga/finalizar", response_model=MobileEventoResultado)
async def finalizar_descarga(payload: DescargaFinalizarInput) -> MobileEventoResultado:
    if not payload.foto_veeder_root_url:
        raise HTTPException(
            status_code=400,
            detail="Foto do Veeder-Root pos-descarga e obrigatoria",
        )
    resultado = criar_evento_mobile(payload, StatusViagem.ENTREGUE)
    if payload.volume_descargado_litros != payload.volume_programado_litros:
        resultado.alertas.append(
            Alerta(
                tipo="divergencia_volume_descarga",
                mensagem="Volume descarregado diverge do volume programado",
                severidade=SeveridadeAlerta.ERRO,
            )
        )
    resultado.alertas.append(
        Alerta(
            tipo="estoque_atualizado_por_veeder_root",
            mensagem="Foto Veeder-Root registrada como evidência da entrega e estoque do posto",
            severidade=SeveridadeAlerta.INFO,
        )
    )
    return resultado


@router.post("/comprovante", response_model=MobileEventoResultado)
async def registrar_comprovante(payload: MobileEventoInput) -> MobileEventoResultado:
    resultado = criar_evento_mobile(payload, StatusViagem.ENTREGUE)
    if not payload.payload.get("foto_url"):
        resultado.alertas.append(
            Alerta(
                tipo="comprovante_sem_foto",
                mensagem="Foto do comprovante nao informada",
                severidade=SeveridadeAlerta.WARNING,
            )
        )
    return resultado
