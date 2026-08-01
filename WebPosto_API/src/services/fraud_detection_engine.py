"""Engine de detecção anti-fraude de pista — thresholds 100% dinâmicos."""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.services.fraud_audit_settings_service import (
    AuditFraudSettingsDTO,
    get_settings,
)
from src.services.webposto_pista_service import AbastecimentoRestV1, get_pista_service

LOGGER = logging.getLogger(__name__)

FILIAIS = {
    5555: "AP CASA CAIADA",
    11495: "POSTO VIP",
    74014: "POSTO REAL / DOZE",
}

CARD_KEYWORDS = (
    "CARTAO", "CARTÃO", "CREDITO", "CRÉDITO", "DEBITO", "DÉBITO",
    "TEF", "POS", "VISA", "MASTER", "ELO", "HIPER", "AMEX",
)

NivelRisco = Literal["ALTO", "MEDIO", "BAIXO"]


class AbastecimentoFraudeDetalhe(BaseModel):
    idAbastecimento: int = 0
    uuid: str = ""
    dataHoraBico: str = ""
    postoNome: str = ""
    tipoCombustivel: str = ""
    litros: float = 0.0
    precoUnitario: float = 0.0
    valorTotal: float = 0.0
    valorDesconto: float = 0.0
    cpfDesconto: str | None = None
    bico: int = 0


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
    cartaoBandeira: str = ""
    cartaoFinal: str = ""
    postoNome: str = ""
    postoUnidade: int = 0
    valorTotal: float = 0.0
    dataHoraBico: str = ""
    dataHoraBaixa: str = ""
    tipoCombustivel: str = ""
    litros: float = 0.0
    precoUnitario: float = 0.0
    valorDesconto: float = 0.0
    percentualDesconto: float = 0.0
    origemDesconto: str = ""
    cpfDesconto: str | None = None
    motivoSuspeita: str = ""
    nivelRisco: NivelRisco = "MEDIO"
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
    fonte: str = "FraudDetectionEngine+RAM_CACHE"
    endpoint: str = "/api/v1/abastecimentos/baixados"
    periodo: dict[str, str]
    empresaCodigo: int | None = None
    parametros: AuditFraudSettingsDTO | None = None
    limiarRetencaoMinutos: int = 15
    limiarCriticoMinutos: int = 30
    resumo: ResumoExecutivoFraude = Field(default_factory=ResumoExecutivoFraude)
    resumoExecutivo: ResumoExecutivoFraude = Field(default_factory=ResumoExecutivoFraude)
    ocorrencias: list[OcorrenciaFraudeDTO] = Field(default_factory=list)
    bannerAlerta: str | None = None
    observacoes: list[str] = Field(default_factory=list)


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


def _bandeira_final(forma: str | None) -> tuple[str, str]:
    text = (forma or "").strip()
    upper = text.upper()
    bandeira = "CARTÃO/TEF"
    for name in ("VISA", "MASTER", "ELO", "HIPER", "AMEX"):
        if name in upper:
            bandeira = name.title()
            break
    digits = re.findall(r"\d{4}", text)
    final = digits[-1] if digits else ""
    return bandeira, final


class FraudDetectionEngine:
    """Detecta anomalias de pista com parâmetros configuráveis."""

    async def auditar(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: int | None = None,
        limiar_override: int | None = None,
    ) -> FraudAuditEngineResult:
        settings = await get_settings(empresa_id=int(empresa_codigo or 0))
        if limiar_override is not None:
            # Compat: query limiarRetencaoMinutos → atenção; crítico = max(override+15, settings)
            settings.tempo_retencao_atencao_min = int(limiar_override)
            if settings.tempo_retencao_atencao_min >= settings.tempo_retencao_critico_min:
                settings.tempo_retencao_critico_min = settings.tempo_retencao_atencao_min + 15

        result = FraudAuditEngineResult(
            periodo={"inicio": data_inicial, "fim": data_final},
            empresaCodigo=empresa_codigo,
            parametros=settings,
            limiarRetencaoMinutos=settings.tempo_retencao_atencao_min,
            limiarCriticoMinutos=settings.tempo_retencao_critico_min,
        )

        try:
            items, obs, fonte = await self._load_items(
                data_inicial, data_final, empresa_codigo
            )
            result.fonte = fonte
            result.observacoes.extend(obs)

            card_items = [i for i in items if _is_card(i.formaPagamento)]
            if not items:
                result.observacoes.append("SEM REGISTRO NO PERIODO")
                return result
            if not card_items:
                result.observacoes.append("SEM REGISTRO DE PAGAMENTO EM CARTAO/TEF NO PERIODO")
                return result

            ocorrencias = self._detect(card_items, settings)
            result.ocorrencias = ocorrencias
            resumo = self._build_resumo(ocorrencias)
            result.resumo = resumo
            result.resumoExecutivo = resumo
            result.bannerAlerta = self._banner(resumo, settings)
            return result
        except Exception as exc:
            LOGGER.exception("FraudDetectionEngine falhou: %s", exc)
            result.success = False
            result.observacoes.append(str(exc))
            return result

    async def _load_items(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: int | None,
    ) -> tuple[list[AbastecimentoRestV1], list[str], str]:
        try:
            from src.services.pista_cache_service import get_pista_cache

            snap = get_pista_cache().get_snapshot()
            if (
                snap.ultima_sincronizacao_iso
                and snap.data_ref == data_inicial == data_final
                and snap.baixados
            ):
                items = list(snap.baixados)
                if empresa_codigo is not None:
                    items = [i for i in items if i.idEmpresa == int(empresa_codigo)]
                return items, ["Fonte: cache RAM pista"], "FraudDetectionEngine+RAM_CACHE"
        except Exception as exc:
            LOGGER.warning("engine: cache miss (%s)", exc)

        items, _, obs, _ = await get_pista_service().coletar_baixados_universo(
            id_empresa=empresa_codigo,
            data_inicio=data_inicial,
            data_fim=data_final,
        )
        return items, list(obs or []), "FraudDetectionEngine+Quality"

    def _detect(
        self,
        items: list[AbastecimentoRestV1],
        cfg: AuditFraudSettingsDTO,
    ) -> list[OcorrenciaFraudeDTO]:
        by_venda: dict[tuple[int, int], list[AbastecimentoRestV1]] = defaultdict(list)
        by_card_key: dict[str, list[AbastecimentoRestV1]] = defaultdict(list)

        for item in items:
            vc = int(item.idVenda or 0) or -int(item.idAbastecimento)
            by_venda[(item.idEmpresa, vc)].append(item)
            bandeira, final = _bandeira_final(item.formaPagamento)
            if final:
                by_card_key[f"{item.idEmpresa}:{bandeira}:{final}"].append(item)

        recorrentes = {
            k for k, v in by_card_key.items() if len(v) >= cfg.recorrencia_cpf_cartao_limite
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

            retencoes = [
                int((baixa - bico).total_seconds() / 60)
                for bico, baixa, _ in enriched
                if baixa and baixa >= bico
            ]
            retencao = max(retencoes) if retencoes else 0
            primeiro_dt, _, primeiro = enriched[0]
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
                real_venda and qtd >= 2 and intervalo > cfg.tempo_agrupamento_max_min
            )
            trigger_frac = real_venda and qtd >= 2 and 0 < intervalo < 5
            bandeira, final = _bandeira_final(primeiro.formaPagamento)
            card_key = f"{emp}:{bandeira}:{final}"
            trigger_recorrencia = bool(final) and card_key in recorrentes

            # Desconto: payload Quality nem sempre traz — deriva 0 se ausente
            descontos = []
            for _, _, a in enriched:
                # campos opcionais futuros
                desc = float(getattr(a, "valorDesconto", 0) or 0)
                descontos.append(desc)
            valor_bruto = sum(a.valorTotal for _, _, a in enriched) + sum(descontos)
            valor_desc = round(sum(descontos), 2)
            pct_desc = round((valor_desc / valor_bruto) * 100, 2) if valor_bruto > 0 else 0.0
            trigger_desc = pct_desc > cfg.percentual_desconto_suspeito_pct

            if not any(
                [
                    trigger_ret_crit,
                    trigger_ret_med,
                    trigger_lote,
                    trigger_frac,
                    trigger_recorrencia,
                    trigger_desc,
                ]
            ):
                continue

            if trigger_ret_crit or trigger_lote or trigger_recorrencia:
                nivel: NivelRisco = "ALTO"
            elif trigger_ret_med or trigger_desc:
                nivel = "MEDIO"
            else:
                nivel = "BAIXO"

            motivos: list[str] = []
            if trigger_ret_crit:
                motivos.append(
                    f"Retenção de {retencao} min ultrapassou o limite Crítico configurado "
                    f"({cfg.tempo_retencao_critico_min} min)"
                )
            elif trigger_ret_med:
                motivos.append(
                    f"Retenção de {retencao} min ultrapassou o limite de Atenção configurado "
                    f"({cfg.tempo_retencao_atencao_min} min)"
                )
            if trigger_lote:
                motivos.append(
                    f"Agrupamento de {qtd} bicos com intervalo de {intervalo} min "
                    f"(limite configurado: {cfg.tempo_agrupamento_max_min} min)"
                )
            if trigger_recorrencia:
                motivos.append(
                    f"Reutilização do cartão final {final} ≥ {cfg.recorrencia_cpf_cartao_limite}x no dia"
                )
            if trigger_desc:
                motivos.append(
                    f"Desconto acumulado {pct_desc:.1f}% acima do limiar "
                    f"({cfg.percentual_desconto_suspeito_pct}%)"
                )
            if trigger_frac and nivel == "BAIXO":
                motivos.append(
                    f"Fracionamento curto de {qtd} abastecimentos em {intervalo} min (< 5 min)"
                )

            gatilho = "+".join(
                [
                    n
                    for n, f in [
                        ("RETENCAO", trigger_ret_crit or trigger_ret_med),
                        ("AGRUPAMENTO", trigger_lote),
                        ("RECORRENCIA_CARTAO", trigger_recorrencia),
                        ("DESCONTO", trigger_desc),
                        ("FRACIONAMENTO", trigger_frac and not trigger_lote),
                    ]
                    if f
                ]
            ) or "ANOMALIA"

            counts: dict[tuple[int | None, str], int] = defaultdict(int)
            for _, _, a in enriched:
                counts[(a.idFrentista, a.nomeFrentista or "N/I")] += 1
            (fid, fname), _ = max(counts.items(), key=lambda x: x[1])

            detalhes = [
                AbastecimentoFraudeDetalhe(
                    idAbastecimento=a.idAbastecimento,
                    uuid=a.uuid or "",
                    dataHoraBico=_fmt(bico_dt),
                    postoNome=FILIAIS.get(a.idEmpresa, a.nomeEmpresa or f"Empresa {a.idEmpresa}"),
                    tipoCombustivel=a.descricaoProduto or "Combustível",
                    litros=round(float(a.litros or 0), 3),
                    precoUnitario=round(float(a.precoUnitario or 0), 4),
                    valorTotal=round(float(a.valorTotal or 0), 2),
                    valorDesconto=0.0,
                    cpfDesconto=None,
                    bico=a.bico,
                )
                for bico_dt, _, a in enriched
            ]

            litros_tot = round(sum(d.litros for d in detalhes), 3)
            valor_tot = round(sum(d.valorTotal for d in detalhes), 2)
            pvm = round(valor_tot / litros_tot, 4) if litros_tot > 0 else 0.0
            seq += 1
            oid = f"FR-{emp}-{abs(venda)}-{seq}"

            dto = OcorrenciaFraudeDTO(
                idOcorrencia=oid,
                linkOcorrencia=f"/executive/data-audit?ocorrencia={oid}",
                funcionarioNome=fname,
                funcionarioId=fid,
                cartaoBandeira=bandeira,
                cartaoFinal=final,
                postoNome=FILIAIS.get(emp, primeiro.nomeEmpresa or f"Empresa {emp}"),
                postoUnidade=emp,
                valorTotal=valor_tot,
                dataHoraBico=_fmt(primeiro_dt),
                dataHoraBaixa=_fmt(pag_dt),
                tipoCombustivel=detalhes[0].tipoCombustivel if detalhes else "",
                litros=litros_tot,
                precoUnitario=pvm,
                valorDesconto=valor_desc,
                percentualDesconto=pct_desc,
                origemDesconto="N/I" if not valor_desc else "PROMOCAO",
                cpfDesconto=None,
                motivoSuspeita=" · ".join(motivos),
                nivelRisco=nivel,
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
                horaBaixa=_fmt(pag_dt),
                dataHora=_fmt(primeiro_dt),
                tempoRetencaoMinutos=retencao,
                intervaloBicosMinutos=intervalo,
                qtdAbastecimentosAgrupados=qtd,
                valorTotalCartao=valor_tot,
                meioPagamento=primeiro.formaPagamento or bandeira,
                detalhes=detalhes,
            )
            # alias for legacy field name in JSON
            out.append(dto)

        risk_rank = {"ALTO": 0, "MEDIO": 1, "BAIXO": 2}
        out.sort(
            key=lambda o: (
                risk_rank.get(o.nivelRisco, 9),
                -o.tempoRetencaoMinutos,
                -o.valorTotal,
            )
        )
        return out

    def _build_resumo(self, ocorrencias: list[OcorrenciaFraudeDTO]) -> ResumoExecutivoFraude:
        if not ocorrencias:
            return ResumoExecutivoFraude()

        altos = [o for o in ocorrencias if o.nivelRisco == "ALTO"]
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
                "MEDIO": len(medios),
                "BAIXO": len(baixos),
            },
            totalAgrupamentosSuspeitos=len(ocorrencias),
            totalCriticos=len(altos),
            totalAtencao=len(medios) + len(baixos),
            valorTotalRetidoCartoes=round(sum(o.valorTotal for o in ocorrencias), 2),
            valorCritico=round(sum(o.valorTotal for o in altos), 2),
            frentistaMaiorIncidencia=rank_f[0].nome if rank_f else "SEM REGISTRO NO PERIODO",
            frentistaMaiorIncidenciaQtd=rank_f[0].qtd if rank_f else 0,
            abastecimentosCriticosBanner=sum(o.qtdAbastecimentosAgrupados for o in altos),
        )

    @staticmethod
    def _banner(resumo: ResumoExecutivoFraude, cfg: AuditFraudSettingsDTO) -> str | None:
        if resumo.totalCriticos <= 0:
            return None
        return (
            f"ALERTA: {resumo.totalCriticos} ocorrência(s) de RISCO ALTO "
            f"(retenção > {cfg.tempo_retencao_critico_min} min / agrupamento / recorrência). "
            f"Valor envolvido: R$ {resumo.valorCritico:,.2f}."
        )


_engine: FraudDetectionEngine | None = None


def get_fraud_detection_engine() -> FraudDetectionEngine:
    global _engine
    if _engine is None:
        _engine = FraudDetectionEngine()
    return _engine
