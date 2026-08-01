"""Rota para Cockpit 30s — Feed vivo REST v1 (pendentes + baixados).

GET /api/v1/operational/cockpit-live

Consome a fachada:
  GET /api/v1/abastecimentos/pendentes
  GET /api/v1/abastecimentos/baixados
via WebPostoPistaService (mapeamento Quality INTEGRACAO → schema REST v1).
"""

from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.core.config import OFFICIAL_COMPANY_CODES
from src.services.webposto_pista_service import get_pista_service

LOGGER = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/operational",
    tags=["Cockpit Live"],
)

FILIAIS = {
    5555: "AP CASA CAIADA",
    11495: "POSTO VIP",
    74014: "POSTO REAL / DOZE",
}

FONTE = "REST_v1_Abastecimentos"
ENDPOINT = "/api/v1/abastecimentos/pendentes+/baixados"


class AbastecimentoDTO(BaseModel):
    id: int
    uuid: str = ""
    data: str
    hora: str
    bico: int
    produto: str
    litros: float
    valor: float
    encerrante_inicial: float = 0.0
    encerrante_final: float = 0.0
    empresa_codigo: int
    empresa_nome: str
    frentista_id: int | None = None
    frentista_nome: str = "N/I"
    status_pista: str = "PAGO"  # PENDENTE | PAGO (alias BAIXADO)
    reservado: bool = False
    venda_item_codigo: int = 0
    data_hora_abastecimento: str = ""
    data_hora_baixa: str | None = None
    forma_pagamento: str | None = None
    id_venda: int | None = None


class FilialSummary(BaseModel):
    empresa_codigo: int
    empresa_nome: str
    total_litros: float
    total_valor: float
    total_transacoes: int
    total_pendentes: int = 0
    ultimo_abastecimento: AbastecimentoDTO | None
    status: str


class CockpitLiveResponse(BaseModel):
    success: bool
    synthetic: bool = False
    fonte: str = FONTE
    endpoint: str = ENDPOINT
    periodo: dict[str, str]
    filiais: list[FilialSummary]
    abastecimentos: list[AbastecimentoDTO]
    observacoes: list[str] = []
    error: str | None = None


def _empty_summary(empresa_codigo: int) -> FilialSummary:
    return FilialSummary(
        empresa_codigo=empresa_codigo,
        empresa_nome=FILIAIS.get(empresa_codigo, f"Empresa {empresa_codigo}"),
        total_litros=0.0,
        total_valor=0.0,
        total_transacoes=0,
        total_pendentes=0,
        ultimo_abastecimento=None,
        status="AGUARDANDO",
    )


def _hora_from(data_hora: str) -> str:
    if not data_hora:
        return "--:--"
    if "T" in data_hora:
        return data_hora.split("T", 1)[1][:8]
    if " " in data_hora:
        return data_hora.split(" ", 1)[1][:8]
    return data_hora[:8]


@router.get("/cockpit-live", response_model=CockpitLiveResponse)
async def cockpit_live(
    dataInicial: str | None = Query(None, description="Data inicial (YYYY-MM-DD)"),
    dataFinal: str | None = Query(None, description="Data final (YYYY-MM-DD)"),
    empresaCodigo: int | None = Query(None, description="Codigo da empresa (filial)"),
) -> CockpitLiveResponse:
    """Feed vivo: mescla pendentes REST v1 + últimos baixados."""
    hoje = str(date.today())
    start = dataInicial or hoje
    end = dataFinal or hoje
    periodo = {"inicio": start, "fim": end}

    targets = (
        [empresaCodigo]
        if empresaCodigo
        else list(OFFICIAL_COMPANY_CODES)
    )

    try:
        feed = await get_pista_service().feed_vivo(
            id_empresa=empresaCodigo,
            data_inicio=start,
            data_fim=end,
            limite_baixados=100,
        )

        mapped: list[AbastecimentoDTO] = []
        for item in feed.items:
            if empresaCodigo and item.idEmpresa != int(empresaCodigo):
                continue
            if item.idEmpresa not in FILIAIS and item.idEmpresa not in targets:
                continue

            pendente = item.status == "PENDENTE"
            mapped.append(
                AbastecimentoDTO(
                    id=item.idAbastecimento,
                    uuid=item.uuid,
                    data=(item.dataHora or "")[:10],
                    hora=_hora_from(item.dataHora),
                    bico=item.bico,
                    produto=item.descricaoProduto,
                    litros=item.litros,
                    valor=item.valorTotal,
                    empresa_codigo=item.idEmpresa,
                    empresa_nome=item.nomeEmpresa or FILIAIS.get(item.idEmpresa, f"Empresa {item.idEmpresa}"),
                    frentista_id=item.idFrentista,
                    frentista_nome=item.nomeFrentista,
                    status_pista="PENDENTE" if pendente else "PAGO",
                    reservado=item.reservado,
                    venda_item_codigo=0 if pendente else (item.idVenda or 1),
                    data_hora_abastecimento=item.dataHora,
                    data_hora_baixa=item.dataHoraBaixa,
                    forma_pagamento=item.formaPagamento,
                    id_venda=item.idVenda,
                )
            )

        by_filial: dict[int, list[AbastecimentoDTO]] = {c: [] for c in targets}
        for dto in mapped:
            if dto.empresa_codigo in by_filial:
                by_filial[dto.empresa_codigo].append(dto)
            elif dto.empresa_codigo in FILIAIS:
                by_filial.setdefault(dto.empresa_codigo, []).append(dto)

        filiais: list[FilialSummary] = []
        for codigo in targets:
            items = by_filial.get(codigo) or []
            pendentes = sum(1 for i in items if i.status_pista == "PENDENTE")
            filiais.append(
                FilialSummary(
                    empresa_codigo=codigo,
                    empresa_nome=FILIAIS.get(codigo, f"Empresa {codigo}"),
                    total_litros=round(sum(i.litros for i in items), 2),
                    total_valor=round(sum(i.valor for i in items), 2),
                    total_transacoes=len(items),
                    total_pendentes=pendentes,
                    ultimo_abastecimento=items[0] if items else None,
                    status="PISTA_ATIVA" if items else "AGUARDANDO",
                )
            )

        LOGGER.info(
            "cockpit-live REST v1: pend+baix=%d periodo=%s..%s",
            len(mapped),
            start,
            end,
        )

        return CockpitLiveResponse(
            success=True,
            synthetic=False,
            fonte=FONTE,
            endpoint=ENDPOINT,
            periodo=periodo,
            filiais=filiais,
            abastecimentos=mapped[:120],
            observacoes=feed.observacoes,
            error=feed.error,
        )
    except Exception as exc:
        LOGGER.exception("Cockpit REST v1 falhou: %s", exc)
        return CockpitLiveResponse(
            success=True,
            synthetic=False,
            fonte=FONTE,
            endpoint=ENDPOINT,
            periodo=periodo,
            filiais=[_empty_summary(c) for c in (targets or list(OFFICIAL_COMPANY_CODES))],
            abastecimentos=[],
            error=str(exc),
        )
