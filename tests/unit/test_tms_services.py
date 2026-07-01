from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from src.domain.tms.schemas import (
    CompartimentoProgramacao,
    DescargaFinalizarInput,
    EntregaResumo,
    NFE,
    OrdemDescarga,
    PostoResumo,
    ProgramacaoInput,
    StatusViagem,
    TanqueResumo,
    ValidarExecucaoOrdemInput,
)
from src.domain.tms.services import (
    NFEAuditoriaService,
    OrdemDescargaException,
    OrdemDescargaService,
    ProgramacaoValidator,
    criar_evento_mobile,
)


def _programacao_valida() -> ProgramacaoInput:
    posto_id = uuid4()
    produto_id = uuid4()
    tanques = [
        TanqueResumo(
            id=uuid4(),
            posto_id=posto_id,
            produto_id=produto_id,
            codigo=f"TQ-{index}",
            qr_code=f"QR-TQ-{index}",
        )
        for index in range(1, 6)
    ]
    compartimentos = [
        CompartimentoProgramacao(
            id=uuid4(),
            numero=index,
            produto_id=produto_id,
            posto_id=posto_id,
            tanque_id=tanques[index - 1].id,
            entrega_id=uuid4(),
            volume_litros=5000,
        )
        for index in range(1, 6)
    ]
    return ProgramacaoInput(
        veiculo_id=uuid4(),
        motorista_id=uuid4(),
        janela_suape=datetime.now(timezone.utc) + timedelta(hours=4),
        protocolo_suape="SUP-123",
        compartimentos=compartimentos,
        postos=[
            PostoResumo(
                id=posto_id,
                nome="Posto Real",
                latitude=-7.834,
                longitude=-34.9,
            )
        ],
        tanques=tanques,
        ordem_definida=True,
        nfe_vinculada=True,
    )


def test_programacao_valida_sem_erros() -> None:
    resultado = ProgramacaoValidator().validar_programacao(_programacao_valida())

    assert resultado.erros == []
    assert resultado.alertas == []
    assert {status.value for status in resultado.status_compartimentos.values()} == {"valido"}


def test_programacao_bloqueia_compartimento_vazio() -> None:
    programacao = _programacao_valida()
    programacao.compartimentos.pop()

    resultado = ProgramacaoValidator().validar_programacao(programacao)

    assert "Todos os 5 compartimentos devem estar preenchidos" in resultado.erros
    assert "Volume total abaixo de 25.000L" in resultado.alertas


def test_programacao_detecta_tanque_incompativel() -> None:
    programacao = _programacao_valida()
    programacao.tanques[0].produto_id = uuid4()

    resultado = ProgramacaoValidator().validar_programacao(programacao)

    assert "Produto incompativel com tanque" in resultado.erros


def test_ordem_descarga_sugere_por_rota_index() -> None:
    service = OrdemDescargaService()
    entrega_longe = EntregaResumo(id=uuid4(), posto_id=uuid4(), rota_index=2)
    entrega_perto = EntregaResumo(id=uuid4(), posto_id=uuid4(), rota_index=1)

    assert service.sugerir_ordem([entrega_longe, entrega_perto]) == [
        entrega_perto.id,
        entrega_longe.id,
    ]


def test_ordem_descarga_fora_da_ordem_requer_autorizacao() -> None:
    entrega_correta = uuid4()
    entrega_errada = uuid4()
    payload = ValidarExecucaoOrdemInput(
        ordem=OrdemDescarga(viagem_id=uuid4(), ordem=[entrega_correta], manual=True),
        entrega_atual=entrega_errada,
    )

    with pytest.raises(OrdemDescargaException):
        OrdemDescargaService().validar_execucao(payload)


def test_nfe_auditoria_alerta_sem_placa_e_sem_vinculo() -> None:
    resultado = NFEAuditoriaService().auditar(
        NFE(
            numero="123",
            posto_cnpj="00000000000100",
            produto="Diesel S10",
            volume=5000,
            transportador="Terceiro",
        )
    )

    assert {alerta.tipo for alerta in resultado.alertas} >= {
        "nfe_sem_placa",
        "nfe_sem_vinculo_viagem",
    }


def test_finalizacao_descarga_carrega_foto_e_estoque() -> None:
    payload = DescargaFinalizarInput(
        viagem_id=uuid4(),
        usuario_id=uuid4(),
        entrega_id=uuid4(),
        posto_id=uuid4(),
        tanque_id=uuid4(),
        produto_id=uuid4(),
        compartimento_id=uuid4(),
        volume_programado_litros=5000,
        volume_descargado_litros=5000,
        estoque_pos_descarga_litros=18340,
        foto_veeder_root_url="storage://veeder-root/posto-real/descarga.jpg",
    )

    resultado = criar_evento_mobile(payload, StatusViagem.ENTREGUE)

    assert resultado.status == StatusViagem.ENTREGUE
    assert payload.foto_veeder_root_url.endswith("descarga.jpg")
    assert payload.estoque_pos_descarga_litros == 18340
