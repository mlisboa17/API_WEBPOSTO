"""Rota de Sobras/Perdas + Autonomia preditiva de tanques."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from src.core.config import OFFICIAL_COMPANY_CODES
from src.services.inventory_prediction_service import InventoryPredictionService

router = APIRouter(prefix="/api/v1/operational", tags=["Operacional"])
logger = logging.getLogger(__name__)

_EMPRESA_NOME_OPERACIONAL = {
    5555: "AP CASA CAIADA",
    11495: "POSTO VIP",
    74014: "POSTO REAL / DOZE",
}


def _empresa_nome_operacional(codigo: int) -> str:
    return _EMPRESA_NOME_OPERACIONAL.get(codigo, f"Filial {codigo}")


def _is_gnv(fuel: str = "", tipo: str = "", produto_codigo: Any = None) -> bool:
    blob = f"{fuel} {tipo}".upper()
    code = str(produto_codigo or "").strip()
    return (
        "GNV" in blob
        or "GAS NATURAL" in blob
        or code in {"99", "099"}
        or code.lstrip("0") == "99"
    )


class TankData(BaseModel):
    """Payload compatível com o frontend de /operational/tanks."""

    id: int = 0
    name: str = ""
    fuel: str = ""
    capacity: float = 0.0
    current: float = 0.0
    temp: float = 0.0
    physical_var: float = 0.0
    thermal_var: float = 0.0
    status: str = "NORMAL"
    empresa_codigo: int = 0
    empresa_nome: str = ""
    autonomia_dias: float | None = None
    consumo_medio_diario: float = 0.0
    alerta_autonomia: str = "OK"  # OK | ATENCAO | COMPRA_URGENTE
    alerta_label: str = "Saudável"
    estoque_fisico: float = 0.0
    estoque_contabil: float = 0.0
    divergencia_litros: float = 0.0
    divergencia_pct: float = 0.0
    alerta_variancia: bool = False
    alerta_variancia_label: str = ""
    data_hora_medidor: str | None = None


class FuelLossSummary(BaseModel):
    total_tanques: int = 0
    tanques_criticos: int = 0
    tanques_suspeitos: int = 0
    tanques_ruptura: int = 0
    volume_total_litros: float = 0.0
    variacao_total_litros: float = 0.0


class FuelLossResponse(BaseModel):
    success: bool = True
    tanks: list[TankData] = Field(default_factory=list)
    summary: FuelLossSummary | None = None


@router.get("/fuel-loss", response_model=FuelLossResponse)
async def get_fuel_loss(
    dataInicial: str = Query(..., description="Data inicial (YYYY-MM-DD)"),
    dataFinal: str = Query(..., description="Data final (YYYY-MM-DD)"),
    empresaCodigo: int | None = Query(None, description="Código da empresa (filial)"),
) -> FuelLossResponse:
    """
    Tanques WebPosto + Autonomia (Dias) = volume atual / venda média diária 7d.
    """
    try:
        from src.gateway.shared_client import get_webposto_client

        client = get_webposto_client()
        targets = (
            [int(empresaCodigo)]
            if empresaCodigo
            else list(OFFICIAL_COMPANY_CODES)
        )

        # Predições com runway (TANQUE + histórico local 7d)
        pred_service = InventoryPredictionService()
        runway_by_key: dict[tuple[int, str], Any] = {}
        for code in targets:
            try:
                pred = await pred_service.predict(code, dias_historico=7)
                for p in pred.predicoes:
                    key = (code, str(p.produto_codigo))
                    runway_by_key[key] = p
                    # também indexa por nome normalizado
                    runway_by_key[(code, p.produto_nome.upper().strip())] = p
            except Exception as exc:
                logger.warning("runway predict empresa=%s: %s", code, exc)

        tanks: list[TankData] = []
        # Dedupe (empresa, tanqueCodigo) — mantém a medição mais recente
        latest_by_tank: dict[tuple[int, int], dict[str, Any]] = {}

        for code in targets:
            params: dict[str, Any] = {
                "dataInicial": dataInicial,
                "dataFinal": dataFinal,
                "empresaCodigo": code,
            }
            resp = await client.call_endpoint("tanque", params=params)
            if not resp.success:
                logger.warning("Falha tanque empresa=%s: %s", code, resp.error)
                continue
            raw = resp.data
            records: list[dict] = []
            if isinstance(raw, dict):
                records = raw.get("dados") or raw.get("data") or raw.get("resultados") or []
            elif isinstance(raw, list):
                records = raw
            records = [
                r for r in records if int(r.get("empresaCodigo") or code or 0) == int(code)
            ]

            for r in records:
                try:
                    tank_id = int(r.get("tanqueCodigo") or r.get("codigo") or 0)
                    if tank_id <= 0:
                        continue
                    medidor_raw = (
                        r.get("dataHoraMedidor")
                        or r.get("dataHoraMedicao")
                        or r.get("dataMedicao")
                        or r.get("ultimaMedicao")
                        or ""
                    )
                    medidor_key = str(medidor_raw)
                    prev = latest_by_tank.get((code, tank_id))
                    if prev and str(prev.get("_medidor_key") or "") >= medidor_key:
                        continue
                    r = {**r, "_medidor_key": medidor_key, "_empresa": code, "_tank_id": tank_id}
                    latest_by_tank[(code, tank_id)] = r
                except (ValueError, TypeError) as e:
                    logger.debug("Erro ao indexar tanque: %s", e)
                    continue

        for (code, tank_id), r in latest_by_tank.items():
            try:
                capacidade = float(
                    r.get("capacidade")
                    or r.get("capacidadeLitros")
                    or r.get("capacidadeTotal")
                    or r.get("volumeMaximo")
                    or r.get("capacidadeMaxima")
                    or 0
                )
                fisico = float(
                    r.get("volumeAtual")
                    or r.get("volumeAtualLitros")
                    or r.get("estoqueFisico")
                    or r.get("estoqueAtual")
                    or r.get("volume")
                    or 0
                )
                contabil = float(
                    r.get("estoqueEscritural")
                    or r.get("estoqueContabil")
                    or r.get("saldoEscritural")
                    or 0
                )
                entradas = float(r.get("entradas") or r.get("volumeEntradas") or 0)
                saidas = float(
                    r.get("saidas") or r.get("vendas") or r.get("volumeSaidas") or 0
                )
                inicial = float(r.get("estoqueInicial") or r.get("saldoInicial") or 0)
                if contabil <= 0 and (inicial > 0 or entradas > 0 or saidas > 0):
                    contabil = inicial + entradas - saidas
                volume = fisico if fisico > 0 else contabil
                variacao = float(r.get("variacao") or r.get("variacaoLitros") or 0)
                if fisico > 0 and contabil > 0:
                    divergencia = fisico - contabil
                else:
                    divergencia = variacao
                    if contabil <= 0 and fisico > 0:
                        contabil = fisico - variacao
                base_vol = capacidade if capacidade > 0 else max(fisico, contabil, 1)
                divergencia_pct = (abs(divergencia) / base_vol) * 100 if base_vol else 0
                alerta_var = abs(divergencia) > (0.006 * base_vol) and base_vol > 0
                temp = float(r.get("temperatura") or r.get("temp") or 0)
                prod_cod = str(
                    r.get("produtoCodigo")
                    or r.get("produtoLmcCodigo")
                    or r.get("codigoProduto")
                    or ""
                )
                prod_nome = str(
                    r.get("produtoDescricao") or r.get("produto") or r.get("nome") or ""
                ).strip()
                nome = str(r.get("descricao") or r.get("nome") or prod_nome or "Tanque")

                pred = runway_by_key.get((code, prod_cod)) or runway_by_key.get(
                    (code, prod_nome.upper())
                )
                if pred and volume <= 0 and pred.estoque_atual_litros > 0:
                    volume = pred.estoque_atual_litros
                    fisico = volume
                if pred and capacidade <= 0 and pred.capacidade_tanque > 0:
                    capacidade = pred.capacidade_tanque
                    base_vol = capacidade
                    divergencia_pct = (abs(divergencia) / base_vol) * 100 if base_vol else 0
                    alerta_var = abs(divergencia) > (0.006 * base_vol)

                autonomia = pred.autonomia_dias_restantes if pred else None
                alerta = pred.status_alerta if pred else "OK"
                label = pred.alerta_label if pred else "Saudável"
                consumo = pred.consumo_medio_diario if pred else 0.0
                fuel_label = prod_nome or (pred.produto_nome if pred else "")
                if _is_gnv(
                    fuel_label,
                    pred.tipo_combustivel if pred else "",
                    pred.produto_codigo if pred else None,
                ):
                    alerta = "OK"
                    label = "GNV canalizado — sem carreta"
                    autonomia = None

                status = "NORMAL"
                if alerta == "COMPRA_URGENTE" or (autonomia is not None and autonomia < 1.5):
                    status = "CRITICO"
                elif alerta_var:
                    status = "DESVIO_SUSPEITO"
                elif alerta == "ATENCAO" or (autonomia is not None and autonomia < 3):
                    status = "DESVIO_SUSPEITO"
                elif variacao < -50:
                    status = "CRITICO"
                elif variacao < -20:
                    status = "DESVIO_SUSPEITO"

                medidor_raw = r.get("_medidor_key") or (
                    r.get("dataHoraMedidor")
                    or r.get("dataHoraMedicao")
                    or r.get("dataMedicao")
                    or r.get("ultimaMedicao")
                )
                medidor_iso = str(medidor_raw).strip() if medidor_raw else None

                tanks.append(
                    TankData(
                        id=tank_id,
                        name=nome,
                        fuel=fuel_label,
                        capacity=capacidade,
                        current=volume,
                        temp=temp,
                        physical_var=divergencia if divergencia else variacao,
                        thermal_var=float(r.get("variacaoTermica") or 0),
                        status=status,
                        empresa_codigo=code,
                        empresa_nome=_empresa_nome_operacional(code),
                        autonomia_dias=autonomia,
                        consumo_medio_diario=consumo,
                        alerta_autonomia=alerta,
                        alerta_label=label,
                        estoque_fisico=round(fisico or volume, 2),
                        estoque_contabil=round(contabil, 2),
                        divergencia_litros=round(divergencia, 2),
                        divergencia_pct=round(divergencia_pct, 3),
                        alerta_variancia=alerta_var,
                        alerta_variancia_label=(
                            "Alerta de Auditoria de Variância (Possível Variação Térmica ou Fuga)"
                            if alerta_var
                            else ""
                        ),
                        data_hora_medidor=medidor_iso,
                    )
                )
            except (ValueError, TypeError) as e:
                logger.debug("Erro ao processar tanque: %s", e)
                continue

        # Se TANQUE vazio mas há predições, materializa cards a partir do inventário
        if not tanks and runway_by_key:
            seen: set[tuple[int, int]] = set()
            for (code, key), p in list(runway_by_key.items()):
                if not isinstance(key, str) or not key.isdigit():
                    continue
                sig = (code, int(key))
                if sig in seen:
                    continue
                seen.add(sig)
                gnv = _is_gnv(p.produto_nome, p.tipo_combustivel, p.produto_codigo)
                alerta = "OK" if gnv else p.status_alerta
                tanks.append(
                    TankData(
                        id=p.produto_codigo,
                        name=p.produto_nome,
                        fuel=p.tipo_combustivel,
                        capacity=p.capacidade_tanque,
                        current=p.estoque_atual_litros,
                        status=(
                            "NORMAL"
                            if gnv
                            else "CRITICO"
                            if alerta == "COMPRA_URGENTE"
                            else "DESVIO_SUSPEITO"
                            if alerta == "ATENCAO"
                            else "NORMAL"
                        ),
                        empresa_codigo=code,
                        empresa_nome=_empresa_nome_operacional(code),
                        autonomia_dias=None if gnv else p.autonomia_dias_restantes,
                        consumo_medio_diario=p.consumo_medio_diario,
                        alerta_autonomia=alerta,
                        alerta_label=(
                            "GNV canalizado — sem carreta" if gnv else p.alerta_label
                        ),
                    )
                )

        summary = FuelLossSummary(
            total_tanques=len(tanks),
            tanques_criticos=sum(1 for t in tanks if t.status == "CRITICO"),
            tanques_suspeitos=sum(1 for t in tanks if t.status == "DESVIO_SUSPEITO"),
            tanques_ruptura=sum(
                1 for t in tanks if t.alerta_autonomia == "COMPRA_URGENTE"
            ),
            volume_total_litros=sum(t.current for t in tanks),
            variacao_total_litros=sum(t.physical_var for t in tanks),
        )
        return FuelLossResponse(success=True, tanks=tanks, summary=summary)
    except Exception as e:
        logger.exception("Erro na rota fuel-loss: %s", e)
        return FuelLossResponse(success=True, tanks=[], summary=FuelLossSummary())
