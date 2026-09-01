"""Auditoria de Caixas — cálculo em background + leitura 100% RAM (<50ms).

Diferença bico (abastecimentos baixados) × caixa declarado × formas de pagamento.
Publicado a cada ciclo do PistaSyncWorker.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from src.utils.filial_normalizer import resolve_empresa_codigo

LOGGER = logging.getLogger(__name__)
TZ = ZoneInfo("America/Recife")

FILIAIS = {
    5555: "AP CASA CAIADA",
    11495: "POSTO VIP",
    74014: "POSTO REAL / DOZE",
}

FORMAS_ORDEM = (
    "DINHEIRO",
    "PIX",
    "CARTAO_DEBITO",
    "CARTAO_CREDITO",
    "CONVENIO",
    "OUTROS",
)


class ResumoDiaCaixa(BaseModel):
    totalEsperado: float = 0.0
    totalDeclarado: float = 0.0
    divergenciaTotal: float = 0.0
    sobras: float = 0.0
    faltas: float = 0.0
    qtdTurnos: int = 0
    qtdAuditados: int = 0
    qtdPendentes: int = 0
    qtdComDivergencia: int = 0


class FechamentoTurno(BaseModel):
    id: str
    operadorId: int | None = None
    operadorNome: str = "N/I"
    postoCodigo: int = 0
    postoNome: str = ""
    turno: str = ""
    dataRef: str = ""
    # IMUTÁVEIS via API (bico / sistêmico PDV)
    faturamentoBico: float = 0.0
    dinheiro_sistemico: float = 0.0
    pix_sistemico: float = 0.0
    cartao_debito_sistemico: float = 0.0
    cartao_credito_sistemico: float = 0.0
    convenio_sistemico: float = 0.0
    # Auditáveis / alteráveis pela diretoria
    faturamentoCaixa: float = 0.0
    dinheiro_declarado: float = 0.0
    pix_declarado: float = 0.0
    cartao_debito_declarado: float = 0.0
    cartao_credito_declarado: float = 0.0
    convenio_declarado: float = 0.0
    observacao_auditoria: str | None = None
    ajustadoManualmente: bool = False
    saldo: float = 0.0
    status: str = "PENDENTE"  # AUDITADO | PENDENTE
    qtdAbastecimentos: int = 0
    caixaCodigo: int | None = None


class CashierAuditAdjustRequest(BaseModel):
    dinheiro_declarado: float | None = None
    pix_declarado: float | None = None
    cartao_debito_declarado: float | None = None
    cartao_credito_declarado: float | None = None
    convenio_declarado: float | None = None
    observacao_auditoria: str | None = None


class QuebraFormaPagamento(BaseModel):
    forma: str
    label: str
    valorSistemico: float = 0.0
    valorInformado: float = 0.0
    diferenca: float = 0.0


class CashierAuditSnapshot(BaseModel):
    success: bool = True
    fromCache: bool = True
    dataRef: str = ""
    geradoEm: str | None = None
    latencyMs: float = 0.0
    resumoDia: ResumoDiaCaixa = Field(default_factory=ResumoDiaCaixa)
    fechamentosPorTurno: list[FechamentoTurno] = Field(default_factory=list)
    quebrasPorFormaPagamento: list[QuebraFormaPagamento] = Field(default_factory=list)
    observacoes: list[str] = Field(default_factory=list)
    # paginação aplicada na resposta
    pagina: int = 1
    limite: int = 20
    totalFechamentos: int = 0
    hasMore: bool = False


@dataclass
class _RamStore:
    data_ref: str = ""
    gerado_em: str | None = None
    resumo: ResumoDiaCaixa = field(default_factory=ResumoDiaCaixa)
    fechamentos: tuple[FechamentoTurno, ...] = ()
    quebras: tuple[QuebraFormaPagamento, ...] = ()
    observacoes: tuple[str, ...] = ()
    last_error: str | None = None
    last_duration_ms: float = 0.0
    # Overrides de auditoria (sobrevivem ao refresh do worker)
    adjustments: dict[str, dict[str, Any]] = field(default_factory=dict)


def _money(v: Any) -> float:
    try:
        return round(float(v or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def _turno_label(data_hora: str | None) -> str:
    try:
        hh = int(str(data_hora or "")[11:13])
    except (TypeError, ValueError):
        return "TURNO"
    if hh < 14:
        return "MANHÃ"
    if hh < 20:
        return "TARDE"
    return "NOITE"


def _bucket_forma(raw: str | None) -> str:
    u = (raw or "").upper()
    if not u.strip():
        return "OUTROS"
    if "PIX" in u:
        return "PIX"
    if "DINHEIRO" in u or "ESPECIE" in u or "ESPÉCIE" in u or "CASH" in u:
        return "DINHEIRO"
    if "DEBIT" in u or "DÉBIT" in u:
        return "CARTAO_DEBITO"
    if "CREDIT" in u or "CRÉDIT" in u:
        return "CARTAO_CREDITO"
    if "CONVEN" in u or "FROTA" in u or "PRAZO" in u or "A PRAZO" in u:
        return "CONVENIO"
    if any(k in u for k in ("CARTAO", "CARTÃO", "TEF", "POS", "VISA", "MASTER", "ELO", "HIPER")):
        return "CARTAO_CREDITO"
    return "OUTROS"


_FORMA_LABEL = {
    "DINHEIRO": "Dinheiro",
    "PIX": "PIX",
    "CARTAO_DEBITO": "Cartão Débito",
    "CARTAO_CREDITO": "Cartão Crédito",
    "CONVENIO": "Convênio",
    "OUTROS": "Outros",
}


_DECL_FIELDS = (
    "dinheiro_declarado",
    "pix_declarado",
    "cartao_debito_declarado",
    "cartao_credito_declarado",
    "convenio_declarado",
)


def _recalc_fechamento(f: FechamentoTurno) -> FechamentoTurno:
    """Recalcula Δ e status a partir dos declarados (bico permanece imutável)."""
    total_dec = round(
        sum(_money(getattr(f, k)) for k in _DECL_FIELDS),
        2,
    )
    # Se nenhum breakdown foi informado, mantém faturamentoCaixa legado
    if total_dec <= 0 and _money(f.faturamentoCaixa) > 0:
        total_dec = _money(f.faturamentoCaixa)
        if _money(f.dinheiro_declarado) <= 0 and _money(f.dinheiro_sistemico) > 0:
            # proporção sistêmica como baseline editável
            ratio = total_dec / max(_money(f.faturamentoBico), 0.01)
            f.dinheiro_declarado = round(_money(f.dinheiro_sistemico) * ratio, 2)
            f.pix_declarado = round(_money(f.pix_sistemico) * ratio, 2)
            f.cartao_debito_declarado = round(_money(f.cartao_debito_sistemico) * ratio, 2)
            f.cartao_credito_declarado = round(_money(f.cartao_credito_sistemico) * ratio, 2)
            f.convenio_declarado = round(_money(f.convenio_sistemico) * ratio, 2)
            total_dec = round(sum(_money(getattr(f, k)) for k in _DECL_FIELDS), 2)

    f.faturamentoCaixa = total_dec
    f.saldo = round(total_dec - _money(f.faturamentoBico), 2)
    if abs(f.saldo) < 0.01:
        f.status = "AUDITADO"
        f.saldo = 0.0
    elif f.ajustadoManualmente:
        f.status = "PENDENTE"
    return f


class CashierAuditService:
    """Cache RAM de auditoria de caixa — publish atômico."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._store = _RamStore()

    def get_store(self) -> _RamStore:
        return self._store

    async def refresh_from_pista(self) -> _RamStore:
        """Recalcula a partir do cache de pista + CAIXA (só no worker)."""
        t0 = time.perf_counter()
        obs: list[str] = []
        try:
            from src.services.pista_cache_service import get_pista_cache

            snap = get_pista_cache().get_snapshot()
            baixados = list(snap.baixados or [])
            data_ref = snap.data_ref or str(date.today())

            caixas = await self._fetch_caixas(data_ref, data_ref)
            if not caixas:
                obs.append("CAIXA indisponível no ciclo — cruzamento parcial via bico/pagamentos.")

            fechamentos, quebras, resumo = self._build(baixados, caixas, data_ref)
            async with self._lock:
                adjustments = dict(self._store.adjustments or {})
                # Reaplica overrides de auditoria (declarados) sem tocar no bico
                if adjustments:
                    patched: list[FechamentoTurno] = []
                    for f in fechamentos:
                        adj = adjustments.get(f.id)
                        if adj:
                            data = f.model_dump()
                            for k in _DECL_FIELDS:
                                if k in adj and adj[k] is not None:
                                    data[k] = _money(adj[k])
                            if adj.get("observacao_auditoria") is not None:
                                data["observacao_auditoria"] = adj["observacao_auditoria"]
                            data["ajustadoManualmente"] = True
                            f = _recalc_fechamento(FechamentoTurno(**data))
                        patched.append(f)
                    fechamentos = patched
                    quebras, resumo = self._rebuild_aggregates(fechamentos)
                    obs.append(f"Overrides de auditoria reaplicados: {len(adjustments)}")

                duration = (time.perf_counter() - t0) * 1000.0
                self._store = _RamStore(
                    data_ref=data_ref,
                    gerado_em=datetime.now(TZ).isoformat(),
                    resumo=resumo,
                    fechamentos=tuple(fechamentos),
                    quebras=tuple(quebras),
                    observacoes=tuple(obs),
                    last_error=None,
                    last_duration_ms=duration,
                    adjustments=adjustments,
                )
            LOGGER.info(
                "cashier_audit.refresh ok data_ref=%s turnos=%s duration_ms=%.1f",
                data_ref,
                len(fechamentos),
                duration,
            )
            return self._store
        except Exception as exc:
            LOGGER.exception("cashier_audit.refresh falhou: %s", exc)
            async with self._lock:
                prev = self._store
                self._store = _RamStore(
                    data_ref=prev.data_ref,
                    gerado_em=prev.gerado_em,
                    resumo=prev.resumo,
                    fechamentos=prev.fechamentos,
                    quebras=prev.quebras,
                    observacoes=prev.observacoes + (f"refresh_error: {exc}",),
                    last_error=str(exc),
                    last_duration_ms=(time.perf_counter() - t0) * 1000.0,
                    adjustments=dict(prev.adjustments or {}),
                )
                return self._store

    def _rebuild_aggregates(
        self, fechamentos: list[FechamentoTurno]
    ) -> tuple[list[QuebraFormaPagamento], ResumoDiaCaixa]:
        sobras = sum(f.saldo for f in fechamentos if f.saldo > 0)
        faltas = sum(abs(f.saldo) for f in fechamentos if f.saldo < 0)
        esp = sum(f.faturamentoBico for f in fechamentos)
        dec = sum(f.faturamentoCaixa for f in fechamentos)
        formas_sys = {
            "DINHEIRO": sum(f.dinheiro_sistemico for f in fechamentos),
            "PIX": sum(f.pix_sistemico for f in fechamentos),
            "CARTAO_DEBITO": sum(f.cartao_debito_sistemico for f in fechamentos),
            "CARTAO_CREDITO": sum(f.cartao_credito_sistemico for f in fechamentos),
            "CONVENIO": sum(f.convenio_sistemico for f in fechamentos),
        }
        formas_inf = {
            "DINHEIRO": sum(f.dinheiro_declarado for f in fechamentos),
            "PIX": sum(f.pix_declarado for f in fechamentos),
            "CARTAO_DEBITO": sum(f.cartao_debito_declarado for f in fechamentos),
            "CARTAO_CREDITO": sum(f.cartao_credito_declarado for f in fechamentos),
            "CONVENIO": sum(f.convenio_declarado for f in fechamentos),
        }
        quebras: list[QuebraFormaPagamento] = []
        for forma in FORMAS_ORDEM:
            if forma == "OUTROS":
                continue
            sist = round(formas_sys.get(forma, 0.0), 2)
            inf = round(formas_inf.get(forma, 0.0), 2)
            if sist <= 0 and inf <= 0:
                continue
            quebras.append(
                QuebraFormaPagamento(
                    forma=forma,
                    label=_FORMA_LABEL.get(forma, forma),
                    valorSistemico=sist,
                    valorInformado=inf,
                    diferenca=round(inf - sist, 2),
                )
            )
        resumo = ResumoDiaCaixa(
            totalEsperado=round(esp, 2),
            totalDeclarado=round(dec, 2),
            divergenciaTotal=round(dec - esp, 2),
            sobras=round(sobras, 2),
            faltas=round(faltas, 2),
            qtdTurnos=len(fechamentos),
            qtdAuditados=sum(1 for f in fechamentos if f.status == "AUDITADO"),
            qtdPendentes=sum(1 for f in fechamentos if f.status == "PENDENTE"),
            qtdComDivergencia=sum(1 for f in fechamentos if abs(f.saldo) >= 0.01),
        )
        return quebras, resumo

    async def adjust_fechamento(
        self, fechamento_id: str, body: CashierAuditAdjustRequest
    ) -> FechamentoTurno:
        """Altera apenas valores declarados; recalcula Δ e status."""
        async with self._lock:
            items = list(self._store.fechamentos)
            idx = next((i for i, f in enumerate(items) if f.id == fechamento_id), -1)
            if idx < 0:
                raise KeyError(f"Fechamento não encontrado: {fechamento_id}")

            current = items[idx]
            data = current.model_dump()
            payload = body.model_dump(exclude_unset=True)
            adj = dict(self._store.adjustments.get(fechamento_id) or {})

            for k in _DECL_FIELDS:
                if k in payload and payload[k] is not None:
                    data[k] = _money(payload[k])
                    adj[k] = data[k]
            if "observacao_auditoria" in payload:
                data["observacao_auditoria"] = payload["observacao_auditoria"]
                adj["observacao_auditoria"] = payload["observacao_auditoria"]

            data["ajustadoManualmente"] = True
            updated = _recalc_fechamento(FechamentoTurno(**data))
            items[idx] = updated
            quebras, resumo = self._rebuild_aggregates(items)

            adjustments = dict(self._store.adjustments)
            adjustments[fechamento_id] = adj
            self._store = _RamStore(
                data_ref=self._store.data_ref,
                gerado_em=self._store.gerado_em,
                resumo=resumo,
                fechamentos=tuple(items),
                quebras=tuple(quebras),
                observacoes=self._store.observacoes,
                last_error=self._store.last_error,
                last_duration_ms=self._store.last_duration_ms,
                adjustments=adjustments,
            )
            LOGGER.info(
                "cashier_audit.adjust id=%s saldo=%.2f status=%s",
                fechamento_id,
                updated.saldo,
                updated.status,
            )
            return updated

    async def _fetch_caixas(self, inicio: str, fim: str) -> list[dict[str, Any]]:
        try:
            from src.gateway.shared_client import get_webposto_client
            from src.services.caixa_service import CaixaService

            client = get_webposto_client()
            resp = await CaixaService(client).get_caixa(inicio, fim)
            if not resp.success:
                LOGGER.warning("cashier_audit CAIXA falhou: %s", resp.error)
                return []
            data = resp.data
            if isinstance(data, dict):
                rows = data.get("dados") or data.get("data") or data.get("resultados") or []
            elif isinstance(data, list):
                rows = data
            else:
                rows = []
            return [r for r in rows if isinstance(r, dict)]
        except Exception as exc:
            LOGGER.warning("cashier_audit CAIXA exception: %s", exc)
            return []

    def _build(
        self,
        baixados: list[Any],
        caixas: list[dict[str, Any]],
        data_ref: str,
    ) -> tuple[list[FechamentoTurno], list[QuebraFormaPagamento], ResumoDiaCaixa]:
        # Index CAIXA por (empresa, funcionario)
        caixa_by_op: dict[tuple[int, int], dict[str, Any]] = {}
        for cx in caixas:
            emp = int(cx.get("empresaCodigo") or 0)
            fid = int(cx.get("funcionarioCodigo") or cx.get("operadorCodigo") or 0)
            if emp and fid:
                caixa_by_op[(emp, fid)] = cx

        # Agrega bico + pagamentos por (empresa, frentista, turno)
        groups: dict[tuple[int, int | None, str], dict[str, Any]] = defaultdict(
            lambda: {
                "bico": 0.0,
                "qtd": 0,
                "nome": "N/I",
                "formas": defaultdict(float),
            }
        )
        formas_sys: dict[str, float] = defaultdict(float)

        for item in baixados:
            emp = int(getattr(item, "idEmpresa", 0) or 0)
            if not emp:
                continue
            fid = getattr(item, "idFrentista", None)
            try:
                fid_i = int(fid) if fid is not None else None
            except (TypeError, ValueError):
                fid_i = None
            turno = _turno_label(getattr(item, "dataHora", None))
            key = (emp, fid_i, turno)
            valor = _money(getattr(item, "valorTotal", 0))
            groups[key]["bico"] += valor
            groups[key]["qtd"] += 1
            groups[key]["nome"] = (
                str(getattr(item, "nomeFrentista", None) or groups[key]["nome"] or "N/I")
            )
            bucket = _bucket_forma(getattr(item, "formaPagamento", None))
            groups[key]["formas"][bucket] += valor
            formas_sys[bucket] += valor

        fechamentos: list[FechamentoTurno] = []
        sobras = 0.0
        faltas = 0.0
        total_esp = 0.0
        total_dec = 0.0
        auditados = 0
        pendentes = 0
        com_div = 0

        for (emp, fid, turno), g in groups.items():
            bico = round(g["bico"], 2)
            cx = caixa_by_op.get((emp, fid or -1)) if fid else None
            if cx:
                declarado = _money(
                    cx.get("valorInformado")
                    or cx.get("informado")
                    or cx.get("valorFechamento")
                    or cx.get("totalInformado")
                    or cx.get("valorApresentado")
                )
                # se CAIXA não trouxe informado, usa soma de campos de espécie se existirem
                if declarado <= 0:
                    declarado = _money(
                        cx.get("dinheiroInformado")
                        or cx.get("valorDinheiro")
                        or 0
                    ) + _money(cx.get("valorCheque") or 0)
                if declarado <= 0:
                    # fallback: declara = bico (sem divergência sistêmica) mas marca auditado se caixa existe
                    declarado = bico
                status = "AUDITADO"
                caixa_cod = int(cx.get("caixaCodigo") or cx.get("codigo") or 0) or None
                op_nome = str(
                    cx.get("funcionarioNome") or cx.get("operadorNome") or g["nome"] or "N/I"
                )
            else:
                # Sem fechamento de CAIXA: declarado = soma pagamentos sistêmicos (= bico)
                declarado = bico
                status = "PENDENTE"
                caixa_cod = None
                op_nome = g["nome"]

            formas_g: dict[str, float] = g["formas"]
            din_s = round(float(formas_g.get("DINHEIRO", 0)), 2)
            pix_s = round(float(formas_g.get("PIX", 0)), 2)
            deb_s = round(float(formas_g.get("CARTAO_DEBITO", 0)), 2)
            cred_s = round(float(formas_g.get("CARTAO_CREDITO", 0)), 2)
            conv_s = round(float(formas_g.get("CONVENIO", 0)), 2)
            # Declarado inicial: proporcional ao sistêmico (editável depois via PATCH)
            ratio_turno = (declarado / bico) if bico > 0 else 1.0
            ft = FechamentoTurno(
                id=f"CX-{emp}-{fid or 0}-{turno}-{data_ref}",
                operadorId=fid,
                operadorNome=op_nome,
                postoCodigo=emp,
                postoNome=FILIAIS.get(emp, f"Empresa {emp}"),
                turno=turno,
                dataRef=data_ref,
                faturamentoBico=bico,
                dinheiro_sistemico=din_s,
                pix_sistemico=pix_s,
                cartao_debito_sistemico=deb_s,
                cartao_credito_sistemico=cred_s,
                convenio_sistemico=conv_s,
                faturamentoCaixa=round(declarado, 2),
                dinheiro_declarado=round(din_s * ratio_turno, 2),
                pix_declarado=round(pix_s * ratio_turno, 2),
                cartao_debito_declarado=round(deb_s * ratio_turno, 2),
                cartao_credito_declarado=round(cred_s * ratio_turno, 2),
                convenio_declarado=round(conv_s * ratio_turno, 2),
                saldo=0.0,
                status=status,
                qtdAbastecimentos=int(g["qtd"]),
                caixaCodigo=caixa_cod,
            )
            ft = _recalc_fechamento(ft)
            # Sem CAIXA → sempre pendente; com CAIXA e Δ=0 → auditado
            if not cx:
                ft.status = "PENDENTE"
            elif abs(ft.saldo) < 0.01:
                ft.status = "AUDITADO"
            else:
                ft.status = status  # AUDITADO se caixa existe, mesmo com Δ

            if abs(ft.saldo) >= 0.01:
                com_div += 1
            if ft.saldo > 0:
                sobras += ft.saldo
            elif ft.saldo < 0:
                faltas += abs(ft.saldo)

            total_esp += bico
            total_dec += ft.faturamentoCaixa
            if ft.status == "AUDITADO":
                auditados += 1
            else:
                pendentes += 1

            fechamentos.append(ft)

        fechamentos.sort(key=lambda f: (abs(f.saldo), f.faturamentoBico), reverse=True)
        quebras, resumo = self._rebuild_aggregates(fechamentos)
        # Prefer contadores locais se aggregates divergirem por OUTROS
        resumo.qtdAuditados = auditados
        resumo.qtdPendentes = pendentes
        resumo.qtdComDivergencia = com_div
        resumo.sobras = round(sobras, 2)
        resumo.faltas = round(faltas, 2)
        resumo.totalEsperado = round(total_esp, 2)
        resumo.totalDeclarado = round(total_dec, 2)
        resumo.divergenciaTotal = round(total_dec - total_esp, 2)
        return fechamentos, quebras, resumo

    def response(
        self,
        *,
        empresa_codigo: int | None = None,
        pagina: int = 1,
        limite: int = 20,
    ) -> CashierAuditSnapshot:
        """Leitura síncrona 100% RAM — sem I/O."""
        t0 = time.perf_counter()
        store = self._store
        emp = resolve_empresa_codigo(empresa_codigo)

        fechamentos = list(store.fechamentos)
        if emp is not None:
            fechamentos = [f for f in fechamentos if f.postoCodigo == emp]

        pagina = max(1, int(pagina or 1))
        limite = max(1, min(100, int(limite or 20)))
        total = len(fechamentos)
        offset = (pagina - 1) * limite
        page_items = fechamentos[offset : offset + limite]

        # Recalcula resumo filtrado se filial específica
        if emp is not None:
            sobras = sum(f.saldo for f in fechamentos if f.saldo > 0)
            faltas = sum(abs(f.saldo) for f in fechamentos if f.saldo < 0)
            esp = sum(f.faturamentoBico for f in fechamentos)
            dec = sum(f.faturamentoCaixa for f in fechamentos)
            resumo = ResumoDiaCaixa(
                totalEsperado=round(esp, 2),
                totalDeclarado=round(dec, 2),
                divergenciaTotal=round(dec - esp, 2),
                sobras=round(sobras, 2),
                faltas=round(faltas, 2),
                qtdTurnos=len(fechamentos),
                qtdAuditados=sum(1 for f in fechamentos if f.status == "AUDITADO"),
                qtdPendentes=sum(1 for f in fechamentos if f.status == "PENDENTE"),
                qtdComDivergencia=sum(1 for f in fechamentos if abs(f.saldo) >= 0.01),
            )
            # Filtra quebras proporcionalmente pelo peso da filial no bico
            total_rede = store.resumo.totalEsperado or 1.0
            peso = esp / total_rede if total_rede else 0.0
            quebras = [
                QuebraFormaPagamento(
                    forma=q.forma,
                    label=q.label,
                    valorSistemico=round(q.valorSistemico * peso, 2),
                    valorInformado=round(q.valorInformado * peso, 2),
                    diferenca=round(q.diferenca * peso, 2),
                )
                for q in store.quebras
                if q.valorSistemico * peso > 0.009
            ]
        else:
            resumo = store.resumo
            quebras = list(store.quebras)

        latency = (time.perf_counter() - t0) * 1000.0
        return CashierAuditSnapshot(
            success=True,
            fromCache=True,
            dataRef=store.data_ref,
            geradoEm=store.gerado_em,
            latencyMs=round(latency, 3),
            resumoDia=resumo,
            fechamentosPorTurno=page_items,
            quebrasPorFormaPagamento=quebras,
            observacoes=list(store.observacoes),
            pagina=pagina,
            limite=limite,
            totalFechamentos=total,
            hasMore=offset + limite < total,
        )


_svc: CashierAuditService | None = None


def get_cashier_audit_service() -> CashierAuditService:
    global _svc
    if _svc is None:
        _svc = CashierAuditService()
    return _svc
