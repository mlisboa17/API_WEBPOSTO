"""Auditoria Anti-Fraude de Pista — Retencao e Agrupamento de Cartoes.

Fonte REST v1 (LOGOS facade sobre Quality):
  GET /api/v1/abastecimentos/baixados
  Schema: dataHora, dataHoraBaixa, formaPagamento, idVenda, uuid

Gatilho 1 — Retenção: Delta = dataHoraBaixa - dataHora
  > 15 min → ATENÇÃO | > 30 min → CRÍTICO
Gatilho 2 — Lote: mesmo idVenda com >=2 idAbastecimento e
  (max dataHora - min dataHora) > 15 min
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.services.webposto_pista_service import AbastecimentoRestV1, get_pista_service

LOGGER = logging.getLogger(__name__)

FILIAIS = {
    5555: "AP CASA CAIADA",
    6666: "POSTO VIP",
    11495: "POSTO VIP",
    74014: "POSTO REAL / DOZE",
    5558: "POSTO REAL",
    7777: "POSTO REAL / DOZE",
}

CARD_KEYWORDS = (
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
)

DEFAULT_RETENTION_THRESHOLD_MIN = 15
CRITICAL_RETENTION_MIN = 30
BATCH_GAP_THRESHOLD_MIN = 15

FONTE_OFICIAL = "REST_v1_AbastecimentosBaixados"
ENDPOINT_OFICIAL = "/api/v1/abastecimentos/baixados"


class CardFraudBicoDetalhe(BaseModel):
    abastecimentoId: int = 0
    uuid: str = ""
    bico: int = 0
    horaBico: str = ""
    produto: str = ""
    litros: float = 0.0
    valor: float = 0.0


class CardFraudOcorrencia(BaseModel):
    id: str
    gatilho: str
    frentistaId: int | None = None
    frentistaNome: str = "N/I"
    empresaCodigo: int = 0
    empresaNome: str = ""
    vendaCodigo: int = 0
    uuid: str = ""
    horaBico: str = ""
    horaBaixa: str = ""
    dataHora: str = ""
    dataHoraBaixa: str = ""
    horaPrimeiroBico: str = ""
    horaUltimoBico: str = ""
    horaBaixaCartao: str = ""
    tempoRetencaoMinutos: int = 0
    intervaloBicosMinutos: int = 0
    qtdAbastecimentosAgrupados: int = 0
    valorTotalCartao: float = 0.0
    nivelRisco: str
    meioPagamento: str = ""
    detalhes: list[CardFraudBicoDetalhe] = Field(default_factory=list)


class CardFraudResumo(BaseModel):
    totalAgrupamentosSuspeitos: int = 0
    totalCriticos: int = 0
    totalAtencao: int = 0
    valorTotalRetidoCartoes: float = 0.0
    valorCritico: float = 0.0
    frentistaMaiorIncidencia: str = "SEM REGISTRO NO PERIODO"
    frentistaMaiorIncidenciaQtd: int = 0
    abastecimentosCriticosBanner: int = 0


class CardFraudAuditResult(BaseModel):
    success: bool = True
    synthetic: bool = False
    fonte: str = FONTE_OFICIAL
    endpoint: str = ENDPOINT_OFICIAL
    periodo: dict[str, str]
    empresaCodigo: int | None = None
    limiarRetencaoMinutos: int = DEFAULT_RETENTION_THRESHOLD_MIN
    limiarCriticoMinutos: int = CRITICAL_RETENTION_MIN
    resumo: CardFraudResumo = Field(default_factory=CardFraudResumo)
    ocorrencias: list[CardFraudOcorrencia] = Field(default_factory=list)
    bannerAlerta: str | None = None
    observacoes: list[str] = Field(default_factory=list)


class CardFraudAuditService:
    """Motor anti-fraude sobre abastecimentos baixados REST v1 (dados reais)."""

    def __init__(self) -> None:
        self.pista = get_pista_service()

    async def _load_baixados(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: int | None,
    ) -> tuple[list[AbastecimentoRestV1], list[str], str]:
        """Prefere cache RAM do dia (universo completo); fallback Quality."""
        try:
            from src.services.pista_cache_service import get_pista_cache

            snap = get_pista_cache().get_snapshot()
            if (
                snap.ultima_sincronizacao_iso
                and snap.data_ref
                and snap.data_ref == data_inicial
                and snap.data_ref == data_final
                and snap.baixados
            ):
                items = list(snap.baixados)
                if empresa_codigo is not None:
                    items = [i for i in items if i.idEmpresa == int(empresa_codigo)]
                return (
                    items,
                    ["Fonte: cache RAM pista (universo completo do dia)"],
                    f"{FONTE_OFICIAL}+RAM_CACHE",
                )
        except Exception as exc:
            LOGGER.warning("card-fraud: cache RAM indisponível (%s) — fallback Quality", exc)

        items, _resumo, obs, _err = await self.pista.coletar_baixados_universo(
            id_empresa=empresa_codigo,
            data_inicio=data_inicial,
            data_fim=data_final,
        )
        return items, list(obs or []), FONTE_OFICIAL

    async def auditar(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: int | None = None,
        limiar_retencao_minutos: int = DEFAULT_RETENTION_THRESHOLD_MIN,
    ) -> CardFraudAuditResult:
        limiar = max(15, min(30, int(limiar_retencao_minutos or DEFAULT_RETENTION_THRESHOLD_MIN)))

        result = CardFraudAuditResult(
            periodo={"inicio": data_inicial, "fim": data_final},
            empresaCodigo=empresa_codigo,
            limiarRetencaoMinutos=limiar,
            synthetic=False,
            fonte=FONTE_OFICIAL,
            endpoint=ENDPOINT_OFICIAL,
        )

        try:
            all_items, obs, fonte = await self._load_baixados(
                data_inicial=data_inicial,
                data_final=data_final,
                empresa_codigo=empresa_codigo,
            )
            result.fonte = fonte
            if obs:
                result.observacoes.extend(obs)

            items = [i for i in all_items if self._is_card_forma(i.formaPagamento)]

            if not all_items:
                result.observacoes.append(
                    "SEM REGISTRO NO PERIODO — /abastecimentos/baixados sem dados"
                )
                return result

            if not items:
                result.observacoes.append(
                    "SEM REGISTRO DE PAGAMENTO EM CARTAO/DEBITO/TEF NO PERIODO"
                )
                return result

            ocorrencias = self._detectar_rest_v1(items=items, limiar=limiar)
            result.ocorrencias = ocorrencias
            result.resumo = self._build_resumo(ocorrencias)
            result.bannerAlerta = self._build_banner(result.resumo)

            LOGGER.info(
                "card-fraud REST v1 baixados: periodo=%s..%s empresa=%s cartao=%d/%d "
                "ocorrencias=%d criticos=%d synthetic=false fonte=%s",
                data_inicial,
                data_final,
                empresa_codigo,
                len(items),
                len(all_items),
                len(ocorrencias),
                result.resumo.totalCriticos,
                fonte,
            )
            return result

        except Exception as exc:
            LOGGER.exception(
                "card-fraud REST v1 falhou periodo=%s..%s empresa=%s: %s",
                data_inicial,
                data_final,
                empresa_codigo,
                exc,
            )
            result.success = False
            result.ocorrencias = []
            result.observacoes.append(f"Erro na auditoria: {exc}")
            return result

    def _detectar_rest_v1(
        self,
        items: list[AbastecimentoRestV1],
        limiar: int,
    ) -> list[CardFraudOcorrencia]:
        by_venda: dict[tuple[int, int], list[AbastecimentoRestV1]] = defaultdict(list)
        for item in items:
            vc = int(item.idVenda or 0)
            if not vc:
                vc = -item.idAbastecimento
            by_venda[(item.idEmpresa, vc)].append(item)

        ocorrencias: list[CardFraudOcorrencia] = []
        seq = 0

        for (emp, venda), group in by_venda.items():
            enriched: list[tuple[datetime, datetime | None, AbastecimentoRestV1]] = []
            for ab in group:
                bico_dt = self._parse_iso(ab.dataHora)
                if not bico_dt:
                    continue
                baixa_dt = self._parse_iso(ab.dataHoraBaixa) if ab.dataHoraBaixa else None
                enriched.append((bico_dt, baixa_dt, ab))

            if not enriched:
                continue

            enriched.sort(key=lambda x: x[0])
            primeiro_dt, _, primeiro = enriched[0]
            ultimo_dt, _, _ = enriched[-1]

            retencoes: list[int] = []
            baixa_refs: list[datetime] = []
            for bico_dt, baixa_dt, _ab in enriched:
                if baixa_dt and baixa_dt >= bico_dt:
                    retencoes.append(int((baixa_dt - bico_dt).total_seconds() / 60))
                    baixa_refs.append(baixa_dt)

            retencao = max(retencoes) if retencoes else 0
            pag_dt = max(baixa_refs) if baixa_refs else ultimo_dt
            intervalo_bicos = max(0, int((ultimo_dt - primeiro_dt).total_seconds() / 60))
            qtd = len(enriched)

            trigger_gap = retencao > limiar
            real_venda = venda > 0
            trigger_lote = real_venda and qtd >= 2 and intervalo_bicos > BATCH_GAP_THRESHOLD_MIN
            if not trigger_gap and not trigger_lote:
                continue

            if trigger_gap and trigger_lote:
                gatilho = "AMBOS"
            elif trigger_lote:
                gatilho = "AGRUPAMENTO_LOTE"
            else:
                gatilho = "TIME_GAP"

            max_min = max(retencao, intervalo_bicos if trigger_lote else 0)
            nivel = "CRITICO" if max_min > CRITICAL_RETENTION_MIN else "ATENCAO"

            valor_cartao = round(sum(a.valorTotal for _, _, a in enriched), 2)
            meio = primeiro.formaPagamento or "CARTAO/TEF"
            counts: dict[tuple[int | None, str], int] = defaultdict(int)
            for _, _, a in enriched:
                counts[(a.idFrentista, a.nomeFrentista or "N/I")] += 1
            (fid, fname), _ = max(counts.items(), key=lambda x: x[1])

            hora_bico = self._fmt_dt(primeiro_dt)
            hora_baixa = self._fmt_dt(pag_dt)
            uuids = [a.uuid for _, _, a in enriched if a.uuid]

            detalhes = [
                CardFraudBicoDetalhe(
                    abastecimentoId=a.idAbastecimento,
                    uuid=a.uuid,
                    bico=a.bico,
                    horaBico=self._fmt_dt(bico_dt),
                    produto=a.descricaoProduto,
                    litros=a.litros,
                    valor=a.valorTotal,
                )
                for bico_dt, _baixa, a in enriched
            ]

            seq += 1
            ocorrencias.append(
                CardFraudOcorrencia(
                    id=f"CF-{emp}-{abs(venda)}-{seq}",
                    gatilho=gatilho,
                    frentistaId=fid,
                    frentistaNome=fname,
                    empresaCodigo=emp,
                    empresaNome=FILIAIS.get(emp, f"Empresa {emp}"),
                    vendaCodigo=venda if venda > 0 else 0,
                    uuid=uuids[0] if uuids else "",
                    horaBico=hora_bico,
                    horaBaixa=hora_baixa,
                    dataHora=hora_bico,
                    dataHoraBaixa=hora_baixa,
                    horaPrimeiroBico=hora_bico,
                    horaUltimoBico=self._fmt_dt(ultimo_dt),
                    horaBaixaCartao=hora_baixa,
                    tempoRetencaoMinutos=retencao,
                    intervaloBicosMinutos=intervalo_bicos,
                    qtdAbastecimentosAgrupados=qtd,
                    valorTotalCartao=valor_cartao,
                    nivelRisco=nivel,
                    meioPagamento=meio,
                    detalhes=detalhes,
                )
            )

        ocorrencias.sort(
            key=lambda o: (
                0 if o.nivelRisco == "CRITICO" else 1,
                -o.tempoRetencaoMinutos,
                -o.valorTotalCartao,
            )
        )
        return ocorrencias

    @staticmethod
    def _is_card_forma(forma: str | None) -> bool:
        blob = (forma or "").upper()
        if not blob:
            return False
        return any(kw in blob for kw in CARD_KEYWORDS)

    def _build_resumo(self, ocorrencias: list[CardFraudOcorrencia]) -> CardFraudResumo:
        if not ocorrencias:
            return CardFraudResumo()

        criticos = [o for o in ocorrencias if o.nivelRisco == "CRITICO"]
        atencao = [o for o in ocorrencias if o.nivelRisco == "ATENCAO"]
        by_frentista: dict[str, int] = defaultdict(int)
        for o in ocorrencias:
            by_frentista[o.frentistaNome or "N/I"] += 1

        top_name, top_qtd = "SEM REGISTRO NO PERIODO", 0
        if by_frentista:
            top_name, top_qtd = max(by_frentista.items(), key=lambda x: x[1])

        return CardFraudResumo(
            totalAgrupamentosSuspeitos=len(ocorrencias),
            totalCriticos=len(criticos),
            totalAtencao=len(atencao),
            valorTotalRetidoCartoes=round(sum(o.valorTotalCartao for o in ocorrencias), 2),
            valorCritico=round(sum(o.valorTotalCartao for o in criticos), 2),
            frentistaMaiorIncidencia=top_name,
            frentistaMaiorIncidenciaQtd=top_qtd,
            abastecimentosCriticosBanner=sum(o.qtdAbastecimentosAgrupados for o in criticos),
        )

    @staticmethod
    def _build_banner(resumo: CardFraudResumo) -> str | None:
        if resumo.totalCriticos <= 0 and resumo.abastecimentosCriticosBanner <= 0:
            return None
        qtd = resumo.abastecimentosCriticosBanner or resumo.totalCriticos
        valor_fmt = (
            f"R$ {resumo.valorCritico:,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )
        return (
            f"ALERTA DE PISTA: Detectamos {qtd} abastecimentos retidos por mais de "
            f"30 min e baixados em cartao (Total: {valor_fmt})."
        )

    @staticmethod
    def _parse_iso(raw: Any) -> datetime | None:
        if not raw:
            return None
        text = str(raw).strip()
        if text.endswith("Z"):
            text = text[:-1]
        if len(text) >= 6 and text[-6] in "+-" and text[-3] == ":":
            text = text[:-6]
        text = text.replace("T", " ")
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"):
            try:
                return datetime.strptime(text[:26], fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def _fmt_dt(dt: datetime) -> str:
        return dt.strftime("%Y-%m-%d %H:%M:%S")
