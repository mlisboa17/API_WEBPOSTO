"""Análise Financeira Consolidada das Unidades (Sprint 7 / V2).

Orquestra DataAudit (fat, despesas, categorias) + FuelVolumetry (galonagem histórica).
Métrica central: margem operacional = (fat − despesas) / fat × 100.
"""

from __future__ import annotations

import logging
from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Any

from src.core.config import OFFICIAL_COMPANY_CODES
from src.services.data_audit_service import DataAuditService, FilialDailyAudit
from src.services.fuel_volumetry_service import FuelVolumetryService

LOGGER = logging.getLogger(__name__)

FILIAL_NAMES: dict[int, str] = {
    5555: "AP Casa Caiada",
    11495: "Posto VIP",
    74014: "Real Doze",
}

DEFAULT_META_MARGEM = 15.0
DEFAULT_LIMITE_ATENCAO = 8.0
DESVIO_ALERTA_PCT = 25.0  # categoria X% acima da média da rede


def _prev_period(start: str, end: str) -> tuple[str, str]:
    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    days = (e - s).days + 1
    prev_end = s - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)
    return prev_start.isoformat(), prev_end.isoformat()


def _status(margem: float, meta: float, atencao: float, fat: float, desp: float) -> str:
    if fat <= 0 and desp > 0:
        return "CRITICO"
    # Sem despesas carregadas, margem 100% é artefato — não marcar EXCELENTE
    if fat > 0 and desp <= 0:
        return "ATENCAO"
    if margem < 0 or margem < atencao:
        return "CRITICO"
    if margem < meta:
        return "ATENCAO"
    return "EXCELENTE"


def _folha_rs(f: FilialDailyAudit) -> float:
    total = 0.0
    for c in f.despesasPorCategoria or []:
        key = (c.categoriaKey or c.categoria or "").upper()
        label = (c.categoria or "").casefold()
        if key in {"PESSOAL", "FOLHA"} or "folha" in label or "pessoal" in label:
            total += float(c.valor or 0)
    # vales contam como custo de pessoal operacional
    total += float(getattr(f.valesFuncionarios, "total", 0) or 0)
    return round(total, 2)


def _pct_change(cur: float, prev: float) -> float | None:
    if prev == 0:
        return 0.0 if cur == 0 else None
    return round(((cur - prev) / abs(prev)) * 100.0, 2)


def _unit_row(
    f: FilialDailyAudit,
    *,
    prev: FilialDailyAudit | None,
    meta: float,
    atencao: float,
    media_desp_rede: float,
) -> dict[str, Any]:
    fat = round(float(f.faturamentoTotal or 0), 2)
    desp = round(float(f.despesasTotal or 0), 2)
    litros = round(float(f.volumeLitros or 0), 2)
    abast = int(f.quantidadeAbastecimentos or 0)
    resultado = round(fat - desp, 2)
    margem = round((resultado / fat * 100.0), 2) if fat > 0 else 0.0
    folha = _folha_rs(f)
    ticket = round(fat / abast, 2) if abast > 0 else (round(fat / litros, 4) if litros > 0 else 0.0)
    ticket_tipo = "por_abastecimento" if abast > 0 else ("por_litro" if litros > 0 else "n/d")

    p_fat = float(prev.faturamentoTotal or 0) if prev else 0.0
    p_desp = float(prev.despesasTotal or 0) if prev else 0.0
    p_litros = float(prev.volumeLitros or 0) if prev else 0.0
    p_res = p_fat - p_desp
    p_margem = (p_res / p_fat * 100.0) if p_fat > 0 else 0.0

    status = _status(margem, meta, atencao, fat, desp)
    nome = FILIAL_NAMES.get(int(f.empresaCodigo), f.empresaNome or f"Unidade {f.empresaCodigo}")

    return {
        "unidade_id": int(f.empresaCodigo),
        "nome_unidade": nome,
        "galonagem_litros": litros,
        "faturamento_total_rs": fat,
        "despesas_totais_rs": desp,
        "diferenca_lucro_rs": resultado,
        "resultado_operacional_rs": resultado,
        "margem_percentual": margem,
        "margem_operacional_pct": margem,
        "status_operacional": status,
        "folha_pagamento_rs": folha,
        "qtd_funcionarios": None,  # sem fonte oficial — Sprint 7.1
        "qtd_abastecimentos": abast,
        "ticket_medio_rs": ticket,
        "ticket_medio_tipo": ticket_tipo,
        "volume_por_funcionario": None,
        "faturamento_por_funcionario": None,
        "ebitda_rs": None,
        "crescimento_faturamento_pct": _pct_change(fat, p_fat),
        "crescimento_galonagem_pct": _pct_change(litros, p_litros),
        "crescimento_despesas_pct": _pct_change(desp, p_desp),
        "crescimento_margem_pp": round(margem - p_margem, 2) if prev else None,
        "participacao_despesas_vs_media_rede_pct": (
            round((desp / media_desp_rede - 1.0) * 100.0, 1) if media_desp_rede > 0 else None
        ),
        "despesas_por_categoria": [
            {
                "categoria": c.categoria,
                "categoriaKey": c.categoriaKey or c.categoria,
                "valor": round(float(c.valor or 0), 2),
                "qtd_lancamentos": int(c.qtd_lancamentos or 0),
            }
            for c in (f.despesasPorCategoria or [])
        ],
    }


def _insights(unidades: list[dict[str, Any]]) -> list[str]:
    if len(unidades) < 2:
        return []
    by_fat = sorted(unidades, key=lambda u: u["faturamento_total_rs"], reverse=True)
    by_margem = sorted(unidades, key=lambda u: u["margem_operacional_pct"], reverse=True)
    by_gal = sorted(unidades, key=lambda u: u["galonagem_litros"], reverse=True)
    out: list[str] = []

    a, b = by_gal[0], by_gal[-1]
    if b["galonagem_litros"] > 0:
        delta = (a["galonagem_litros"] / b["galonagem_litros"] - 1) * 100
        desp_delta = (
            (a["despesas_totais_rs"] / b["despesas_totais_rs"] - 1) * 100
            if b["despesas_totais_rs"] > 0
            else 0
        )
        out.append(
            f"{a['nome_unidade']} vendeu {delta:.0f}% mais combustível que {b['nome_unidade']}"
            + (
                f", porém possui despesa operacional {desp_delta:.0f}% superior."
                if desp_delta > 5
                else "."
            )
        )

    best = by_margem[0]
    out.append(
        f"{best['nome_unidade']} lidera a margem operacional da rede "
        f"({best['margem_operacional_pct']:.1f}%)."
    )

    top = by_fat[0]
    if top.get("crescimento_faturamento_pct") is not None:
        g = top["crescimento_faturamento_pct"]
        sinal = "aumentou" if g >= 0 else "retraiu"
        out.append(
            f"{top['nome_unidade']} {sinal} o faturamento em {abs(g):.1f}% "
            f"versus o período anterior."
        )

    risk = [u for u in unidades if u["status_operacional"] == "CRITICO"]
    if risk:
        out.append(
            "Atenção: "
            + ", ".join(u["nome_unidade"] for u in risk)
            + " em status CRÍTICO (margem operacional abaixo do limite)."
        )
    return out[:5]


def _desvios_categoria(unidades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Categorias por unidade X% acima da média da rede."""
    sums: dict[str, list[float]] = {}
    for u in unidades:
        for c in u.get("despesas_por_categoria") or []:
            key = c.get("categoriaKey") or c.get("categoria") or "?"
            sums.setdefault(key, []).append(float(c.get("valor") or 0))

    media: dict[str, float] = {
        k: (sum(v) / len(v) if v else 0.0) for k, v in sums.items()
    }
    alerts: list[dict[str, Any]] = []
    for u in unidades:
        for c in u.get("despesas_por_categoria") or []:
            key = c.get("categoriaKey") or c.get("categoria") or "?"
            val = float(c.get("valor") or 0)
            m = media.get(key, 0.0)
            if m <= 0 or val <= 0:
                continue
            pct = (val / m - 1.0) * 100.0
            if pct >= DESVIO_ALERTA_PCT:
                alerts.append(
                    {
                        "unidade_id": u["unidade_id"],
                        "nome_unidade": u["nome_unidade"],
                        "categoria": c.get("categoria") or key,
                        "valor_rs": round(val, 2),
                        "media_rede_rs": round(m, 2),
                        "desvio_pct": round(pct, 1),
                        "mensagem": (
                            f"{u['nome_unidade']}: {c.get('categoria') or key} está "
                            f"{pct:.0f}% acima da média da rede."
                        ),
                    }
                )
    alerts.sort(key=lambda a: a["desvio_pct"], reverse=True)
    return alerts[:20]


async def _monthly_series(empresa: int, months: int = 12) -> list[dict[str, Any]]:
    """Evolução mensal: galonagem + faturamento (DB local). Despesas = N/D histórico."""
    fuel = FuelVolumetryService()
    today = date.today()
    series: list[dict[str, Any]] = []
    for i in range(months - 1, -1, -1):
        # mês alvo
        y = today.year
        m = today.month - i
        while m <= 0:
            m += 12
            y -= 1
        start = date(y, m, 1)
        end = date(y, m, monthrange(y, m)[1])
        if end > today:
            end = today
        try:
            res = await fuel.build(
                start.isoformat(), end.isoformat(), empresa_codigo=empresa
            )
            fat = 0.0
            litros = 0.0
            for row in res.por_filial or []:
                if int(row.empresa_codigo or 0) == empresa:
                    fat = float(row.valor or 0)
                    litros = float(row.litros or 0)
                    break
            if fat == 0 and litros == 0:
                fat = float(res.total_valor or 0)
                litros = float(res.total_litros or 0)
            series.append(
                {
                    "mes": f"{y:04d}-{m:02d}",
                    "label": start.strftime("%b/%y").capitalize(),
                    "galonagem_litros": round(litros, 2),
                    "faturamento_total_rs": round(fat, 2),
                    "despesas_totais_rs": None,
                    "resultado_operacional_rs": None,
                    "margem_operacional_pct": None,
                    "fonte": res.fonte,
                }
            )
        except Exception as exc:
            LOGGER.warning("units monthly %s-%s emp=%s: %s", y, m, empresa, exc)
            series.append(
                {
                    "mes": f"{y:04d}-{m:02d}",
                    "label": start.strftime("%b/%y").capitalize(),
                    "galonagem_litros": 0.0,
                    "faturamento_total_rs": 0.0,
                    "despesas_totais_rs": None,
                    "resultado_operacional_rs": None,
                    "margem_operacional_pct": None,
                    "fonte": "erro",
                }
            )
    return series


class UnitsPerformanceService:
    def __init__(self) -> None:
        self._audit = DataAuditService()

    async def build_network(
        self,
        data_inicio: str | None,
        data_fim: str | None,
        *,
        meta_margem_pct: float = DEFAULT_META_MARGEM,
        limite_atencao_pct: float = DEFAULT_LIMITE_ATENCAO,
    ) -> dict[str, Any]:
        hoje = date.today().isoformat()
        start = data_inicio or hoje
        end = data_fim or hoje
        p_start, p_end = _prev_period(start, end)

        cur = await self._audit.build(start, end, None)
        try:
            prev = await self._audit.build(p_start, p_end, None)
        except Exception:
            prev = None

        prev_map = {
            int(f.empresaCodigo): f for f in (prev.filiais if prev else [])
        }
        filiais = list(cur.filiais or [])
        # Garante as 3 oficiais mesmo se vazias
        seen = {int(f.empresaCodigo) for f in filiais}
        for code in OFFICIAL_COMPANY_CODES:
            if int(code) not in seen:
                filiais.append(
                    FilialDailyAudit(
                        empresaCodigo=int(code),
                        empresaNome=FILIAL_NAMES.get(int(code), str(code)),
                    )
                )

        desp_vals = [float(f.despesasTotal or 0) for f in filiais if float(f.despesasTotal or 0) > 0]
        media_desp = sum(desp_vals) / len(desp_vals) if desp_vals else 0.0

        unidades = [
            _unit_row(
                f,
                prev=prev_map.get(int(f.empresaCodigo)),
                meta=meta_margem_pct,
                atencao=limite_atencao_pct,
                media_desp_rede=media_desp,
            )
            for f in sorted(filiais, key=lambda x: int(x.empresaCodigo))
        ]

        fat_rede = round(sum(u["faturamento_total_rs"] for u in unidades), 2)
        desp_rede = round(sum(u["despesas_totais_rs"] for u in unidades), 2)
        res_rede = round(fat_rede - desp_rede, 2)
        margem_rede = round((res_rede / fat_rede * 100.0), 2) if fat_rede > 0 else 0.0
        gal_rede = round(sum(u["galonagem_litros"] for u in unidades), 2)

        ranking_lucro = sorted(
            unidades, key=lambda u: u["resultado_operacional_rs"], reverse=True
        )
        ranking_risco = sorted(
            unidades, key=lambda u: (u["margem_operacional_pct"], -u["despesas_totais_rs"])
        )

        return {
            "success": True,
            "periodo": {"inicio": start, "fim": end},
            "periodo_anterior": {"inicio": p_start, "fim": p_end},
            "parametros": {
                "meta_margem_pct": meta_margem_pct,
                "limite_atencao_pct": limite_atencao_pct,
                "metrica": "margem_operacional",
                "formula": "(faturamento - despesas_operacionais) / faturamento * 100",
            },
            "rede": {
                "faturamento_total_rs": fat_rede,
                "despesas_totais_rs": desp_rede,
                "lucro_liquido_global_rs": res_rede,
                "resultado_operacional_rs": res_rede,
                "margem_media_pct": margem_rede,
                "galonagem_total_litros": gal_rede,
                "status_operacional": _status(
                    margem_rede, meta_margem_pct, limite_atencao_pct, fat_rede, desp_rede
                ),
            },
            "unidades": unidades,
            "ranking_mais_lucrativas": [
                {
                    "unidade_id": u["unidade_id"],
                    "nome_unidade": u["nome_unidade"],
                    "resultado_operacional_rs": u["resultado_operacional_rs"],
                    "margem_operacional_pct": u["margem_operacional_pct"],
                }
                for u in ranking_lucro
            ],
            "ranking_maior_risco": [
                {
                    "unidade_id": u["unidade_id"],
                    "nome_unidade": u["nome_unidade"],
                    "margem_operacional_pct": u["margem_operacional_pct"],
                    "status_operacional": u["status_operacional"],
                }
                for u in ranking_risco
            ],
            "insights": _insights(unidades),
            "desvios_categoria": _desvios_categoria(unidades),
            "grafico_barras": [
                {
                    "unidade_id": u["unidade_id"],
                    "nome": u["nome_unidade"],
                    "faturamento": u["faturamento_total_rs"],
                    "despesas": u["despesas_totais_rs"],
                    "resultado": u["resultado_operacional_rs"],
                    "galonagem": u["galonagem_litros"],
                }
                for u in unidades
            ],
            "gerado_em": datetime.now().isoformat(timespec="seconds"),
        }

    async def build_unit_detail(
        self,
        unidade_id: int,
        data_inicio: str | None,
        data_fim: str | None,
        *,
        meta_margem_pct: float = DEFAULT_META_MARGEM,
        limite_atencao_pct: float = DEFAULT_LIMITE_ATENCAO,
    ) -> dict[str, Any]:
        network = await self.build_network(
            data_inicio,
            data_fim,
            meta_margem_pct=meta_margem_pct,
            limite_atencao_pct=limite_atencao_pct,
        )
        unit = next(
            (u for u in network["unidades"] if int(u["unidade_id"]) == int(unidade_id)),
            None,
        )
        if unit is None:
            return {
                "success": False,
                "mensagem": f"Unidade {unidade_id} não encontrada",
                "unidade_id": unidade_id,
            }

        evolucao = await _monthly_series(int(unidade_id), 12)
        # Injeta despesas/margem do período corrente no mês atual da série
        hoje = date.today()
        cur_key = f"{hoje.year:04d}-{hoje.month:02d}"
        for ponto in evolucao:
            if ponto["mes"] == cur_key:
                ponto["despesas_totais_rs"] = unit["despesas_totais_rs"]
                ponto["resultado_operacional_rs"] = unit["resultado_operacional_rs"]
                ponto["margem_operacional_pct"] = unit["margem_operacional_pct"]
                if unit["faturamento_total_rs"] > 0:
                    ponto["faturamento_total_rs"] = unit["faturamento_total_rs"]
                if unit["galonagem_litros"] > 0:
                    ponto["galonagem_litros"] = unit["galonagem_litros"]

        desvios = [
            d for d in network.get("desvios_categoria") or [] if d["unidade_id"] == unidade_id
        ]

        return {
            "success": True,
            "periodo": network["periodo"],
            "parametros": network["parametros"],
            "unidade": unit,
            "evolucao_mensal": evolucao,
            "despesas_por_categoria": unit.get("despesas_por_categoria") or [],
            "desvios": desvios,
            "insights": [
                i for i in network.get("insights") or [] if unit["nome_unidade"] in i
            ]
            or network.get("insights")[:2],
            "rede_resumo": network["rede"],
        }


_svc: UnitsPerformanceService | None = None


def get_units_performance_service() -> UnitsPerformanceService:
    global _svc
    if _svc is None:
        _svc = UnitsPerformanceService()
    return _svc
