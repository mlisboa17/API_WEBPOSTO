"""LOGOS Rush Intelligence / Mapa de Calor Operacional V3.

Engine determinístico em RAM (<25ms) sobre AbastecimentoRestV1 (pista_cache).
Proxies autorizados: pressão de pista, TMA, ocupação de bicos, sequência de baixas.
NÃO inventa contagem de veículos parados (sem sensor/câmera).
NÃO usa queda coletiva de vazão para suavizar baixa produtividade individual.
"""

from __future__ import annotations

import logging
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from src.services.pista_cache_service import get_pista_cache
from src.services.webposto_pista_service import AbastecimentoRestV1

LOGGER = logging.getLogger(__name__)
TZ = ZoneInfo("America/Recife")

# ── Data Audit (RUSH_HEATMAP_DATA_AUDIT) ─────────────────────────────────────
DATA_AUDIT_FIELDS: dict[str, str] = {
    "abastecimentos": "AVAILABLE",
    "bico": "AVAILABLE",
    "bomba": "DERIVABLE",  # item.bomba ou ((bico-1)//2)+1
    "ilha": "DERIVABLE",  # ((bomba-1)//2)+1
    "combustivel": "AVAILABLE",  # descricaoProduto
    "frentista_id": "AVAILABLE",
    "frentista_nome": "AVAILABLE",
    "t1_puxada": "AVAILABLE",  # dataHora
    "t2_baixa": "AVAILABLE",  # dataHoraBaixa (baixados)
    "status_pendente": "AVAILABLE",
    "veiculos_parados_fila": "NOT AVAILABLE",  # sem sensor/câmera
    "pressao_pista": "PROXY",  # taxa de baixas / ocupação bicos
    "tma_ciclo": "DERIVABLE",  # T2-T1
    "ocupacao_bicos": "DERIVABLE",
    "sequencia_baixas": "DERIVABLE",
    "vazao_bomba_individual": "NOT AVAILABLE",
    "vazao_coletiva_rush": "NOT AVAILABLE",  # proibido suavizar produtividade
}

FILIAIS = {5555: "AP Casa Caiada", 11495: "Posto VIP", 74014: "Real Doze"}

# Thresholds
RUSH_MIN_ABS_PER_WINDOW = 8
RUSH_MIN_RATE_PER_HOUR = 20.0
LOW_PROD_RATIO = 0.45  # <45% da mediana da equipe no rush
RECURRENCE_WINDOW = 5
RECURRENCE_THRESHOLD = 3
ISLAND_HIGH_OCC = 0.85
ISLAND_LOW_OCC = 0.40
SHORT_SHIFT_MIN_FOR_RATE_EXCUSE = 25  # min ativos — Teste 6


@dataclass(frozen=True)
class FuelEvent:
    """Evento normalizado de abastecimento para o engine."""

    id: int
    empresa: int
    bico: int
    bomba: int
    ilha: int
    combustivel: str
    frentista_id: int | None
    frentista_nome: str
    t1: datetime
    t2: datetime | None
    litros: float
    valor: float
    pendente: bool


@dataclass
class RushWindow:
    empresa: int
    start: datetime
    end: datetime
    event_ids: list[int] = field(default_factory=list)
    label: str = ""


def _parse_dt(raw: str | None) -> datetime | None:
    if not raw:
        return None
    text = str(raw).strip().replace("Z", "+00:00")
    if " " in text and "T" not in text:
        text = text.replace(" ", "T", 1)
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ)


def bomba_of(bico: int, bomba: int | None = None) -> int:
    if bomba and int(bomba) > 0:
        return int(bomba)
    return ((max(1, int(bico or 1)) - 1) // 2) + 1


def ilha_of(bomba: int) -> int:
    return ((max(1, bomba) - 1) // 2) + 1


def events_from_abastecimentos(
    items: Iterable[AbastecimentoRestV1],
) -> list[FuelEvent]:
    out: list[FuelEvent] = []
    for it in items:
        t1 = _parse_dt(it.dataHora)
        if not t1:
            continue
        bico = int(it.bico or 0)
        if bico <= 0:
            continue
        bomba = bomba_of(bico, it.bomba)
        pendente = str(it.status or "").upper() in {"PENDENTE", "ABERTO", "RETIDO"}
        out.append(
            FuelEvent(
                id=int(it.idAbastecimento or 0),
                empresa=int(it.idEmpresa or 0),
                bico=bico,
                bomba=bomba,
                ilha=ilha_of(bomba),
                combustivel=(it.descricaoProduto or "Combustível").strip(),
                frentista_id=it.idFrentista,
                frentista_nome=(it.nomeFrentista or "N/I").strip() or "N/I",
                t1=t1,
                t2=_parse_dt(it.dataHoraBaixa),
                litros=float(it.litros or 0),
                valor=float(it.valorTotal or 0),
                pendente=pendente,
            )
        )
    return out


def calculate_heat_score(
    severidade: float,
    duracao_minutos: float,
    recurrence_score: float = 0.0,
    rush_factor: float = 1.0,
) -> float:
    """HeatScore = Severidade × ln(1+Duração) × (1+Recurrence) × RushFactor."""
    sev = max(0.0, float(severidade))
    dur = max(0.0, float(duracao_minutos))
    rec = max(0.0, float(recurrence_score))
    rf = max(0.0, float(rush_factor))
    score = sev * math.log(1.0 + dur) * (1.0 + rec) * rf
    return round(score, 2)


def heat_color(score: float) -> str:
    if score < 20:
        return "GREEN"
    if score < 40:
        return "YELLOW"
    if score < 60:
        return "ORANGE"
    if score < 85:
        return "RED"
    return "RED_HOT"


def detect_rush(
    events: list[FuelEvent],
    *,
    window_minutes: int = 30,
    min_abs: int = RUSH_MIN_ABS_PER_WINDOW,
    min_rate_per_hour: float = RUSH_MIN_RATE_PER_HOUR,
) -> list[RushWindow]:
    """Janelas de alto fluxo por empresa (taxa de T1)."""
    by_emp: dict[int, list[FuelEvent]] = defaultdict(list)
    for e in events:
        by_emp[e.empresa].append(e)

    rushes: list[RushWindow] = []
    step = timedelta(minutes=max(5, window_minutes // 2))
    win = timedelta(minutes=window_minutes)

    for emp, rows in by_emp.items():
        rows = sorted(rows, key=lambda x: x.t1)
        if not rows:
            continue
        t0 = rows[0].t1
        t_end = rows[-1].t1
        cursor = t0
        while cursor <= t_end:
            w_end = cursor + win
            bucket = [e for e in rows if cursor <= e.t1 < w_end]
            n = len(bucket)
            rate = n * (60.0 / window_minutes)
            if n >= min_abs or rate >= min_rate_per_hour:
                rushes.append(
                    RushWindow(
                        empresa=emp,
                        start=cursor,
                        end=w_end,
                        event_ids=[e.id for e in bucket],
                        label=f"{cursor.strftime('%H:%M')}-{w_end.strftime('%H:%M')}",
                    )
                )
            cursor += step

    # Merge overlapping windows same empresa
    rushes.sort(key=lambda r: (r.empresa, r.start))
    merged: list[RushWindow] = []
    for r in rushes:
        if (
            merged
            and merged[-1].empresa == r.empresa
            and r.start <= merged[-1].end
        ):
            prev = merged[-1]
            ids = list(dict.fromkeys(prev.event_ids + r.event_ids))
            merged[-1] = RushWindow(
                empresa=prev.empresa,
                start=prev.start,
                end=max(prev.end, r.end),
                event_ids=ids,
                label=f"{prev.start.strftime('%H:%M')}-{max(prev.end, r.end).strftime('%H:%M')}",
            )
        else:
            merged.append(r)
    return merged


def calculate_attendant_productivity(
    events: list[FuelEvent],
    *,
    rush: RushWindow | None = None,
) -> list[dict[str, Any]]:
    """Produtividade absoluta e relativa (abast, L, R$, /hora, TMA, % equipe)."""
    scoped = events
    if rush:
        ids = set(rush.event_ids)
        scoped = [e for e in events if e.id in ids] or [
            e for e in events if rush.start <= e.t1 < rush.end and e.empresa == rush.empresa
        ]

    by_f: dict[tuple[int | None, str], list[FuelEvent]] = defaultdict(list)
    for e in scoped:
        key = (e.frentista_id, e.frentista_nome)
        by_f[key].append(e)

    total_abs = sum(len(v) for v in by_f.values()) or 1
    rows: list[dict[str, Any]] = []

    for (fid, nome), evs in by_f.items():
        evs = sorted(evs, key=lambda x: x.t1)
        abs_n = len(evs)
        litros = sum(e.litros for e in evs)
        valor = sum(e.valor for e in evs)
        t_first = evs[0].t1
        t_last = evs[-1].t1
        active_min = max(1.0, (t_last - t_first).total_seconds() / 60.0)
        # se só 1 abast, assume 1 ciclo mínimo 5 min
        if abs_n == 1:
            active_min = max(active_min, 5.0)
        hours = active_min / 60.0
        tmas: list[float] = []
        for e in evs:
            if e.t2 and e.t2 >= e.t1:
                tmas.append((e.t2 - e.t1).total_seconds() / 60.0)
        tma = sum(tmas) / len(tmas) if tmas else 0.0
        rows.append(
            {
                "frentista_id": fid,
                "frentista_nome": nome,
                "empresa": evs[0].empresa,
                "abastecimentos": abs_n,
                "litros": round(litros, 3),
                "valor_rs": round(valor, 2),
                "minutos_ativos": round(active_min, 1),
                "abastecimentos_hora": round(abs_n / hours, 2),
                "litros_hora": round(litros / hours, 2),
                "tma_minutos": round(tma, 2),
                "participacao_equipe_pct": round(100.0 * abs_n / total_abs, 1),
                "ilhas": sorted({e.ilha for e in evs}),
            }
        )

    rows.sort(key=lambda r: (-r["abastecimentos"], -r["litros"]))
    return rows


def calculate_island_pressure(
    events: list[FuelEvent],
    *,
    empresa: int,
    rush: RushWindow | None = None,
    known_bicos_per_ilha: dict[int, int] | None = None,
) -> list[dict[str, Any]]:
    scoped = [
        e
        for e in events
        if e.empresa == empresa
        and (
            rush is None
            or e.id in set(rush.event_ids)
            or (rush.start <= e.t1 < rush.end)
        )
    ]
    by_ilha: dict[int, list[FuelEvent]] = defaultdict(list)
    bicos_seen: dict[int, set[int]] = defaultdict(set)
    for e in scoped:
        by_ilha[e.ilha].append(e)
        bicos_seen[e.ilha].add(e.bico)

    # pendentes = proxy de ocupação ativa
    pend_by_ilha: dict[int, set[int]] = defaultdict(set)
    for e in events:
        if e.empresa != empresa or not e.pendente:
            continue
        pend_by_ilha[e.ilha].add(e.bico)

    all_ilhas = sorted(set(by_ilha) | set(bicos_seen) | set(pend_by_ilha) | {1, 2, 3})
    out: list[dict[str, Any]] = []
    for ilha in all_ilhas:
        capacity = (
            known_bicos_per_ilha.get(ilha)
            if known_bicos_per_ilha
            else max(2, len(bicos_seen.get(ilha, set())) or 2)
        )
        occ_n = len(pend_by_ilha.get(ilha, set()))
        # pressão também via volume de eventos no rush
        n_ev = len(by_ilha.get(ilha, []))
        util_events = min(1.0, n_ev / max(1.0, capacity * 4.0))
        util_occ = occ_n / capacity if capacity else 0.0
        util = max(util_events, util_occ)
        out.append(
            {
                "ilha": ilha,
                "capacidade_bicos": capacity,
                "bicos_ocupados_proxy": occ_n,
                "abastecimentos_janela": n_ev,
                "utilizacao": round(util, 3),
                "frentistas": sorted(
                    {
                        e.frentista_nome
                        for e in by_ilha.get(ilha, [])
                        if e.frentista_nome and e.frentista_nome != "N/I"
                    }
                ),
            }
        )
    return out


def calculate_forecourt_imbalance(island_pressure: list[dict[str, Any]]) -> float:
    """Índice 0–1: desvio entre utilização máx e mín das ilhas ativas."""
    if not island_pressure:
        return 0.0
    utils = [float(i["utilizacao"]) for i in island_pressure]
    if len(utils) < 2:
        return 0.0
    return round(max(utils) - min(utils), 3)


def _median(vals: list[float]) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    if n % 2:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0


def diagnose_suspicions(
    *,
    empresa: int,
    rush: RushWindow,
    productivity: list[dict[str, Any]],
    island_pressure: list[dict[str, Any]],
    events: list[FuelEvent],
    recurrence_hits: dict[str, int] | None = None,
    structural_bicos_total: int | None = None,
) -> list[dict[str, Any]]:
    """Matriz de diagnóstico — regras determinísticas (testes 1–6)."""
    suspicions: list[dict[str, Any]] = []
    recurrence_hits = recurrence_hits or {}
    imbalance = calculate_forecourt_imbalance(island_pressure)

    # STRUCTURAL_SATURATION — todos bicos compatíveis ocupados (proxy pendentes)
    pend = [e for e in events if e.empresa == empresa and e.pendente]
    all_bicos = {e.bico for e in events if e.empresa == empresa}
    occupied = {e.bico for e in pend}
    capacity = structural_bicos_total or max(len(all_bicos), 1)
    sat_ratio = len(occupied) / capacity if capacity else 0.0
    structural = sat_ratio >= 0.99 and capacity >= 2 and len(occupied) >= capacity

    if structural:
        score = calculate_heat_score(90, max(5.0, (rush.end - rush.start).total_seconds() / 60), 0, 1.3)
        suspicions.append(
            {
                "type": "STRUCTURAL_SATURATION",
                "severity": "RED_HOT" if score >= 85 else "RED",
                "subject_type": "FORECOURT",
                "subject_id": str(empresa),
                "subject_name": FILIAIS.get(empresa, f"Unidade {empresa}"),
                "heat_score": score,
                "evidence": {
                    "bicos_ocupados": len(occupied),
                    "capacidade": capacity,
                    "ocupacao_pct": round(100 * sat_ratio, 1),
                    "nota": "Saturação estrutural — não culpar direcionamento/frentista",
                },
                "recurrence": 0,
                "recommendation": (
                    "Estrutura saturada: avaliar abertura de bicos/ilhas ou "
                    "capacidade hidráulica. Não acionar coaching individual."
                ),
            }
        )
        # Em saturação estrutural, não emitir suspeitas de direcionamento
        return suspicions

    # Produtividade no rush
    abs_vals = [float(p["abastecimentos"]) for p in productivity]
    med = _median(abs_vals) if abs_vals else 0.0
    top_abs = max(abs_vals) if abs_vals else 0.0
    rates = [float(p["abastecimentos_hora"]) for p in productivity]
    med_rate = _median(rates) if rates else 0.0
    peers = sorted(productivity, key=lambda x: -x["abastecimentos"])
    top_peer = peers[0] if peers else None

    for p in productivity:
        nome = p["frentista_nome"]
        abs_n = int(p["abastecimentos"])
        rate = float(p["abastecimentos_hora"])
        mins = float(p["minutos_ativos"])
        key = f"{empresa}:{p['frentista_id'] or nome}"
        rec = int(recurrence_hits.get(key, 0))

        # Contraste vs líder da equipe (ex.: 28 × 9)
        low_abs = (
            top_abs >= 3
            and abs_n < top_abs
            and abs_n <= top_abs * LOW_PROD_RATIO
        )
        if not low_abs or top_peer is None:
            continue

        # Teste 6: turno curto + taxa/hora competitiva → absoluto menor OK, sem card
        top_mins = float(top_peer["minutos_ativos"] or 1)
        high_rate = med_rate > 0 and rate >= med_rate * 0.9
        short_vs_leader = mins <= 35 and mins < top_mins * 0.65
        if short_vs_leader and high_rate:
            continue

        top = top_peer
        evidence = {
            "absoluto": abs_n,
            "referencia_equipe_max": int(top["abastecimentos"]),
            "comparativo_absoluto": f"{int(top['abastecimentos'])} × {abs_n}",
            "mediana_equipe": med,
            "abastecimentos_hora": rate,
            "minutos_ativos": mins,
            "rush": rush.label,
        }

        if rec >= RECURRENCE_THRESHOLD:
            # Reincidente → faixa vermelha (60–84) ou quente (≥85)
            score = calculate_heat_score(
                70, min(mins, 30), rec / RECURRENCE_WINDOW, 1.15
            )
            score = max(60.0, min(score, 95.0))
            suspicions.append(
                {
                    "type": "RECURRING_LOW_RUSH_PRODUCTIVITY",
                    "severity": "RED_HOT" if score >= 85 else "RED",
                    "subject_type": "ATTENDANT",
                    "subject_id": str(p["frentista_id"] or nome),
                    "subject_name": nome,
                    "heat_score": score,
                    "evidence": {**evidence, "recurrence_hits": rec, "window": RECURRENCE_WINDOW},
                    "recurrence": rec,
                    "recommendation": (
                        f"Baixa produtividade reincidente ({rec}/{RECURRENCE_WINDOW} rushes). "
                        f"Comparativo absoluto {evidence['comparativo_absoluto']}. "
                        "Agendar coaching e revisão de posicionamento."
                    ),
                }
            )
        else:
            # Padrão isolado → sempre Laranja (40–59)
            score = calculate_heat_score(40, min(mins, 20), 0.0, 1.0)
            score = min(max(score, 40.0), 59.0)
            suspicions.append(
                {
                    "type": "LOW_RUSH_PRODUCTIVITY",
                    "severity": "ORANGE",
                    "subject_type": "ATTENDANT",
                    "subject_id": str(p["frentista_id"] or nome),
                    "subject_name": nome,
                    "heat_score": score,
                    "evidence": evidence,
                    "recurrence": rec,
                    "recommendation": (
                        f"Produção inferior no rush ({evidence['comparativo_absoluto']}). "
                        "Verificar posicionamento e tempo ativo antes de disciplinar."
                    ),
                }
            )

    # POOR_OPERATIONAL_POSITIONING + VEHICLE_DIRECTION
    high = [i for i in island_pressure if float(i["utilizacao"]) >= ISLAND_HIGH_OCC]
    low = [i for i in island_pressure if float(i["utilizacao"]) <= ISLAND_LOW_OCC]
    if high and low and imbalance >= 0.45:
        h, lo = high[0], low[0]
        has_attendant_idle = bool(lo.get("frentistas"))
        free_bicos = int(lo["capacidade_bicos"]) - int(lo["bicos_ocupados_proxy"])
        if has_attendant_idle and free_bicos > 0:
            score = calculate_heat_score(70, 20, 0.2, 1.15)
            suspicions.append(
                {
                    "type": "POOR_OPERATIONAL_POSITIONING",
                    "severity": "RED",
                    "subject_type": "ISLAND",
                    "subject_id": f"{h['ilha']}→{lo['ilha']}",
                    "subject_name": f"Ilha {h['ilha']} saturada × Ilha {lo['ilha']} ociosa",
                    "heat_score": score,
                    "evidence": {
                        "ilha_alta": h,
                        "ilha_baixa": lo,
                        "imbalance": imbalance,
                        "frentistas_ilha_ociosa": lo.get("frentistas"),
                    },
                    "recurrence": 0,
                    "recommendation": (
                        "Reposicionar frentista/demanda da ilha saturada para a ociosa. "
                        "Rebalancear posicionamento operacional."
                    ),
                }
            )
            # VEHICLE_DIRECTION_FAILURE — demanda na alta, livre na baixa com frentista
            score2 = calculate_heat_score(72, 15, 0.1, 1.2)
            suspicions.append(
                {
                    "type": "VEHICLE_DIRECTION_FAILURE_SUSPECTED",
                    "severity": "RED",
                    "subject_type": "FORECOURT",
                    "subject_id": str(empresa),
                    "subject_name": FILIAIS.get(empresa, f"Unidade {empresa}"),
                    "heat_score": score2,
                    "evidence": {
                        "proxy": "pressao_pista_sem_contagem_veiculos",
                        "ilha_demanda": h["ilha"],
                        "ilha_livre": lo["ilha"],
                        "bico_livre": free_bicos > 0,
                        "frentista_na_ilha_livre": True,
                        "nota": "Proxy: sequência de baixas concentrada na ilha saturada",
                    },
                    "recurrence": 0,
                    "recommendation": (
                        "Suspeita de falha de direcionamento de veículos: há frentista "
                        "e bico livre na ilha ociosa com pressão na ilha saturada. "
                        "Orientar sinalização/condução de fila."
                    ),
                }
            )

    # HUMAN_CAPACITY_BOTTLENECK — bicos livres, demanda alta, poucos frentistas
    active_att = {
        p["frentista_nome"]
        for p in productivity
        if p["frentista_nome"] and p["frentista_nome"] != "N/I"
    }
    free_total = sum(
        max(0, int(i["capacidade_bicos"]) - int(i["bicos_ocupados_proxy"]))
        for i in island_pressure
    )
    demand_high = any(float(i["utilizacao"]) >= ISLAND_HIGH_OCC for i in island_pressure) or len(
        rush.event_ids
    ) >= RUSH_MIN_ABS_PER_WINDOW
    if demand_high and free_total >= 2 and len(active_att) <= 1 and not structural:
        score = calculate_heat_score(68, 25, 0, 1.1)
        suspicions.append(
            {
                "type": "HUMAN_CAPACITY_BOTTLENECK",
                "severity": "RED",
                "subject_type": "FORECOURT",
                "subject_id": str(empresa),
                "subject_name": FILIAIS.get(empresa, f"Unidade {empresa}"),
                "heat_score": score,
                "evidence": {
                    "frentistas_ativos": len(active_att),
                    "bicos_livres_proxy": free_total,
                    "demanda_alta": True,
                },
                "recurrence": 0,
                "recommendation": "Reforçar equipe na pista — gargalo de capacidade humana.",
            }
        )

    return suspicions


# Histórico de recorrência em RAM (frentista × rush hits)
_RECURRENCE: dict[str, list[str]] = defaultdict(list)
_INTERVENTIONS: list[dict[str, Any]] = []


def _track_recurrence(empresa: int, productivity: list[dict[str, Any]], rush_id: str) -> dict[str, int]:
    """Atualiza hits de baixa produtividade; retorna contagem nos últimos N rushes."""
    abs_vals = [float(p["abastecimentos"]) for p in productivity]
    med = _median(abs_vals)
    hits: dict[str, int] = {}
    for p in productivity:
        key = f"{empresa}:{p['frentista_id'] or p['frentista_nome']}"
        low = med > 0 and p["abastecimentos"] <= med * LOW_PROD_RATIO
        hist = _RECURRENCE[key]
        if low:
            if rush_id not in hist:
                hist.append(rush_id)
            _RECURRENCE[key] = hist[-RECURRENCE_WINDOW:]
        hits[key] = sum(1 for _ in _RECURRENCE[key][-RECURRENCE_WINDOW:])
    return hits


def _coerce_window(
    inicio: datetime | str | None,
    fim: datetime | str | None,
) -> tuple[datetime | None, datetime | None]:
    start = inicio if isinstance(inicio, datetime) else _parse_dt(str(inicio) if inicio else None)
    end = fim if isinstance(fim, datetime) else _parse_dt(str(fim) if fim else None)
    if start and end and end <= start:
        end = start + timedelta(hours=2)
    return start, end


def build_rush_heatmap(
    *,
    empresa_codigo: int | None = None,
    events: list[FuelEvent] | None = None,
    periodo_inicio: datetime | str | None = None,
    periodo_fim: datetime | str | None = None,
) -> dict[str, Any]:
    """Monta payload completo a partir do cache RAM (ou eventos injetados p/ testes).

    Com periodo_inicio/fim a análise usa a janela do usuário (Rush Alvo).
    """
    t0 = time.perf_counter()
    data_audit = dict(DATA_AUDIT_FIELDS)
    win_start, win_end = _coerce_window(periodo_inicio, periodo_fim)
    forced_window = win_start is not None and win_end is not None

    if events is None:
        snap = get_pista_cache().get_snapshot()
        raw = list(snap.baixados) + list(snap.pendentes)
        events = events_from_abastecimentos(raw)
        sync_iso = snap.ultima_sincronizacao_iso
    else:
        sync_iso = datetime.now(TZ).isoformat()

    if empresa_codigo:
        events = [e for e in events if e.empresa == int(empresa_codigo)]

    if forced_window and win_start and win_end:
        events = [e for e in events if win_start <= e.t1 < win_end]

    rushes = detect_rush(events)
    # foca no rush mais recente por empresa (ou sintetiza janela do dia)
    by_emp_rush: dict[int, RushWindow] = {}
    for r in rushes:
        prev = by_emp_rush.get(r.empresa)
        if prev is None or r.end > prev.end:
            by_emp_rush[r.empresa] = r

    empresas = sorted({e.empresa for e in events} | set(by_emp_rush))
    if empresa_codigo:
        empresas = [int(empresa_codigo)]
    elif forced_window:
        empresas = sorted(set(empresas) | set(FILIAIS.keys()))

    posts: list[dict[str, Any]] = []
    all_suspicions: list[dict[str, Any]] = []

    for emp in empresas:
        emp_events = [e for e in events if e.empresa == emp]
        if forced_window and win_start and win_end:
            rush = RushWindow(
                empresa=emp,
                start=win_start,
                end=win_end,
                event_ids=[e.id for e in emp_events],
                label=f"{win_start.strftime('%H:%M')}-{win_end.strftime('%H:%M')}",
            )
        else:
            rush = by_emp_rush.get(emp)
            if rush is None and emp_events:
                # janela sintética das últimas 2h
                tmax = max(e.t1 for e in emp_events)
                rush = RushWindow(
                    empresa=emp,
                    start=tmax - timedelta(hours=2),
                    end=tmax + timedelta(minutes=1),
                    event_ids=[
                        e.id
                        for e in emp_events
                        if e.t1 >= tmax - timedelta(hours=2)
                    ],
                    label="JANELA_2H",
                )

        if rush is None:
            if not forced_window or not win_start or not win_end:
                continue
            rush = RushWindow(
                empresa=emp,
                start=win_start,
                end=win_end,
                event_ids=[],
                label=f"{win_start.strftime('%H:%M')}-{win_end.strftime('%H:%M')}",
            )

        prod = calculate_attendant_productivity(emp_events, rush=rush)
        islands = calculate_island_pressure(emp_events, empresa=emp, rush=rush)
        imbalance = calculate_forecourt_imbalance(islands)
        rush_id = f"{emp}:{rush.start.isoformat()}:{rush.end.isoformat()}"
        rec_hits = _track_recurrence(emp, prod, rush_id)
        suspicions = diagnose_suspicions(
            empresa=emp,
            rush=rush,
            productivity=prod,
            island_pressure=islands,
            events=emp_events,
            recurrence_hits=rec_hits,
        )
        all_suspicions.extend(suspicions)

        # heat do posto = max das suspeitas (sem card verde)
        max_score = max((s["heat_score"] for s in suspicions), default=0.0)
        color = heat_color(max_score) if max_score >= 20 else "GREEN"

        posts.append(
            {
                "unidade_id": emp,
                "nome_unidade": FILIAIS.get(emp, f"Unidade {emp}"),
                "rush_status": {
                    "active": True,
                    "label": rush.label,
                    "start": rush.start.isoformat(),
                    "end": rush.end.isoformat(),
                    "abastecimentos": len(rush.event_ids),
                    "modo": "RUSH_ALVO" if forced_window else "AUTO",
                },
                "heat_score": max_score,
                "heat_color": color,
                "forecourt_imbalance_score": imbalance,
                "island_pressure": islands,
                "ranking_absoluto": [
                    {
                        "pos": i + 1,
                        "frentista_id": p["frentista_id"],
                        "frentista_nome": p["frentista_nome"],
                        "abastecimentos": p["abastecimentos"],
                        "litros": p["litros"],
                        "valor_rs": p["valor_rs"],
                        "comparativo": (
                            f"{prod[0]['abastecimentos']} × {p['abastecimentos']}"
                            if prod
                            else str(p["abastecimentos"])
                        ),
                    }
                    for i, p in enumerate(prod)
                ],
                "ranking_relativo": sorted(
                    [
                        {
                            "pos": 0,
                            "frentista_id": p["frentista_id"],
                            "frentista_nome": p["frentista_nome"],
                            "abastecimentos_hora": p["abastecimentos_hora"],
                            "litros_hora": p["litros_hora"],
                            "tma_minutos": p["tma_minutos"],
                            "minutos_ativos": p["minutos_ativos"],
                            "participacao_equipe_pct": p["participacao_equipe_pct"],
                        }
                        for p in prod
                    ],
                    key=lambda x: -x["abastecimentos_hora"],
                ),
                "suspeitas": suspicions,
                "drilldown": {
                    "posto": emp,
                    "ilhas": [i["ilha"] for i in islands],
                    "frentistas": [p["frentista_nome"] for p in prod],
                    "periodo": rush.label,
                    "historico_recorrencia": {
                        f"{p['frentista_nome']}": rec_hits.get(
                            f"{emp}:{p['frentista_id'] or p['frentista_nome']}", 0
                        )
                        for p in prod
                    },
                },
            }
        )
        for i, row in enumerate(posts[-1]["ranking_relativo"]):
            row["pos"] = i + 1

    # Ordenação cards: 🔥 > 🔴 > 🟠 > 🟡 (sem verde)
    sev_order = {"RED_HOT": 0, "RED": 1, "ORANGE": 2, "YELLOW": 3}
    cards = [s for s in all_suspicions if heat_color(s["heat_score"]) != "GREEN"]
    cards.sort(
        key=lambda s: (
            sev_order.get(s["severity"], 9),
            -float(s["heat_score"]),
        )
    )

    latency_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    periodo_analise = None
    if forced_window and win_start and win_end:
        periodo_analise = {
            "inicio": win_start.isoformat(),
            "fim": win_end.isoformat(),
            "label": (
                f"{win_start.strftime('%d/%m/%Y')} das "
                f"{win_start.strftime('%H:%M')} às {win_end.strftime('%H:%M')}"
            ),
            "modo": "RUSH_ALVO",
        }
    elif posts:
        # janela efetiva do primeiro posto
        rs0 = posts[0]["rush_status"]
        periodo_analise = {
            "inicio": rs0["start"],
            "fim": rs0["end"],
            "label": rs0.get("label") or "AUTO",
            "modo": "AUTO",
        }

    return {
        "success": True,
        "fonte": "RushHeatmapEngine+PistaCacheRAM",
        "data_audit": data_audit,
        "latency_ms": latency_ms,
        "ultima_sincronizacao_iso": sync_iso,
        "periodo_analise": periodo_analise,
        "rush_status": {
            "posts_com_rush": len(posts),
            "total_suspeitas": len(cards),
            "modo": "RUSH_ALVO" if forced_window else "AUTO",
        },
        "heat_score_rede": max((p["heat_score"] for p in posts), default=0.0),
        "forecourt_imbalance_score_rede": max(
            (p["forecourt_imbalance_score"] for p in posts), default=0.0
        ),
        "posts": posts,
        "intelligence_cards": cards,
        "regras": {
            "vazao_coletiva": "PROIBIDO_SUAVIZAR_PRODUTIVIDADE_INDIVIDUAL",
            "veiculos_fila": "NOT_AVAILABLE_USE_PROXIES",
            "heat_formula": "Severidade * ln(1+DuracaoMin) * (1+RecurrenceScore) * RushFactor",
        },
    }


def register_intervention(payload: dict[str, Any]) -> dict[str, Any]:
    """Registra intervenção e janela 30 min antes/depois para comparação."""
    now = datetime.now(TZ)
    before_start = now - timedelta(minutes=30)
    after_end = now + timedelta(minutes=30)
    record = {
        "id": f"INT-{int(now.timestamp())}-{len(_INTERVENTIONS)+1}",
        "empresa_codigo": payload.get("empresa_codigo") or payload.get("unidade_id"),
        "tipo": payload.get("tipo") or payload.get("type") or "MANUAL",
        "suspeita_type": payload.get("suspeita_type"),
        "subject_id": payload.get("subject_id"),
        "acao": payload.get("acao") or payload.get("action") or "",
        "operador": payload.get("operador") or "sistema",
        "registrado_em": now.isoformat(),
        "janela_antes": {
            "inicio": before_start.isoformat(),
            "fim": now.isoformat(),
            "minutos": 30,
        },
        "janela_depois": {
            "inicio": now.isoformat(),
            "fim": after_end.isoformat(),
            "minutos": 30,
            "status": "AGUARDANDO",
        },
        "metrics_baseline": payload.get("metrics_baseline") or {},
        "metrics_after": None,
    }
    _INTERVENTIONS.append(record)
    LOGGER.info(
        "pista_intervention id=%s emp=%s tipo=%s",
        record["id"],
        record["empresa_codigo"],
        record["tipo"],
    )
    return record


def list_interventions(empresa_codigo: int | None = None) -> list[dict[str, Any]]:
    rows = list(_INTERVENTIONS)
    if empresa_codigo is not None:
        rows = [r for r in rows if int(r.get("empresa_codigo") or 0) == int(empresa_codigo)]
    return list(reversed(rows))


def reset_engine_state_for_tests() -> None:
    """Limpa RAM de recorrência/intervenções (apenas testes)."""
    _RECURRENCE.clear()
    _INTERVENTIONS.clear()
