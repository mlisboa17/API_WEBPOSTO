"""Painel Tático — status de bicos/ilhas a partir do cache RAM (Sprint 6).

GET /api/v1/executive/audit/pista-live
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from src.services.fraud_detection_engine import (
    OcorrenciaFraudeDTO,
    get_fraud_detection_engine,
)
from src.services.pista_cache_service import get_pista_cache
from src.services.webposto_pista_service import AbastecimentoRestV1

TZ = ZoneInfo("America/Recife")

FILIAIS = {
    5555: "Casa Caiada",
    11495: "VIP",
    74014: "Real Doze",
}


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


def _bomba_of(item: AbastecimentoRestV1) -> int:
    if item.bomba and int(item.bomba) > 0:
        return int(item.bomba)
    bico = max(1, int(item.bico or 1))
    return ((bico - 1) // 2) + 1


def _ilha_of(bomba: int) -> int:
    return ((max(1, bomba) - 1) // 2) + 1


def _retencao_min(data_hora: str) -> int:
    dt = _parse_dt(data_hora)
    if not dt:
        return 0
    now = datetime.now(TZ)
    return max(0, int((now - dt).total_seconds() // 60))


def _index_ocorrencias_by_abast(
    ocorrencias: list[OcorrenciaFraudeDTO],
) -> dict[int, OcorrenciaFraudeDTO]:
    idx: dict[int, OcorrenciaFraudeDTO] = {}
    for o in ocorrencias:
        for d in o.abastecimentosAgrupados or o.detalhes or []:
            aid = int(getattr(d, "idAbastecimento", 0) or 0)
            if aid and aid not in idx:
                idx[aid] = o
    return idx


def _match_ocorrencia(
    item: AbastecimentoRestV1,
    by_id: dict[int, OcorrenciaFraudeDTO],
    ocorrencias: list[OcorrenciaFraudeDTO],
) -> OcorrenciaFraudeDTO | None:
    aid = int(item.idAbastecimento or 0)
    if aid and aid in by_id:
        return by_id[aid]
    emp = int(item.idEmpresa or 0)
    bico = int(item.bico or 0)
    t1 = (item.dataHora or "")[:16]
    for o in ocorrencias:
        if int(o.empresaCodigo or o.postoUnidade or 0) != emp:
            continue
        for d in o.abastecimentosAgrupados or o.detalhes or []:
            if int(getattr(d, "bico", 0) or 0) != bico:
                continue
            dh = str(
                getattr(d, "dataHoraBico", "")
                or getattr(d, "horaBico", "")
                or getattr(d, "dataHora", "")
                or ""
            )
            if t1 and dh[:16] == t1:
                return o
        if (o.dataHoraBico or o.horaBico or o.dataHora or "")[:16] == t1 and bico:
            return o
    return None


def build_pista_live_status(*, empresa_codigo: int | None = None) -> dict[str, Any]:
    """Monta grid Ilha → Bomba → Bicos a partir de pendentes/baixados RAM."""
    snap = get_pista_cache().get_snapshot()
    engine = get_fraud_detection_engine()
    store = engine.get_store()
    ocorrencias = (
        list(store.result.ocorrencias)
        if store.result and store.result.ocorrencias
        else []
    )
    by_abast = _index_ocorrencias_by_abast(ocorrencias)

    pendentes = list(snap.pendentes)
    baixados = list(snap.baixados)
    if empresa_codigo:
        emp = int(empresa_codigo)
        pendentes = [p for p in pendentes if int(p.idEmpresa or 0) == emp]
        baixados = [b for b in baixados if int(b.idEmpresa or 0) == emp]
        ocorrencias = [
            o
            for o in ocorrencias
            if int(o.empresaCodigo or o.postoUnidade or 0) == emp
        ]

    # Último evento por (empresa, bico) — pendente tem prioridade absoluta
    by_bico: dict[tuple[int, int], AbastecimentoRestV1] = {}
    for item in baixados:
        key = (int(item.idEmpresa or 0), int(item.bico or 0))
        if key[1] <= 0:
            continue
        prev = by_bico.get(key)
        if prev is None or (item.dataHora or "") > (prev.dataHora or ""):
            by_bico[key] = item
    for item in pendentes:
        key = (int(item.idEmpresa or 0), int(item.bico or 0))
        if key[1] <= 0:
            continue
        by_bico[key] = item  # sobrescreve — retenção ativa

    # Agrupa
    buckets: dict[tuple[int, int, int], list[dict[str, Any]]] = defaultdict(list)
    total_retencao = 0
    for (emp, bico), item in sorted(by_bico.items(), key=lambda x: (x[0][0], x[0][1])):
        bomba = _bomba_of(item)
        ilha = _ilha_of(bomba)
        is_pendente = str(item.status or "").upper() in {"PENDENTE", "ABERTO", "RETIDO"}
        # Heurística: se está na lista pendentes do snap
        if not is_pendente:
            is_pendente = any(
                int(p.idAbastecimento or 0) == int(item.idAbastecimento or 0)
                for p in pendentes
            )
        status = "RETENCAO" if is_pendente else "NORMAL"
        if status == "RETENCAO":
            total_retencao += 1
        occ = _match_ocorrencia(item, by_abast, ocorrencias)
        ret_min = _retencao_min(item.dataHora) if status == "RETENCAO" else 0
        buckets[(emp, ilha, bomba)].append(
            {
                "bico": bico,
                "bomba": bomba,
                "ilha": ilha,
                "status": status,
                "idAbastecimento": int(item.idAbastecimento or 0),
                "uuid": item.uuid or "",
                "empresaCodigo": emp,
                "empresaNome": FILIAIS.get(emp, item.nomeEmpresa or f"Filial {emp}"),
                "dataHoraT1": item.dataHora or "",
                "valorPendente": round(float(item.valorTotal or 0), 2)
                if status == "RETENCAO"
                else 0.0,
                "valorUltimo": round(float(item.valorTotal or 0), 2),
                "litros": round(float(item.litros or 0), 3),
                "produto": item.descricaoProduto or "Combustível",
                "frentistaNome": item.nomeFrentista or "N/I",
                "frentistaId": item.idFrentista,
                "tempoRetencaoMinutos": ret_min,
                "formaPagamento": item.formaPagamento or "",
                "ocorrenciaId": (occ.idOcorrencia or occ.id) if occ else None,
                "scoreGravidade": int(occ.scoreGravidade) if occ else None,
                "cartaoRepetido": bool(occ.cartaoRepetido) if occ else False,
            }
        )

    # Estrutura ilhas
    by_emp_ilha: dict[tuple[int, int], dict[int, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for (emp, ilha, bomba), bicos in buckets.items():
        by_emp_ilha[(emp, ilha)][bomba] = sorted(bicos, key=lambda b: b["bico"])

    filiais_out: list[dict[str, Any]] = []
    for emp in sorted({k[0] for k in by_emp_ilha}):
        ilhas_out: list[dict[str, Any]] = []
        ilha_keys = sorted(i for e, i in by_emp_ilha if e == emp)
        for ilha in ilha_keys:
            bombas_map = by_emp_ilha[(emp, ilha)]
            bombas_out = [
                {
                    "bomba": bomba,
                    "bicos": bombas_map[bomba],
                    "retencoes": sum(
                        1 for b in bombas_map[bomba] if b["status"] == "RETENCAO"
                    ),
                }
                for bomba in sorted(bombas_map)
            ]
            ilhas_out.append(
                {
                    "ilha": ilha,
                    "label": f"Ilha {ilha}",
                    "bombas": bombas_out,
                    "retencoes": sum(b["retencoes"] for b in bombas_out),
                }
            )
        filiais_out.append(
            {
                "empresaCodigo": emp,
                "empresaNome": FILIAIS.get(emp, f"Filial {emp}"),
                "ilhas": ilhas_out,
                "totalBicos": sum(
                    len(b["bicos"]) for il in ilhas_out for b in il["bombas"]
                ),
                "totalRetencoes": sum(il["retencoes"] for il in ilhas_out),
            }
        )

    return {
        "success": True,
        "fromCache": True,
        "fonte": "PistaCache+FraudEngine",
        "endpoint": "/api/v1/executive/audit/pista-live",
        "dataRef": snap.data_ref,
        "ultimaSincronizacaoIso": snap.ultima_sincronizacao_iso,
        "syncing": snap.syncing,
        "empresaCodigo": empresa_codigo,
        "totalBicos": sum(f["totalBicos"] for f in filiais_out),
        "totalRetencoes": total_retencao,
        "filiais": filiais_out,
        "observacoes": list(snap.observacoes or ()),
    }
