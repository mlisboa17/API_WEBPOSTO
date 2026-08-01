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

NivelRisco = Literal["ALTO", "DESCONTO", "MEDIO", "BAIXO"]


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
    percentualDesconto: float = 0.0
    origemDesconto: str = ""
    cpfDesconto: str | None = None
    cpfRepetido: bool = False
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
    abastecimentosCriticosBanner: int = 0


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
                "MEDIO(40-59) agrup. dinheiro · BAIXO(0-39) retenção dinheiro/sem TEF",
                "TEF: bandeira/NSU via JOIN /INTEGRACAO/CARTAO por vendaCodigo",
            ]
            if not items:
                obs.append("SEM REGISTRO NO PERIODO — cache pista vazio")
                result.observacoes = obs
            else:
                qtd_dinheiro = sum(1 for i in items if _is_especie(i))
                ocorrencias = self._detect(items, settings)
                obs.append(
                    f"Baixados={len(items)} · dinheiro={qtd_dinheiro} · "
                    f"ocorrências={len(ocorrencias)}"
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
        """Compat: leitura exclusiva da RAM (limiar_override ignorado no GET — settings do worker)."""
        _ = limiar_override
        return self.response_from_ram(
            empresa_codigo=empresa_codigo,
            data_inicial=data_inicial,
            data_final=data_final,
        )

    def _detect(
        self,
        items: list[AbastecimentoRestV1],
        cfg: AuditFraudSettingsDTO,
    ) -> list[OcorrenciaFraudeDTO]:
        by_venda: dict[tuple[int, int], list[AbastecimentoRestV1]] = defaultdict(list)
        by_card_key: dict[str, list[AbastecimentoRestV1]] = defaultdict(list)
        by_cpf_frentista: dict[tuple[int, int | None, str], set[int]] = defaultdict(set)

        for item in items:
            vc = int(item.idVenda or 0) or -int(item.idAbastecimento)
            by_venda[(item.idEmpresa, vc)].append(item)
            bandeira, final = _bandeira_final(item)
            if final and not _is_especie(item):
                by_card_key[f"{item.idEmpresa}:{bandeira}:{final}"].append(item)
            cpf = str(getattr(item, "cpfCliente", None) or "").strip()
            cpf_digits = "".join(ch for ch in cpf if ch.isdigit())
            if cpf_digits and set(cpf_digits) != {"0"} and item.idFrentista:
                by_cpf_frentista[(item.idEmpresa, item.idFrentista, cpf_digits)].add(vc)

        recorrentes = {
            k for k, v in by_card_key.items() if len(v) >= cfg.recorrencia_cpf_cartao_limite
        }
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
            card_key = f"{emp}:{bandeira}:{final}"
            trigger_recorrencia = eletronico and bool(final) and card_key in recorrentes

            descontos = [float(getattr(a, "valorDesconto", 0) or 0) for _, _, a in enriched]
            valor_bruto = sum(a.valorTotal for _, _, a in enriched) + sum(descontos)
            valor_desc = round(sum(descontos), 2)
            pct_desc = round((valor_desc / valor_bruto) * 100, 2) if valor_bruto > 0 else 0.0
            trigger_desc = pct_desc > cfg.percentual_desconto_suspeito_pct or (
                valor_desc > 0 and pct_desc >= cfg.percentual_desconto_suspeito_pct
            )

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

            # ── Régua de gravidade (score decrescente) ──
            # ALTO só com evidência Cartão/PIX/Frota (elimina "Não informado" no topo)
            nivel: NivelRisco | None = None
            score = 0
            if eletronico and (trigger_lote or trigger_ret_crit):
                nivel = "ALTO"
                score = 95 if (trigger_lote and trigger_ret_crit) else (90 if trigger_lote else 85)
            elif trigger_cpf or trigger_desc or trigger_recorrencia:
                nivel = "DESCONTO"
                score = 75 if trigger_cpf else (70 if trigger_desc else 65)
            elif especie and trigger_lote:
                nivel = "MEDIO"
                score = 50
            elif eletronico and trigger_ret_med:
                nivel = "MEDIO"
                score = 45
            elif especie and (trigger_ret_crit or trigger_ret_med):
                nivel = "BAIXO"
                score = 30 if trigger_ret_crit else 20
            elif (not eletronico) and (not especie) and trigger_lote:
                # Sem TEF/forma: agrupamento não sobe a CRÍTICO
                nivel = "MEDIO"
                score = 42
            elif (not eletronico) and (trigger_ret_crit or trigger_ret_med):
                # Sem TEF/forma: retenção longa fica na base
                nivel = "BAIXO"
                score = 25 if trigger_ret_crit else 15
            elif eletronico and trigger_frac:
                nivel = "BAIXO"
                score = 15
            else:
                continue

            motivos: list[str] = []
            if trigger_ret_crit:
                motivos.append(
                    f"Retenção {retencao} min > {cfg.tempo_retencao_critico_min} min "
                    f"({'Dinheiro → BAIXO' if especie else f'baixa em {forma_label}'})"
                )
            elif trigger_ret_med:
                motivos.append(
                    f"Retenção {retencao} min > {cfg.tempo_retencao_atencao_min} min "
                    f"({'Dinheiro' if especie else forma_label})"
                )
            if trigger_lote:
                motivos.append(
                    f"Agrupamento de {qtd} bicos em {intervalo} min "
                    f"baixados em {forma_label}"
                    + (" (espécie → MÉDIO)" if especie else "")
                )
            if trigger_cpf:
                motivos.append(
                    f"Abuso de CPF/App {cpf_grp[-4:].rjust(4, '*')} pelo frentista "
                    f"≥ {cfg.recorrencia_cpf_cartao_limite}x no dia"
                )
            if trigger_recorrencia:
                motivos.append(
                    f"Reutilização do cartão final {final} ≥ {cfg.recorrencia_cpf_cartao_limite}x"
                )
            if trigger_desc:
                motivos.append(
                    f"Desconto/App {pct_desc:.1f}% (R$ {valor_desc:.2f}) acima do teto "
                    f"{cfg.percentual_desconto_suspeito_pct}%"
                )
            if trigger_frac and score < 40:
                motivos.append(f"Fracionamento curto: {qtd} abast. em {intervalo} min")

            gatilho = "+".join(
                n
                for n, f in [
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
                        litros=round(float(a.litros or 0), 3),
                        precoUnitario=round(preco_prat, 4),
                        precoTabela=round(preco_tab, 4),
                        precoPraticado=round(preco_prat, 4),
                        valorTotal=round(float(a.valorTotal or 0), 2),
                        valorDesconto=round(desc_a, 2),
                        origemDesconto=str(getattr(a, "origemDesconto", None) or ("FIDELIDADE/APP" if desc_a > 0 else "")),
                        cpfDesconto=getattr(a, "cpfCliente", None),
                        bico=a.bico,
                        bomba=bomba,
                        tempoRetencaoMinutos=ret_bico,
                    )
                )

            litros_tot = round(sum(d.litros for d in detalhes), 3)
            valor_tot = round(sum(d.valorTotal for d in detalhes), 2)
            pvm = round(valor_tot / litros_tot, 4) if litros_tot > 0 else 0.0
            seq += 1
            oid = f"FR-{emp}-{abs(venda)}-{seq}"
            origem = "FIDELIDADE/APP" if valor_desc > 0 else ("N/I" if not trigger_desc else "DESCONTO_MANUAL")

            bandeira_out = bandeira or ("—" if especie or forma_label == "PIX" else "")
            if forma_label == "PIX" and not bandeira_out:
                bandeira_out = "PIX"
            dto = OcorrenciaFraudeDTO(
                idOcorrencia=oid,
                linkOcorrencia=f"/executive/data-audit?ocorrencia={oid}",
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
                percentualDesconto=pct_desc,
                origemDesconto=origem,
                cpfDesconto=cpf_grp or None,
                cpfRepetido=trigger_cpf,
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

        # Ordenação padrão: score DESC → retenção DESC → valor DESC
        out.sort(key=lambda o: (-o.scoreGravidade, -o.tempoRetencaoMinutos, -o.valorTotal))
        return out

    def _build_resumo(self, ocorrencias: list[OcorrenciaFraudeDTO]) -> ResumoExecutivoFraude:
        if not ocorrencias:
            return ResumoExecutivoFraude()

        altos = [o for o in ocorrencias if o.nivelRisco == "ALTO"]
        descontos = [o for o in ocorrencias if o.nivelRisco == "DESCONTO"]
        medios = [o for o in ocorrencias if o.nivelRisco == "MEDIO"]
        baixos = [o for o in ocorrencias if o.nivelRisco == "BAIXO"]

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
            },
            totalAgrupamentosSuspeitos=len(ocorrencias),
            totalCriticos=len(altos) + len(descontos),
            totalAtencao=len(medios) + len(baixos),
            valorTotalRetidoCartoes=round(sum(o.valorTotal for o in ocorrencias), 2),
            valorCritico=round(sum(o.valorTotal for o in altos) + sum(o.valorTotal for o in descontos), 2),
            frentistaMaiorIncidencia=rank_f[0].nome if rank_f else "SEM REGISTRO NO PERIODO",
            frentistaMaiorIncidenciaQtd=rank_f[0].qtd if rank_f else 0,
            abastecimentosCriticosBanner=sum(o.qtdAbastecimentosAgrupados for o in altos),
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


_engine: FraudDetectionEngine | None = None


def get_fraud_detection_engine() -> FraudDetectionEngine:
    global _engine
    if _engine is None:
        _engine = FraudDetectionEngine()
    return _engine
