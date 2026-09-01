"""Engine de detecção anti-fraude de pista — thresholds dinâmicos + cache RAM."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from src.services.fraud_audit_settings_service import (
    AuditFraudSettingsDTO,
    get_settings,
)
from src.services.webposto_pista_service import AbastecimentoRestV1

LOGGER = logging.getLogger(__name__)
TZ = ZoneInfo("America/Recife")

FILIAIS = {
    5555: "AP CASA CAIADA",
    11495: "POSTO VIP",
    74014: "POSTO REAL / DOZE",
}

CARD_KEYWORDS = (
    "CARTAO", "CARTÃO", "CREDITO", "CRÉDITO", "DEBITO", "DÉBITO",
    "TEF", "POS", "VISA", "MASTER", "ELO", "HIPER", "AMEX", "MAESTRO",
)

DINHEIRO_KEYWORDS = (
    "DINHEIRO",
    "ESPECIE",
    "ESPÉCIE",
    "CASH",
    "NUMERARIO",
    "NUMERÁRIO",
)

ELETRONICO_KEYWORDS = (
    "PIX",
    "CARTAO",
    "CARTÃO",
    "CREDITO",
    "CRÉDITO",
    "DEBITO",
    "DÉBITO",
    "TEF",
    "POS",
    "VISA",
    "MASTER",
    "ELO",
    "HIPER",
    "AMEX",
    "MAESTRO",
    "PREMMIA",
    "FROTA",
    "FROTISTA",
    "CONVENIO",
    "CONVÊNIO",
    "PRAZO",
)

NivelRisco = Literal["ALTO", "DESCONTO", "MEDIO", "BAIXO", "FRAUDE_SUSPEITA"]


class AbastecimentoFraudeDetalhe(BaseModel):
    idAbastecimento: int = 0
    uuid: str = ""
    dataHoraBico: str = ""
    postoNome: str = ""
    tipoCombustivel: str = ""
    litros: float = 0.0
    precoUnitario: float = 0.0
    precoTabela: float = 0.0
    precoPraticado: float = 0.0
    valorTotal: float = 0.0
    valorDesconto: float = 0.0
    descontoPorLitro: float = 0.0
    origemDesconto: str = ""
    cpfDesconto: str | None = None
    bico: int = 0
    bomba: int = 0
    tempoRetencaoMinutos: int = 0
    # aliases UI
    horaBico: str = ""
    produto: str = ""


class MetricasAgrupamento(BaseModel):
    qtdAbastecimentos: int = 0
    intervaloBicosMinutos: int = 0
    tempoRetencaoMinutos: int = 0
    limiarCriticoMin: int = 30
    limiarAtencaoMin: int = 15
    limiarAgrupamentoMin: int = 15


class OcorrenciaFraudeDTO(BaseModel):
    idOcorrencia: str
    linkOcorrencia: str = ""
    funcionarioNome: str = "N/I"
    funcionarioId: int | None = None
    formaPagamento: str = ""
    cartaoBandeira: str = ""
    cartaoFinal: str = ""
    cartaoNsu: str = ""
    cartaoAutorizacao: str = ""
    isEspecie: bool = False
    postoNome: str = ""
    postoUnidade: int = 0
    valorTotal: float = 0.0
    dataHoraBico: str = ""
    dataHoraBaixa: str = ""
    dataHoraEmissaoCupom: str = ""
    tipoCombustivel: str = ""
    litros: float = 0.0
    precoUnitario: float = 0.0
    valorDesconto: float = 0.0
    descontoPorLitro: float = 0.0
    percentualDesconto: float = 0.0
    origemDesconto: str = ""
    cpfDesconto: str | None = None
    cpfRepetido: bool = False
    # Cartão Curinga — recorrência Bandeira+Final / NSU entre baixas distintas
    cartaoRepetido: bool = False
    quantidadeUsoCartao: int = 0
    quantidadeAbastecimentosCartao: int = 0
    motivoSuspeita: str = ""
    nivelRisco: NivelRisco = "MEDIO"
    scoreGravidade: int = 0
    isAgrupado: bool = False
    abastecimentosAgrupados: list[AbastecimentoFraudeDetalhe] = Field(default_factory=list)
    metricasAgrupamento: MetricasAgrupamento = Field(default_factory=MetricasAgrupamento)
    # Compat legado UI
    id: str = ""
    gatilho: str = ""
    frentistaNome: str = ""
    frentistaId: int | None = None
    empresaCodigo: int = 0
    empresaNome: str = ""
    vendaCodigo: int = 0
    uuid: str = ""
    horaBico: str = ""
    horaBaixa: str = ""
    dataHora: str = ""
    tempoRetencaoMinutos: int = 0
    intervaloBicosMinutos: int = 0
    qtdAbastecimentosAgrupados: int = 0
    valorTotalCartao: float = 0.0
    meioPagamento: str = ""
    detalhes: list[AbastecimentoFraudeDetalhe] = Field(default_factory=list)


class RankingItem(BaseModel):
    nome: str
    qtd: int = 0
    valor: float = 0.0


class ResumoExecutivoFraude(BaseModel):
    totalFraudes: int = 0
    valorTotalEnvolvido: float = 0.0
    totalDescontosIdentificados: float = 0.0
    totalAbastecimentosSuspeitos: int = 0
    rankingFrentistas: list[RankingItem] = Field(default_factory=list)
    rankingCartoes: list[RankingItem] = Field(default_factory=list)
    rankingCPFs: list[RankingItem] = Field(default_factory=list)
    rankingPostos: list[RankingItem] = Field(default_factory=list)
    distribuicaoRisco: dict[str, int] = Field(default_factory=dict)
    # Compat legado
    totalAgrupamentosSuspeitos: int = 0
    totalCriticos: int = 0
    totalAtencao: int = 0
    valorTotalRetidoCartoes: float = 0.0
    valorCritico: float = 0.0
    frentistaMaiorIncidencia: str = "SEM REGISTRO NO PERIODO"
    frentistaMaiorIncidenciaQtd: int = 0
    frentistaMaiorIncidenciaRetencaoMediaMin: float = 0.0
    abastecimentosCriticosBanner: int = 0
    # Severidades UI (🔴 Crítico · 🟧 Alto · 🟡 Médio · 🟢 Baixo)
    totalSeveridadeCritico: int = 0
    totalSeveridadeAlto: int = 0
    totalSeveridadeMedio: int = 0
    totalSeveridadeBaixo: int = 0


class FraudAuditEngineResult(BaseModel):
    success: bool = True
    synthetic: bool = False
    fromCache: bool = True
    fonte: str = "FraudDetectionEngine+RAM_CACHE"
    endpoint: str = "/api/v1/abastecimentos/baixados"
    periodo: dict[str, str] = Field(default_factory=dict)
    dataRef: str = ""
    geradoEm: str | None = None
    latencyMs: float = 0.0
    empresaCodigo: int | None = None
    parametros: AuditFraudSettingsDTO | None = None
    limiarRetencaoMinutos: int = 15
    limiarCriticoMinutos: int = 30
    resumo: ResumoExecutivoFraude = Field(default_factory=ResumoExecutivoFraude)
    resumoExecutivo: ResumoExecutivoFraude = Field(default_factory=ResumoExecutivoFraude)
    ocorrencias: list[OcorrenciaFraudeDTO] = Field(default_factory=list)
    bannerAlerta: str | None = None
    observacoes: list[str] = Field(default_factory=list)


@dataclass
class _FraudRamStore:
    data_ref: str = ""
    gerado_em: str | None = None
    result: FraudAuditEngineResult | None = None
    last_duration_ms: float = 0.0
    last_error: str | None = None
    observacoes: tuple[str, ...] = field(default_factory=tuple)


def _parse_iso(raw: Any) -> datetime | None:
    if not raw:
        return None
    text = str(raw).strip().replace("Z", "+00:00")
    if " " in text and "T" not in text:
        text = text.replace(" ", "T", 1)
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _fmt(dt: datetime | None) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S") if dt else ""


def _is_card(forma: str | None) -> bool:
    blob = (forma or "").upper()
    return bool(blob) and any(k in blob for k in CARD_KEYWORDS)


def _is_especie(item: AbastecimentoRestV1 | None = None, forma: str | None = None) -> bool:
    """Baixa em Dinheiro/Espécie — isenta de alerta crítico de fraude de cartão."""
    if item is not None and getattr(item, "isEspecie", False):
        return True
    blob = (forma if forma is not None else (item.formaPagamento if item else None) or "").upper()
    return bool(blob) and any(k in blob for k in DINHEIRO_KEYWORDS)


def _bandeira_final(item: AbastecimentoRestV1) -> tuple[str, str]:
    """Prefere campos do JOIN CARTAO; fallback parseia formaPagamento."""
    bandeira = str(getattr(item, "cartaoBandeira", None) or "").strip()
    if bandeira.upper() in ("N/I", "NI", "—", "-"):
        bandeira = ""
    final = str(getattr(item, "cartaoFinal", None) or "").strip()
    final = "".join(ch for ch in final if ch.isdigit())[-4:] if final else ""

    text = (item.formaPagamento or "").strip()
    upper = text.upper()
    if "PIX" in upper and not bandeira:
        bandeira = "PIX"
    if not bandeira or not final:
        if not bandeira:
            for name, label in (
                ("MASTERCARD", "Mastercard"),
                ("MASTER", "Mastercard"),
                ("MAESTRO", "Maestro"),
                ("VISA", "Visa"),
                ("ELO", "Elo"),
                ("HIPER", "Hipercard"),
                ("AMEX", "Amex"),
                ("PREMMIA", "Premmia"),
            ):
                if name in upper:
                    bandeira = label
                    break
        if not final:
            digits = re.findall(r"\d{4}", text)
            final = digits[-1] if digits else ""
    return bandeira, final


def _is_eletronico(item: AbastecimentoRestV1) -> bool:
    """Cartão/PIX/Frota/TEF comprovado — exclusivo para score ALTO (80-100)."""
    if _is_especie(item):
        return False
    if getattr(item, "cartaoBandeira", None) or getattr(item, "cartaoFinal", None) or getattr(
        item, "cartaoNsu", None
    ):
        return True
    blob = (item.formaPagamento or "").upper()
    return bool(blob) and any(k in blob for k in ELETRONICO_KEYWORDS)


def _pick_payment_anchor(group: list[AbastecimentoRestV1]) -> AbastecimentoRestV1:
    """Escolhe o item com melhor evidência TEF/forma na venda agrupada."""

    def score(a: AbastecimentoRestV1) -> tuple[int, int, int]:
        band = 1 if getattr(a, "cartaoBandeira", None) else 0
        final = 1 if getattr(a, "cartaoFinal", None) else 0
        forma = 1 if (a.formaPagamento or "").strip() else 0
        return (band + final, forma, final)

    return max(group, key=score)


def _card_fingerprint_keys(item: AbastecimentoRestV1) -> list[str]:
    """Chaves de cruzamento: Bandeira+Final e/ou NSU (por filial)."""
    if _is_especie(item):
        return []
    emp = int(getattr(item, "idEmpresa", 0) or 0)
    keys: list[str] = []
    bandeira, final = _bandeira_final(item)
    final_digits = "".join(ch for ch in (final or "") if ch.isdigit())[-4:]
    if final_digits and len(final_digits) >= 4:
        keys.append(f"{emp}:F:{(bandeira or 'CARTAO').upper()}:{final_digits}")
    nsu = str(getattr(item, "cartaoNsu", None) or "").strip()
    if nsu and nsu.upper() not in {"N/I", "NI", "-", "—"}:
        keys.append(f"{emp}:N:{nsu}")
    return keys


def _forma_pagamento_label(forma: str | None, *, bandeira: str = "") -> str:
    raw = (forma or "").strip()
    upper = raw.upper()
    if _is_especie(forma=raw):
        return "Dinheiro"
    if "PIX" in upper or (bandeira or "").upper() == "PIX":
        return "PIX"
    if "CONVENIO" in upper or "CONVÊNIO" in upper or "FROTISTA" in upper or "PRAZO" in upper or "FROTA" in upper:
        return "Convênio/Prazo"
    if "DEBITO" in upper or "DÉBITO" in upper or "MAESTRO" in upper:
        return "Cartão Débito"
    if "CREDITO" in upper or "CRÉDITO" in upper:
        return "Cartão Crédito"
    if "POS" in upper or "TEF" in upper or "CARTAO" in upper or "CARTÃO" in upper:
        return "Cartão/TEF"
    if _is_card(raw) or (bandeira and bandeira.upper() not in ("PIX",)):
        if bandeira:
            return f"Cartão {bandeira}"
        return "Cartão/TEF"
    return raw or "Não informado"


class FraudDetectionEngine:
    """Detecta anomalias de pista — publish no worker, GET só lê RAM."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._store = _FraudRamStore()

    def get_store(self) -> _FraudRamStore:
        return self._store

    async def refresh_from_pista(self) -> _FraudRamStore:
        """Worker 30s: recalcula só com baixados da RAM (sem Quality/WebPosto)."""
        t0 = time.perf_counter()
        try:
            from src.services.pista_cache_service import get_pista_cache

            snap = get_pista_cache().get_snapshot()
            data_ref = snap.data_ref or str(date.today())
            items = list(snap.baixados or [])
            settings = await get_settings(empresa_id=0)

            result = FraudAuditEngineResult(
                periodo={"inicio": data_ref, "fim": data_ref},
                dataRef=data_ref,
                empresaCodigo=None,
                parametros=settings,
                limiarRetencaoMinutos=settings.tempo_retencao_atencao_min,
                limiarCriticoMinutos=settings.tempo_retencao_critico_min,
                fonte="FraudDetectionEngine+RAM_CACHE",
                fromCache=True,
            )
            obs: list[str] = [
                "Fonte: cache RAM pista (worker 30s) — GET sem I/O externo",
                "Régua: ALTO(80-100) Cartão/PIX/Frota · DESCONTO(60-79) · "
                "MEDIO(40-59) agrupamento eletrônico · BAIXO(0-39) sem TEF · "
                "FRAUDE_SUSPEITA dinheiro (desconto manual / falta / estorno)",
                "Dinheiro sem desconto = OK (não gera alerta). "
                "Retenção/agrupamento em espécie NÃO são fraude de dinheiro.",
                "TEF: bandeira/NSU via JOIN /INTEGRACAO/CARTAO por vendaCodigo",
            ]
            if not items:
                obs.append("SEM REGISTRO NO PERIODO — cache pista vazio")
                result.observacoes = obs
            else:
                qtd_dinheiro = sum(1 for i in items if _is_especie(i))
                ocorrencias = self._detect(items, settings)
                faltas = self._detect_faltas_dinheiro_caixa(data_ref)
                if faltas:
                    ocorrencias.extend(faltas)
                    ocorrencias.sort(
                        key=lambda o: (
                            -int(bool(o.cartaoRepetido)),
                            -o.scoreGravidade,
                            -int(o.quantidadeUsoCartao or 0),
                            -o.tempoRetencaoMinutos,
                            -o.valorTotal,
                        )
                    )
                obs.append(
                    f"Baixados={len(items)} · dinheiro={qtd_dinheiro} · "
                    f"ocorrências={len(ocorrencias)} · faltas_dinheiro={len(faltas)}"
                )
                result.ocorrencias = ocorrencias
                resumo = self._build_resumo(ocorrencias)
                result.resumo = resumo
                result.resumoExecutivo = resumo
                result.bannerAlerta = self._banner(resumo, settings)
                result.observacoes = obs

            duration = (time.perf_counter() - t0) * 1000.0
            result.geradoEm = datetime.now(TZ).isoformat()
            async with self._lock:
                self._store = _FraudRamStore(
                    data_ref=data_ref,
                    gerado_em=result.geradoEm,
                    result=result,
                    last_duration_ms=duration,
                    last_error=None,
                    observacoes=tuple(result.observacoes),
                )
            LOGGER.info(
                "card_fraud.refresh ok data_ref=%s ocorrencias=%s duration_ms=%.1f",
                data_ref,
                len(result.ocorrencias),
                duration,
            )
            return self._store
        except Exception as exc:
            LOGGER.exception("card_fraud.refresh falhou: %s", exc)
            async with self._lock:
                prev = self._store
                self._store = _FraudRamStore(
                    data_ref=prev.data_ref,
                    gerado_em=prev.gerado_em,
                    result=prev.result,
                    last_duration_ms=(time.perf_counter() - t0) * 1000.0,
                    last_error=str(exc),
                    observacoes=prev.observacoes + (f"refresh_error: {exc}",),
                )
                return self._store

    def response_from_ram(
        self,
        *,
        empresa_codigo: int | None = None,
        data_inicial: str | None = None,
        data_final: str | None = None,
    ) -> FraudAuditEngineResult:
        """GET path — 100% sincronizado da RAM, sem I/O externo (<50ms)."""
        t0 = time.perf_counter()
        store = self._store
        if store.result is None:
            empty = FraudAuditEngineResult(
                success=True,
                fromCache=True,
                fonte="FraudDetectionEngine+RAM_CACHE",
                periodo={
                    "inicio": data_inicial or str(date.today()),
                    "fim": data_final or str(date.today()),
                },
                dataRef=store.data_ref,
                geradoEm=store.gerado_em,
                observacoes=["Cache anti-fraude vazio — aguardando PistaSyncWorker (30s)"],
            )
            empty.latencyMs = round((time.perf_counter() - t0) * 1000.0, 3)
            return empty

        base = store.result.model_copy(deep=True)
        base.fromCache = True
        base.fonte = "FraudDetectionEngine+RAM_CACHE"
        base.dataRef = store.data_ref
        base.geradoEm = store.gerado_em

        req_ini = data_inicial or store.data_ref
        req_fim = data_final or store.data_ref
        if store.data_ref and (req_ini != store.data_ref or req_fim != store.data_ref):
            base.observacoes = list(base.observacoes) + [
                f"Período solicitado {req_ini}..{req_fim} — servindo cache RAM do dia "
                f"{store.data_ref} (sem chamada síncrona)."
            ]
        base.periodo = {"inicio": store.data_ref or req_ini, "fim": store.data_ref or req_fim}

        if empresa_codigo is not None:
            emp = int(empresa_codigo)
            occ = [o for o in base.ocorrencias if int(o.empresaCodigo or o.postoUnidade or 0) == emp]
            base.ocorrencias = occ
            base.empresaCodigo = emp
            resumo = self._build_resumo(occ)
            base.resumo = resumo
            base.resumoExecutivo = resumo
            base.bannerAlerta = self._banner(resumo, base.parametros) if base.parametros else None

        base.latencyMs = round((time.perf_counter() - t0) * 1000.0, 3)
        return base

    async def auditar(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: int | None = None,
        limiar_override: int | None = None,
    ) -> FraudAuditEngineResult:
        """Auditoria do período — histórico via WebPosto; D0 usa RAM do worker quando possível."""
        _ = limiar_override
        return await self.auditar_periodo(
            data_inicial=data_inicial,
            data_final=data_final,
            empresa_codigo=empresa_codigo,
        )

    async def auditar_periodo(
        self,
        *,
        data_inicial: str,
        data_final: str,
        empresa_codigo: int | None = None,
    ) -> FraudAuditEngineResult:
        """Carrega baixados reais do período e aplica os 4 motores de auditoria."""
        t0 = time.perf_counter()
        hoje = str(date.today())
        settings = await get_settings(empresa_id=int(empresa_codigo or 0))
        single_day = data_inicial == data_final
        is_d0 = single_day and data_inicial == hoje

        # D0: preferir cache RAM do worker (rápido)
        if is_d0 and self._store.result and self._store.result.ocorrencias:
            ram = self.response_from_ram(
                empresa_codigo=empresa_codigo,
                data_inicial=data_inicial,
                data_final=data_final,
            )
            if ram.ocorrencias:
                return ram

        targets: list[int | None]
        if empresa_codigo is not None:
            targets = [int(empresa_codigo)]
        else:
            targets = list(FILIAIS.keys())

        items: list[AbastecimentoRestV1] = []
        obs: list[str] = [
            f"Auditoria período {data_inicial}..{data_final}",
            f"Régua retenção: Atenção >{settings.tempo_retencao_atencao_min} min · "
            f"Crítico >{settings.tempo_retencao_critico_min} min",
        ]
        try:
            from src.services.webposto_pista_service import WebPostoPistaService

            svc = WebPostoPistaService()
            for emp in targets:
                try:
                    baixados, _resumo, _o, err = await asyncio.wait_for(
                        svc.coletar_baixados_universo(
                            id_empresa=emp,
                            data_inicio=data_inicial,
                            data_fim=data_final,
                        ),
                        timeout=90.0,
                    )
                    if err:
                        obs.append(f"empresa={emp} aviso: {err}")
                    items.extend(baixados or [])
                except Exception as exc:
                    LOGGER.warning("auditar_periodo empresa=%s falhou: %s", emp, exc)
                    obs.append(f"empresa={emp} erro: {exc}")
        except Exception as exc:
            LOGGER.exception("auditar_periodo falhou: %s", exc)
            obs.append(f"falha carga: {exc}")
            # Fallback RAM
            return self.response_from_ram(
                empresa_codigo=empresa_codigo,
                data_inicial=data_inicial,
                data_final=data_final,
            )

        if empresa_codigo is not None:
            emp = int(empresa_codigo)
            items = [i for i in items if int(i.idEmpresa or 0) == emp]

        result = FraudAuditEngineResult(
            periodo={"inicio": data_inicial, "fim": data_final},
            dataRef=data_final,
            empresaCodigo=empresa_codigo,
            parametros=settings,
            limiarRetencaoMinutos=settings.tempo_retencao_atencao_min,
            limiarCriticoMinutos=settings.tempo_retencao_critico_min,
            fonte="FraudDetectionEngine+WEBPOSTO_BAIXADOS",
            fromCache=False,
            endpoint="/INTEGRACAO/CONSULTAR_ABASTECIMENTO_REDE",
        )

        if not items:
            obs.append("SEM REGISTRO NO PERIODO — nenhum abastecimento baixado no intervalo")
            result.observacoes = obs
            result.latencyMs = round((time.perf_counter() - t0) * 1000.0, 3)
            result.geradoEm = datetime.now(TZ).isoformat()
            return result

        ocorrencias = self._detect(items, settings)
        ocorrencias.extend(self._detect_agrupamento_mesmo_bico(items, settings))
        faltas = self._detect_faltas_dinheiro_caixa(data_final)
        if faltas:
            ocorrencias.extend(faltas)
        # Dedup por idOcorrencia
        seen: set[str] = set()
        uniq: list[OcorrenciaFraudeDTO] = []
        for o in ocorrencias:
            if o.idOcorrencia in seen:
                continue
            seen.add(o.idOcorrencia)
            uniq.append(o)
        uniq.sort(
            key=lambda o: (
                -int(bool(o.cartaoRepetido)),
                -o.scoreGravidade,
                -o.tempoRetencaoMinutos,
                -o.valorTotal,
            )
        )
        resumo = self._build_resumo(uniq)
        result.ocorrencias = uniq
        result.resumo = resumo
        result.resumoExecutivo = resumo
        result.bannerAlerta = self._banner(resumo, settings)
        obs.append(
            f"Baixados={len(items)} · ocorrências={len(uniq)} · "
            f"valor_suspeita=R${resumo.valorTotalEnvolvido:,.2f}"
        )
        result.observacoes = obs
        result.geradoEm = datetime.now(TZ).isoformat()
        result.latencyMs = round((time.perf_counter() - t0) * 1000.0, 3)
        LOGGER.info(
            "auditar_periodo ok %s..%s emp=%s items=%s occ=%s ms=%.0f",
            data_inicial,
            data_final,
            empresa_codigo,
            len(items),
            len(uniq),
            result.latencyMs,
        )
        return result

    def _detect_agrupamento_mesmo_bico(
        self,
        items: list[AbastecimentoRestV1],
        cfg: AuditFraudSettingsDTO,
    ) -> list[OcorrenciaFraudeDTO]:
        """Abastecimentos sequenciais no mesmo bico baixados no mesmo fechamento de caixa."""
        by_bico: dict[tuple[int, int], list[AbastecimentoRestV1]] = defaultdict(list)
        for it in items:
            if int(it.bico or 0) <= 0:
                continue
            if not it.dataHoraBaixa:
                continue
            by_bico[(int(it.idEmpresa or 0), int(it.bico))].append(it)

        out: list[OcorrenciaFraudeDTO] = []
        seq = 0
        for (emp, bico), group in by_bico.items():
            # Agrupa por horário de baixa (fechamento)
            by_baixa: dict[str, list[AbastecimentoRestV1]] = defaultdict(list)
            for g in group:
                by_baixa[str(g.dataHoraBaixa)[:19]].append(g)
            for baixa_key, batch in by_baixa.items():
                if len(batch) < 2:
                    continue
                enriched = []
                for a in batch:
                    dt = _parse_iso(a.dataHora)
                    if dt:
                        enriched.append((dt, a))
                if len(enriched) < 2:
                    continue
                enriched.sort(key=lambda x: x[0])
                # Sequencial: gaps entre bicos ≤ limiar de agrupamento
                gaps_ok = True
                for (a_dt, _), (b_dt, _) in zip(enriched, enriched[1:]):
                    gap = (b_dt - a_dt).total_seconds() / 60.0
                    if gap > cfg.tempo_agrupamento_max_min * 2:
                        gaps_ok = False
                        break
                if not gaps_ok:
                    continue
                # Só alerta se vendas distintas (fechamento em lote)
                vendas = {int(a.idVenda or 0) for _, a in enriched}
                if len([v for v in vendas if v > 0]) < 2 and len(enriched) < 3:
                    continue
                items_grp = [a for _, a in enriched]
                anchor = _pick_payment_anchor(items_grp)
                especie = _is_especie(anchor)
                if especie:
                    continue  # agrupamento em espécie não é fraude de meio
                valor_tot = round(sum(float(a.valorTotal or 0) for a in items_grp), 2)
                retencoes = []
                baixa_dt = _parse_iso(baixa_key)
                for bico_dt, a in enriched:
                    if baixa_dt and baixa_dt >= bico_dt:
                        retencoes.append(int((baixa_dt - bico_dt).total_seconds() / 60))
                retencao = max(retencoes) if retencoes else 0
                counts: dict[tuple[int | None, str], int] = defaultdict(int)
                for a in items_grp:
                    counts[(a.idFrentista, a.nomeFrentista or "N/I")] += 1
                (fid, fname), _ = max(counts.items(), key=lambda x: x[1])
                seq += 1
                oid = f"FR-AGR-{emp}-{bico}-{seq}"
                detalhes = [
                    AbastecimentoFraudeDetalhe(
                        idAbastecimento=a.idAbastecimento,
                        uuid=a.uuid or "",
                        dataHoraBico=_fmt(_parse_iso(a.dataHora)),
                        horaBico=_fmt(_parse_iso(a.dataHora)),
                        postoNome=FILIAIS.get(emp, a.nomeEmpresa or f"Empresa {emp}"),
                        tipoCombustivel=a.descricaoProduto or "Combustível",
                        produto=a.descricaoProduto or "Combustível",
                        litros=round(float(a.litros or 0), 3),
                        valorTotal=round(float(a.valorTotal or 0), 2),
                        bico=a.bico,
                        tempoRetencaoMinutos=retencao,
                    )
                    for a in items_grp
                ]
                out.append(
                    OcorrenciaFraudeDTO(
                        idOcorrencia=oid,
                        linkOcorrencia=f"/executive/data-audit?tab=anti-fraude&ocorrencia={oid}",
                        funcionarioNome=fname,
                        funcionarioId=fid,
                        formaPagamento=_forma_pagamento_label(anchor.formaPagamento),
                        postoNome=FILIAIS.get(emp, f"Empresa {emp}"),
                        postoUnidade=emp,
                        valorTotal=valor_tot,
                        dataHoraBico=_fmt(enriched[0][0]),
                        dataHoraBaixa=_fmt(baixa_dt),
                        tipoCombustivel=detalhes[0].tipoCombustivel if detalhes else "",
                        litros=round(sum(d.litros for d in detalhes), 3),
                        motivoSuspeita=(
                            f"Agrupamento de {len(batch)} abastecimentos no bico {bico:02d} "
                            f"sem fechamento intermediário de caixa (baixa {baixa_key})"
                        ),
                        nivelRisco="ALTO",
                        scoreGravidade=88,
                        isAgrupado=True,
                        abastecimentosAgrupados=detalhes,
                        metricasAgrupamento=MetricasAgrupamento(
                            qtdAbastecimentos=len(batch),
                            intervaloBicosMinutos=max(
                                0,
                                int((enriched[-1][0] - enriched[0][0]).total_seconds() / 60),
                            ),
                            tempoRetencaoMinutos=retencao,
                            limiarCriticoMin=cfg.tempo_retencao_critico_min,
                            limiarAtencaoMin=cfg.tempo_retencao_atencao_min,
                            limiarAgrupamentoMin=cfg.tempo_agrupamento_max_min,
                        ),
                        id=oid,
                        gatilho="AGRUPAMENTO_BICOS",
                        frentistaNome=fname,
                        frentistaId=fid,
                        empresaCodigo=emp,
                        empresaNome=FILIAIS.get(emp, f"Empresa {emp}"),
                        tempoRetencaoMinutos=retencao,
                        qtdAbastecimentosAgrupados=len(batch),
                        valorTotalCartao=valor_tot,
                        meioPagamento=anchor.formaPagamento or "",
                        detalhes=detalhes,
                    )
                )
        return out

    def _detect(
        self,
        items: list[AbastecimentoRestV1],
        cfg: AuditFraudSettingsDTO,
    ) -> list[OcorrenciaFraudeDTO]:
        by_venda: dict[tuple[int, int], list[AbastecimentoRestV1]] = defaultdict(list)
        # Cartão Curinga: conta baixas (vendas) e abastecimentos distintos por fingerprint
        by_card_vendas: dict[str, set[int]] = defaultdict(set)
        by_card_abast: dict[str, set[int]] = defaultdict(set)
        by_cpf_frentista: dict[tuple[int, int | None, str], set[int]] = defaultdict(set)

        for item in items:
            vc = int(item.idVenda or 0) or -int(item.idAbastecimento)
            by_venda[(item.idEmpresa, vc)].append(item)
            for ck in _card_fingerprint_keys(item):
                by_card_vendas[ck].add(vc)
                by_card_abast[ck].add(int(item.idAbastecimento))
            cpf = str(getattr(item, "cpfCliente", None) or "").strip()
            cpf_digits = "".join(ch for ch in cpf if ch.isdigit())
            if cpf_digits and set(cpf_digits) != {"0"} and item.idFrentista:
                by_cpf_frentista[(item.idEmpresa, item.idFrentista, cpf_digits)].add(vc)

        # >1 baixa/ocorrência distinta com o mesmo cartão → curinga
        recorrentes = {k for k, vendas in by_card_vendas.items() if len(vendas) > 1}
        cpf_abuso = {
            k
            for k, vendas in by_cpf_frentista.items()
            if len(vendas) >= cfg.recorrencia_cpf_cartao_limite
        }

        out: list[OcorrenciaFraudeDTO] = []
        seq = 0
        for (emp, venda), group in by_venda.items():
            enriched: list[tuple[datetime, datetime | None, AbastecimentoRestV1]] = []
            for ab in group:
                bico_dt = _parse_iso(ab.dataHora)
                if not bico_dt:
                    continue
                baixa_dt = _parse_iso(ab.dataHoraBaixa) if ab.dataHoraBaixa else None
                enriched.append((bico_dt, baixa_dt, ab))
            if not enriched:
                continue
            enriched.sort(key=lambda x: x[0])

            primeiro_dt, _, _primeiro_ab = enriched[0]
            items_grp = [a for _, _, a in enriched]
            anchor = _pick_payment_anchor(items_grp)
            especie = _is_especie(anchor)
            eletronico = _is_eletronico(anchor)
            retencoes = [
                int((baixa - bico).total_seconds() / 60)
                for bico, baixa, _ in enriched
                if baixa and baixa >= bico
            ]
            retencao = max(retencoes) if retencoes else 0
            ultimo_dt = enriched[-1][0]
            baixa_refs = [b for _, b, _ in enriched if b]
            pag_dt = max(baixa_refs) if baixa_refs else ultimo_dt
            intervalo = max(0, int((ultimo_dt - primeiro_dt).total_seconds() / 60))
            qtd = len(enriched)
            real_venda = venda > 0

            trigger_ret_crit = retencao > cfg.tempo_retencao_critico_min
            trigger_ret_med = (
                cfg.tempo_retencao_atencao_min < retencao <= cfg.tempo_retencao_critico_min
            )
            trigger_lote = (
                real_venda and qtd > 1 and intervalo > cfg.tempo_agrupamento_max_min
            )
            trigger_frac = real_venda and qtd > 1 and 0 < intervalo < 5

            bandeira, final = _bandeira_final(anchor)
            forma_label = _forma_pagamento_label(anchor.formaPagamento, bandeira=bandeira)
            if forma_label == "PIX":
                bandeira = bandeira or "PIX"
            card_keys = _card_fingerprint_keys(anchor)
            # Também une fingerprints de todos os itens do grupo (mesmo final em qualquer bico)
            for _, _, a in enriched:
                for ck in _card_fingerprint_keys(a):
                    if ck not in card_keys:
                        card_keys.append(ck)
            matching_recur = [k for k in card_keys if k in recorrentes]
            trigger_recorrencia = eletronico and bool(matching_recur)
            qtd_uso_cartao = 0
            qtd_abast_cartao = 0
            if matching_recur:
                qtd_uso_cartao = max(len(by_card_vendas[k]) for k in matching_recur)
                qtd_abast_cartao = max(len(by_card_abast[k]) for k in matching_recur)

            descontos = [float(getattr(a, "valorDesconto", 0) or 0) for _, _, a in enriched]
            valor_bruto = sum(a.valorTotal for _, _, a in enriched) + sum(descontos)
            valor_desc = round(sum(descontos), 2)
            pct_desc = round((valor_desc / valor_bruto) * 100, 2) if valor_bruto > 0 else 0.0

            counts: dict[tuple[int | None, str], int] = defaultdict(int)
            for _, _, a in enriched:
                counts[(a.idFrentista, a.nomeFrentista or "N/I")] += 1
            (fid, fname), _ = max(counts.items(), key=lambda x: x[1])

            cpf_grp = ""
            for _, _, a in enriched:
                raw = str(getattr(a, "cpfCliente", None) or "").strip()
                digits = "".join(ch for ch in raw if ch.isdigit())
                if digits and set(digits) != {"0"}:
                    cpf_grp = digits
                    break
            trigger_cpf = bool(fid and cpf_grp and (emp, fid, cpf_grp) in cpf_abuso)

            # Abuso de desconto: PDV sem fidelidade/App+CPF e sem código de gerente
            from src.services.anti_fraud_service import is_desconto_autorizado

            origem_detect = ""
            for _, _, a in enriched:
                od = str(getattr(a, "origemDesconto", None) or "").strip()
                if od:
                    origem_detect = od
                    break
            origem_up = origem_detect.upper()
            autorizado_gerente = any(
                k in origem_up
                for k in ("GERENTE", "AUTORIZ", "SUPERVISOR", "COD_GERENTE", "CODIGO_GERENTE")
            )
            autorizado_app = is_desconto_autorizado(
                origem_desconto=origem_detect, cpf_cliente=cpf_grp or None
            )
            origem_manual = any(
                k in origem_up for k in ("MANUAL", "PDV", "OPERADOR", "SEM AUTORIZ", "BALCAO", "BALCÃO")
            )
            trigger_desc_pct = pct_desc > cfg.percentual_desconto_suspeito_pct
            # Sem origem explícita: só flag se % acima do teto (evita flood)
            trigger_desc_nao_autorizado = (
                valor_desc > 0
                and not autorizado_app
                and not autorizado_gerente
                and (origem_manual or (not origem_detect and trigger_desc_pct))
            )
            trigger_desc = trigger_desc_nao_autorizado or trigger_desc_pct

            # ── Régua de gravidade (score decrescente) ──
            # Dinheiro: regra estrita em anti_fraud_service (sem retenção/agrupamento).
            nivel: NivelRisco | None = None
            score = 0
            motivos: list[str] = []
            gatilho = "ANOMALIA"

            if especie:
                from src.services.anti_fraud_service import classify_dinheiro_pagamento

                origem_grp = ""
                for _, _, a in enriched:
                    od = str(getattr(a, "origemDesconto", None) or "").strip()
                    if od:
                        origem_grp = od
                        break
                if not origem_grp and valor_desc > 0:
                    origem_grp = "DESCONTO_MANUAL"
                preco_tab = float(
                    getattr(anchor, "precoTabela", None) or anchor.precoUnitario or 0
                )
                preco_prat = float(anchor.precoUnitario or 0)
                cash_status, cash_motivo = classify_dinheiro_pagamento(
                    valor_desconto=valor_desc,
                    origem_desconto=origem_grp,
                    cpf_cliente=cpf_grp or None,
                    preco_tabela=preco_tab,
                    preco_praticado=preco_prat,
                    status=str(getattr(anchor, "status", "") or ""),
                    forma_pagamento=anchor.formaPagamento,
                    valor_total=sum(float(a.valorTotal or 0) for _, _, a in enriched),
                    percentual_desconto=pct_desc,
                    limiar_desconto_suspeito_pct=cfg.percentual_desconto_suspeito_pct,
                )
                # Inconsistência: Dinheiro + rastros TEF/PIX (meio não conciliado)
                tem_tef = bool(
                    getattr(anchor, "cartaoNsu", None)
                    or getattr(anchor, "cartaoFinal", None)
                    or getattr(anchor, "cartaoAutorizacao", None)
                )
                if cash_status == "OK" and tem_tef and (trigger_ret_med or trigger_ret_crit):
                    nivel = "MEDIO"
                    score = 55
                    motivos.append(
                        "Inconsistência de meio: venda como Dinheiro com NSU/TEF e "
                        f"retenção atípica ({retencao} min)"
                    )
                    gatilho = "INCONSISTENCIA_MEIO_PAGAMENTO"
                elif cash_status == "OK":
                    continue
                else:
                    nivel = "FRAUDE_SUSPEITA"
                    score = 72
                    if cash_motivo:
                        motivos.append(cash_motivo)
                    gatilho = (
                        "ESTORNO_DINHEIRO"
                        if cash_motivo and "estorno" in cash_motivo.casefold()
                        else "DESCONTO_DINHEIRO_MANUAL"
                        if valor_desc > 0
                        else "FRAUDE_DINHEIRO"
                    )
            elif trigger_recorrencia:
                nivel = "ALTO"
                score = 100
            elif eletronico and (trigger_lote or trigger_ret_crit):
                nivel = "ALTO"
                score = 95 if (trigger_lote and trigger_ret_crit) else (90 if trigger_lote else 85)
            elif trigger_cpf or trigger_desc:
                nivel = "DESCONTO"
                score = 75 if trigger_cpf else 70
            elif eletronico and trigger_ret_med:
                nivel = "MEDIO"
                score = 45
            elif (not eletronico) and trigger_lote:
                nivel = "MEDIO"
                score = 42
            elif (not eletronico) and (trigger_ret_crit or trigger_ret_med):
                nivel = "BAIXO"
                score = 25 if trigger_ret_crit else 15
            elif eletronico and trigger_frac:
                nivel = "BAIXO"
                score = 15
            else:
                continue

            if not especie:
                if trigger_recorrencia:
                    final_lbl = final or "****"
                    motivos.append(
                        f"CARTÃO CURINGA: final {final_lbl} usado em {qtd_uso_cartao} baixas "
                        f"({qtd_abast_cartao} abastecimentos) no período — score máximo"
                    )
                if trigger_ret_crit:
                    motivos.append(
                        f"Retenção {retencao} min > {cfg.tempo_retencao_critico_min} min "
                        f"(baixa em {forma_label})"
                    )
                elif trigger_ret_med:
                    motivos.append(
                        f"Retenção {retencao} min > {cfg.tempo_retencao_atencao_min} min "
                        f"({forma_label})"
                    )
                if trigger_lote:
                    motivos.append(
                        f"Agrupamento de {qtd} bicos em {intervalo} min "
                        f"baixados em {forma_label}"
                    )
                if trigger_cpf:
                    motivos.append(
                        f"Abuso de CPF/App {cpf_grp[-4:].rjust(4, '*')} pelo frentista "
                        f"≥ {cfg.recorrencia_cpf_cartao_limite}x no dia"
                    )
                if trigger_desc:
                    if trigger_desc_nao_autorizado:
                        motivos.append(
                            f"Abuso de desconto PDV R$ {valor_desc:.2f} ({pct_desc:.1f}%) "
                            f"sem autorização/código de gerente (origem={origem_detect or 'N/I'})"
                        )
                    else:
                        motivos.append(
                            f"Desconto/App {pct_desc:.1f}% (R$ {valor_desc:.2f}) acima do teto "
                            f"{cfg.percentual_desconto_suspeito_pct}%"
                        )
                if trigger_frac and score < 40:
                    motivos.append(
                        f"Fracionamento curto: {qtd} abast. em {intervalo} min"
                    )
                gatilho = "+".join(
                    n
                    for n, f in [
                        ("CARTAO_CURINGA", trigger_recorrencia),
                        ("RETENCAO", trigger_ret_crit or trigger_ret_med),
                        ("AGRUPAMENTO", trigger_lote),
                        ("ABUSO_CPF_APP", trigger_cpf),
                        ("RECORRENCIA_CARTAO", trigger_recorrencia),
                        ("DESCONTO", trigger_desc),
                        ("FRACIONAMENTO", trigger_frac and not trigger_lote),
                    ]
                    if f
                ) or "ANOMALIA"

            emissao = _fmt(pag_dt)
            detalhes: list[AbastecimentoFraudeDetalhe] = []
            for bico_dt, baixa_dt, a in enriched:
                ret_bico = 0
                if baixa_dt and baixa_dt >= bico_dt:
                    ret_bico = int((baixa_dt - bico_dt).total_seconds() / 60)
                elif pag_dt and pag_dt >= bico_dt:
                    ret_bico = int((pag_dt - bico_dt).total_seconds() / 60)
                preco_tab = float(getattr(a, "precoTabela", None) or a.precoUnitario or 0)
                preco_prat = float(a.precoUnitario or 0)
                desc_a = float(getattr(a, "valorDesconto", 0) or 0)
                litros_a = round(float(a.litros or 0), 3)
                desc_por_litro_a = (
                    round(desc_a / litros_a, 4) if litros_a > 0 else 0.0
                )
                bomba = int(getattr(a, "bomba", None) or (((max(1, a.bico) - 1) // 2) + 1))
                detalhes.append(
                    AbastecimentoFraudeDetalhe(
                        idAbastecimento=a.idAbastecimento,
                        uuid=a.uuid or "",
                        dataHoraBico=_fmt(bico_dt),
                        horaBico=_fmt(bico_dt),
                        postoNome=FILIAIS.get(a.idEmpresa, a.nomeEmpresa or f"Empresa {a.idEmpresa}"),
                        tipoCombustivel=a.descricaoProduto or "Combustível",
                        produto=a.descricaoProduto or "Combustível",
                        litros=litros_a,
                        precoUnitario=round(preco_prat, 4),
                        precoTabela=round(preco_tab, 4),
                        precoPraticado=round(preco_prat, 4),
                        valorTotal=round(float(a.valorTotal or 0), 2),
                        valorDesconto=round(desc_a, 2),
                        descontoPorLitro=desc_por_litro_a,
                        origemDesconto=str(
                            getattr(a, "origemDesconto", None)
                            or ("FIDELIDADE/APP" if desc_a > 0 else "SEM DESCONTO")
                        ),
                        cpfDesconto=getattr(a, "cpfCliente", None),
                        bico=a.bico,
                        bomba=bomba,
                        tempoRetencaoMinutos=ret_bico,
                    )
                )

            litros_tot = round(sum(d.litros for d in detalhes), 3)
            valor_tot = round(sum(d.valorTotal for d in detalhes), 2)
            pvm = round(valor_tot / litros_tot, 4) if litros_tot > 0 else 0.0
            desconto_por_litro = (
                round(valor_desc / litros_tot, 4) if litros_tot > 0 else 0.0
            )
            seq += 1
            oid = f"FR-{emp}-{abs(venda)}-{seq}"
            if valor_desc > 0:
                origem = "FIDELIDADE/APP"
            elif trigger_desc:
                origem = "DESCONTO_MANUAL"
            else:
                origem = "SEM DESCONTO"

            bandeira_out = bandeira or ("—" if especie or forma_label == "PIX" else "")
            if forma_label == "PIX" and not bandeira_out:
                bandeira_out = "PIX"
            dto = OcorrenciaFraudeDTO(
                idOcorrencia=oid,
                linkOcorrencia=f"/executive/data-audit?tab=anti-fraude&ocorrencia={oid}",
                funcionarioNome=fname,
                funcionarioId=fid,
                formaPagamento=forma_label,
                cartaoBandeira=bandeira_out or "—",
                cartaoFinal=final or "",
                cartaoNsu=str(getattr(anchor, "cartaoNsu", None) or ""),
                cartaoAutorizacao=str(getattr(anchor, "cartaoAutorizacao", None) or ""),
                isEspecie=especie,
                postoNome=FILIAIS.get(emp, anchor.nomeEmpresa or f"Empresa {emp}"),
                postoUnidade=emp,
                valorTotal=valor_tot,
                dataHoraBico=_fmt(primeiro_dt),
                dataHoraBaixa=emissao,
                dataHoraEmissaoCupom=emissao,
                tipoCombustivel=detalhes[0].tipoCombustivel if detalhes else "",
                litros=litros_tot,
                precoUnitario=pvm,
                valorDesconto=valor_desc,
                descontoPorLitro=desconto_por_litro,
                percentualDesconto=pct_desc,
                origemDesconto=origem,
                cpfDesconto=cpf_grp or None,
                cpfRepetido=trigger_cpf,
                cartaoRepetido=trigger_recorrencia,
                quantidadeUsoCartao=qtd_uso_cartao,
                quantidadeAbastecimentosCartao=qtd_abast_cartao,
                motivoSuspeita=" · ".join(motivos),
                nivelRisco=nivel,
                scoreGravidade=score,
                isAgrupado=qtd >= 2,
                abastecimentosAgrupados=detalhes,
                metricasAgrupamento=MetricasAgrupamento(
                    qtdAbastecimentos=qtd,
                    intervaloBicosMinutos=intervalo,
                    tempoRetencaoMinutos=retencao,
                    limiarCriticoMin=cfg.tempo_retencao_critico_min,
                    limiarAtencaoMin=cfg.tempo_retencao_atencao_min,
                    limiarAgrupamentoMin=cfg.tempo_agrupamento_max_min,
                ),
                id=oid,
                gatilho=gatilho,
                frentistaNome=fname,
                frentistaId=fid,
                empresaCodigo=emp,
                empresaNome=FILIAIS.get(emp, f"Empresa {emp}"),
                vendaCodigo=venda if venda > 0 else 0,
                uuid=detalhes[0].uuid if detalhes else "",
                horaBico=_fmt(primeiro_dt),
                horaBaixa=emissao,
                dataHora=_fmt(primeiro_dt),
                tempoRetencaoMinutos=retencao,
                intervaloBicosMinutos=intervalo,
                qtdAbastecimentosAgrupados=qtd,
                valorTotalCartao=valor_tot,
                meioPagamento=anchor.formaPagamento or forma_label,
                detalhes=detalhes,
            )
            out.append(dto)

        # Cartão Curinga no topo absoluto → score 100 → retenção → usos → valor
        out.sort(
            key=lambda o: (
                -int(bool(o.cartaoRepetido)),
                -o.scoreGravidade,
                -int(o.quantidadeUsoCartao or 0),
                -o.tempoRetencaoMinutos,
                -o.valorTotal,
            )
        )
        return out

    def _detect_faltas_dinheiro_caixa(self, data_ref: str) -> list[OcorrenciaFraudeDTO]:
        """Regra 2: falta em dinheiro no encerramento (caixa vs bico sistêmico)."""
        from src.services.anti_fraud_service import classify_falta_dinheiro_caixa

        out: list[OcorrenciaFraudeDTO] = []
        try:
            from src.services.cashier_audit_service import get_cashier_audit_service

            store = get_cashier_audit_service().get_store()
            if store.data_ref and store.data_ref != data_ref:
                # Ainda assim avalia o cache atual (D0 típico)
                pass
            for f in store.fechamentos:
                sist = float(getattr(f, "dinheiro_sistemico", 0) or 0)
                decl = float(getattr(f, "dinheiro_declarado", 0) or 0)
                if sist <= 0 and decl <= 0:
                    # fallback: falta global do turno com peso em dinheiro
                    if float(f.saldo or 0) >= -0.01:
                        continue
                    sist = float(f.faturamentoBico or 0)
                    decl = float(f.faturamentoCaixa or 0)
                status, motivo = classify_falta_dinheiro_caixa(
                    dinheiro_sistemico=sist,
                    dinheiro_declarado=decl,
                )
                if status != "FRAUDE_SUSPEITA" or not motivo:
                    continue
                oid = f"FR-CASH-{f.id}"
                falta = round(abs(min(0.0, decl - sist if sist or decl else float(f.saldo))), 2)
                out.append(
                    OcorrenciaFraudeDTO(
                        idOcorrencia=oid,
                        linkOcorrencia=f"/executive/cashier-audit?fechamento={f.id}",
                        funcionarioNome=f.operadorNome,
                        funcionarioId=f.operadorId,
                        formaPagamento="Dinheiro",
                        isEspecie=True,
                        postoNome=f.postoNome,
                        postoUnidade=f.postoCodigo,
                        valorTotal=falta,
                        motivoSuspeita=motivo,
                        nivelRisco="FRAUDE_SUSPEITA",
                        scoreGravidade=68,
                        id=oid,
                        gatilho="FALTA_DINHEIRO_CAIXA",
                        frentistaNome=f.operadorNome,
                        frentistaId=f.operadorId,
                        empresaCodigo=f.postoCodigo,
                        empresaNome=f.postoNome,
                        dataHora=f"{f.dataRef}T12:00:00",
                        dataHoraBico=f"{f.dataRef}T12:00:00",
                        meioPagamento="DINHEIRO",
                        origemDesconto="SEM DESCONTO",
                    )
                )
        except Exception as exc:
            LOGGER.warning("faltas_dinheiro_caixa: %s", exc)
        return out

    def _build_resumo(self, ocorrencias: list[OcorrenciaFraudeDTO]) -> ResumoExecutivoFraude:
        if not ocorrencias:
            return ResumoExecutivoFraude()

        altos = [o for o in ocorrencias if o.nivelRisco == "ALTO"]
        descontos = [o for o in ocorrencias if o.nivelRisco == "DESCONTO"]
        medios = [o for o in ocorrencias if o.nivelRisco == "MEDIO"]
        baixos = [o for o in ocorrencias if o.nivelRisco == "BAIXO"]
        fraude_cash = [o for o in ocorrencias if o.nivelRisco == "FRAUDE_SUSPEITA"]

        def top5(counter: dict[str, list[float]]) -> list[RankingItem]:
            items = [
                RankingItem(nome=k, qtd=int(v[0]), valor=round(v[1], 2))
                for k, v in counter.items()
            ]
            items.sort(key=lambda x: (-x.qtd, -x.valor))
            return items[:5]

        frent: dict[str, list[float]] = defaultdict(lambda: [0, 0.0])
        cartoes: dict[str, list[float]] = defaultdict(lambda: [0, 0.0])
        cpfs: dict[str, list[float]] = defaultdict(lambda: [0, 0.0])
        postos: dict[str, list[float]] = defaultdict(lambda: [0, 0.0])
        for o in ocorrencias:
            frent[o.funcionarioNome][0] += 1
            frent[o.funcionarioNome][1] += o.valorTotal
            card_label = f"{o.cartaoBandeira} *{o.cartaoFinal}" if o.cartaoFinal else o.cartaoBandeira
            cartoes[card_label or "N/I"][0] += 1
            cartoes[card_label or "N/I"][1] += o.valorTotal
            if o.cpfDesconto:
                cpfs[o.cpfDesconto][0] += 1
                cpfs[o.cpfDesconto][1] += o.valorDesconto
            postos[o.postoNome][0] += 1
            postos[o.postoNome][1] += o.valorTotal

        rank_f = top5(frent)
        # Tempo médio de retenção do top frentista
        top_nome = rank_f[0].nome if rank_f else ""
        top_rets = [
            o.tempoRetencaoMinutos
            for o in ocorrencias
            if top_nome and (o.funcionarioNome or o.frentistaNome) == top_nome
        ]
        top_ret_media = round(sum(top_rets) / len(top_rets), 1) if top_rets else 0.0
        # Severidade UI: Crítico=ALTO · Alto=DESCONTO/FRAUDE_CASH · Médio=MEDIO · Baixo=BAIXO
        sev_critico = len(altos)
        sev_alto = len(descontos) + len(fraude_cash)
        sev_medio = len(medios)
        sev_baixo = len(baixos)
        return ResumoExecutivoFraude(
            totalFraudes=len(ocorrencias),
            valorTotalEnvolvido=round(sum(o.valorTotal for o in ocorrencias), 2),
            totalDescontosIdentificados=round(sum(o.valorDesconto for o in ocorrencias), 2),
            totalAbastecimentosSuspeitos=sum(o.qtdAbastecimentosAgrupados for o in ocorrencias),
            rankingFrentistas=rank_f,
            rankingCartoes=top5(cartoes),
            rankingCPFs=top5(cpfs) if cpfs else [],
            rankingPostos=top5(postos),
            distribuicaoRisco={
                "ALTO": len(altos),
                "DESCONTO": len(descontos),
                "MEDIO": len(medios),
                "BAIXO": len(baixos),
                "FRAUDE_SUSPEITA": len(fraude_cash),
                "CRITICO": sev_critico,
            },
            totalAgrupamentosSuspeitos=sum(1 for o in ocorrencias if o.isAgrupado),
            totalCriticos=sev_critico + sev_alto,
            totalAtencao=sev_medio + sev_baixo,
            valorTotalRetidoCartoes=round(sum(o.valorTotal for o in ocorrencias), 2),
            valorCritico=round(
                sum(o.valorTotal for o in altos)
                + sum(o.valorTotal for o in descontos)
                + sum(o.valorTotal for o in fraude_cash),
                2,
            ),
            frentistaMaiorIncidencia=rank_f[0].nome if rank_f else "SEM REGISTRO NO PERIODO",
            frentistaMaiorIncidenciaQtd=rank_f[0].qtd if rank_f else 0,
            frentistaMaiorIncidenciaRetencaoMediaMin=top_ret_media,
            abastecimentosCriticosBanner=sum(o.qtdAbastecimentosAgrupados for o in altos),
            totalSeveridadeCritico=sev_critico,
            totalSeveridadeAlto=sev_alto,
            totalSeveridadeMedio=sev_medio,
            totalSeveridadeBaixo=sev_baixo,
        )

    @staticmethod
    def _banner(resumo: ResumoExecutivoFraude, cfg: AuditFraudSettingsDTO) -> str | None:
        if resumo.totalCriticos <= 0:
            return None
        dist = resumo.distribuicaoRisco or {}
        altos = int(dist.get("ALTO", 0) or 0)
        descontos = int(dist.get("DESCONTO", 0) or 0)
        return (
            f"ALERTA: {altos} CRÍTICO(s) + {descontos} ABUSO DE DESCONTO/APP no topo da lista "
            f"(retenção > {cfg.tempo_retencao_critico_min} min / agrupamento / CPF repetido). "
            f"Valor envolvido: R$ {resumo.valorCritico:,.2f}."
        )


def _match_forma_pagamento(o: OcorrenciaFraudeDTO, forma: str) -> bool:
    key = (forma or "").strip().upper()
    if not key or key in {"TODOS", "ALL", "*"}:
        return True
    blob = " ".join(
        [
            o.formaPagamento or "",
            o.meioPagamento or "",
            o.cartaoBandeira or "",
            "ESPECIE" if o.isEspecie else "",
        ]
    ).upper()
    if key in {"CARTAO", "CARTÃO", "TEF", "CARTAO_TEF"}:
        return (
            "CART" in blob
            or "TEF" in blob
            or "DEBIT" in blob
            or "DÉBIT" in blob
            or "CREDIT" in blob
            or "CRÉDIT" in blob
            or "MAESTRO" in blob
            or "VISA" in blob
            or "ELO" in blob
        ) and "PIX" not in blob and "DINHEIRO" not in blob and not o.isEspecie
    if key == "PIX":
        return "PIX" in blob
    if key in {"DINHEIRO", "ESPECIE", "ESPÉCIE", "CASH"}:
        return o.isEspecie or "DINHEIRO" in blob or "ESPECIE" in blob or "ESPÉCIE" in blob
    if key in {"FROTA", "CONVENIO", "CONVÊNIO", "PRAZO", "FROTISTA"}:
        return any(x in blob for x in ("FROTA", "FROTISTA", "CONVENIO", "CONVÊNIO", "PRAZO"))
    return key in blob


def _match_tipo_infracao(o: OcorrenciaFraudeDTO, tipo: str) -> bool:
    key = (tipo or "").strip().upper()
    if not key or key in {"TODOS", "ALL", "*"}:
        return True
    gatilho = (o.gatilho or "").upper()
    motivo = (o.motivoSuspeita or "").upper()
    if key in {"RETENCAO_CARTAO", "RETENCAO", "RETENÇÃO_CARTAO", "RETENCAO_CRITICA"}:
        return (
            "RETENCAO" in gatilho
            or "RETENÇÃO" in gatilho
            or "RETENCAO" in motivo
            or "RETENÇÃO" in motivo
            or (o.tempoRetencaoMinutos > 0 and _match_forma_pagamento(o, "CARTAO"))
            or (o.tempoRetencaoMinutos > 0 and _match_forma_pagamento(o, "PIX"))
        )
    if key in {"EXCESSO_DESCONTO", "DESCONTO", "ABUSO_DESCONTO"}:
        return (
            o.nivelRisco == "DESCONTO"
            or float(o.valorDesconto or 0) > 0
            or "DESCONTO" in gatilho
            or "DESCONTO" in motivo
        )
    if key in {"AGRUPAMENTO_BICOS", "AGRUPAMENTO", "AGRUPAMENTO_LOTE"}:
        return (
            bool(o.isAgrupado)
            or o.qtdAbastecimentosAgrupados >= 2
            or "AGRUPAMENTO" in gatilho
            or "AGRUP" in motivo
        )
    if key in {"ABUSO_CPF", "CPF"}:
        return bool(o.cpfRepetido) or "CPF" in motivo
    return True


def _match_busca_texto(o: OcorrenciaFraudeDTO, texto: str) -> bool:
    q = (texto or "").strip().casefold()
    if not q:
        return True
    parts: list[str] = [
        o.funcionarioNome or "",
        o.frentistaNome or "",
        o.postoNome or "",
        o.empresaNome or "",
        o.idOcorrencia or o.id or "",
        str(o.vendaCodigo or ""),
        o.cartaoFinal or "",
        o.cartaoNsu or "",
        o.cpfDesconto or "",
        o.formaPagamento or "",
        o.meioPagamento or "",
        o.motivoSuspeita or "",
    ]
    for d in o.abastecimentosAgrupados or o.detalhes or []:
        parts.extend(
            [
                str(d.bico or ""),
                str(d.bomba or ""),
                f"bico {int(d.bico or 0):02d}",
                d.tipoCombustivel or "",
                str(d.idAbastecimento or ""),
            ]
        )
    hay = " ".join(parts).casefold()
    return q in hay


def filter_ocorrencias_ram(
    ocorrencias: list[OcorrenciaFraudeDTO],
    *,
    frentista_id: int | None = None,
    frentista_nome: str | None = None,
    tipo_infracao: str | None = None,
    tempo_retencao_min: int | None = None,
    forma_pagamento: str | None = None,
    busca_texto: str | None = None,
) -> list[OcorrenciaFraudeDTO]:
    """Filtragem 100% em memória — meta <20ms."""
    nome_q = (frentista_nome or "").strip().casefold()
    out: list[OcorrenciaFraudeDTO] = []
    for o in ocorrencias:
        if frentista_id is not None:
            fid = o.frentistaId if o.frentistaId is not None else o.funcionarioId
            if fid is None or int(fid) != int(frentista_id):
                continue
        if nome_q:
            nome = (o.funcionarioNome or o.frentistaNome or "").casefold()
            if nome_q not in nome:
                continue
        if tempo_retencao_min is not None and int(o.tempoRetencaoMinutos or 0) < int(
            tempo_retencao_min
        ):
            continue
        if not _match_tipo_infracao(o, tipo_infracao or ""):
            continue
        if not _match_forma_pagamento(o, forma_pagamento or ""):
            continue
        if not _match_busca_texto(o, busca_texto or ""):
            continue
        out.append(o)
    return out


def list_frentistas_disponiveis(
    ocorrencias: list[OcorrenciaFraudeDTO],
) -> list[dict[str, Any]]:
    """Catálogo para o Select Frentista (derivado do dataset RAM)."""
    seen: dict[int | str, dict[str, Any]] = {}
    for o in ocorrencias:
        fid = o.frentistaId if o.frentistaId is not None else o.funcionarioId
        nome = (o.funcionarioNome or o.frentistaNome or "").strip() or "N/I"
        key: int | str = int(fid) if fid is not None else f"n:{nome.casefold()}"
        if key in seen:
            seen[key]["qtd"] = int(seen[key]["qtd"]) + 1
            continue
        seen[key] = {
            "id": int(fid) if fid is not None else None,
            "nome": nome,
            "qtd": 1,
        }
    return sorted(seen.values(), key=lambda x: (-int(x["qtd"]), str(x["nome"])))


_engine: FraudDetectionEngine | None = None


def get_fraud_detection_engine() -> FraudDetectionEngine:
    global _engine
    if _engine is None:
        _engine = FraudDetectionEngine()
    return _engine
