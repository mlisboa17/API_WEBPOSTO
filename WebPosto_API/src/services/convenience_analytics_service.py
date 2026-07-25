"""Serviço de analytics de conveniência — Curva ABC, ruptura, capital parado — Sprint 46."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ABCClassification(str, Enum):
    """Classificação ABC de produtos."""

    A = "A"
    B = "B"
    C = "C"


class StockStatus(str, Enum):
    """Status de estoque do produto."""

    NORMAL = "NORMAL"
    BAIXO = "BAIXO"
    CRITICO = "CRITICO"
    RUPTURA = "RUPTURA"
    PARADO = "PARADO"


class ProductABC(BaseModel):
    """Produto classificado na Curva ABC."""

    model_config = ConfigDict(frozen=True)

    produto_codigo: int
    produto_nome: str
    empresa_codigo: int | None = None
    faturamento: float
    faturamento_acumulado_pct: float
    margem_contribuicao: float
    margem_pct: float
    quantidade_vendida: float
    classificacao: ABCClassification
    ranking: int
    estoque_atual: float = 0.0
    venda_media_diaria: float = 0.0
    dias_cobertura: float | None = None
    lead_time_dias: int = 3
    status_estoque: StockStatus = StockStatus.NORMAL

    @property
    def is_rupture_risk(self) -> bool:
        if self.dias_cobertura is None:
            return self.estoque_atual <= 0
        return self.dias_cobertura < self.lead_time_dias

    @property
    def requires_action(self) -> bool:
        return self.classificacao == ABCClassification.A and self.is_rupture_risk


class StockBreakItem(BaseModel):
    """Item em ruptura ou risco de ruptura."""

    model_config = ConfigDict(frozen=True)

    produto_codigo: int
    produto_nome: str
    empresa_codigo: int | None = None
    classificacao_abc: ABCClassification
    estoque_atual: float
    venda_media_diaria: float
    dias_cobertura: float | None
    lead_time_dias: int
    status: StockStatus
    urgencia: str
    perda_estimada_dia: float | None = None

    @property
    def dias_para_ruptura(self) -> float | None:
        if self.dias_cobertura is None:
            return None
        return max(0, self.dias_cobertura)


class IdleStockItem(BaseModel):
    """Produto com estoque parado (capital de giro)."""

    model_config = ConfigDict(frozen=True)

    produto_codigo: int
    produto_nome: str
    empresa_codigo: int | None = None
    classificacao_abc: ABCClassification
    estoque_quantidade: float
    estoque_valor: float
    dias_sem_venda: int
    ultima_venda: str | None = None
    acao_sugerida: str
    prioridade: str


class ABCCurveSummary(BaseModel):
    """Resumo da Curva ABC consolidada."""

    model_config = ConfigDict(frozen=True)

    period_start: str
    period_end: str
    empresa_codigo: int | None = None
    total_produtos: int = 0
    total_faturamento: float = 0.0
    total_margem: float = 0.0
    produtos_a: int = 0
    produtos_b: int = 0
    produtos_c: int = 0
    faturamento_a_pct: float = 0.0
    faturamento_b_pct: float = 0.0
    faturamento_c_pct: float = 0.0
    produtos: list[ProductABC] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class StockBreakSummary(BaseModel):
    """Resumo de rupturas e riscos de estoque."""

    model_config = ConfigDict(frozen=True)

    data_analise: str
    empresa_codigo: int | None = None
    total_rupturas: int = 0
    total_riscos: int = 0
    rupturas_curva_a: int = 0
    perda_estimada_dia: float = 0.0
    items: list[StockBreakItem] = Field(default_factory=list)
    alert_level: str = "OK"
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class IdleStockSummary(BaseModel):
    """Resumo de estoque parado (capital de giro)."""

    model_config = ConfigDict(frozen=True)

    data_analise: str
    empresa_codigo: int | None = None
    total_itens_parados: int = 0
    capital_parado_30_dias: float = 0.0
    capital_parado_60_dias: float = 0.0
    capital_parado_total: float = 0.0
    items: list[IdleStockItem] = Field(default_factory=list)
    acao_sugerida: str | None = None
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ConvenienceAnalyticsService:
    """Analytics de conveniência: Curva ABC, ruptura de estoque e capital parado."""

    ABC_A_THRESHOLD = 80.0
    ABC_B_THRESHOLD = 95.0
    IDLE_DAYS_WARNING = 30
    IDLE_DAYS_CRITICAL = 60

    def __init__(
        self,
        a_threshold: float | None = None,
        b_threshold: float | None = None,
        default_lead_time: int = 3,
    ) -> None:
        self._a_threshold = a_threshold or self.ABC_A_THRESHOLD
        self._b_threshold = b_threshold or self.ABC_B_THRESHOLD
        self._default_lead_time = default_lead_time

    def calculate_abc_curve(
        self,
        products: list[dict[str, Any]],
        period_start: str,
        period_end: str,
        empresa_codigo: int | None = None,
    ) -> ABCCurveSummary:
        enriched: list[dict[str, Any]] = []
        for p in products:
            faturamento = float(p.get("faturamento") or p.get("valorTotal") or 0)
            custo = float(p.get("custo") or p.get("custoTotal") or 0)
            margem = faturamento - custo
            quantidade = float(p.get("quantidade") or p.get("quantidadeVendida") or 0)
            estoque = float(p.get("estoqueAtual") or p.get("estoque") or 0)
            venda_media = float(p.get("vendaMediaDiaria") or 0)

            if venda_media <= 0 and quantidade > 0:
                dias_periodo = max(1, self._days_between(period_start, period_end))
                venda_media = quantidade / dias_periodo

            enriched.append({
                "produto_codigo": int(p.get("produtoCodigo") or p.get("codigo") or 0),
                "produto_nome": str(p.get("produtoNome") or p.get("descricao") or p.get("nome") or ""),
                "empresa_codigo": int(p.get("empresaCodigo") or empresa_codigo or 0),
                "faturamento": faturamento,
                "margem": margem,
                "margem_pct": (margem / faturamento * 100) if faturamento > 0 else 0,
                "quantidade": quantidade,
                "estoque_atual": estoque,
                "venda_media_diaria": venda_media,
            })

        enriched.sort(key=lambda x: x["faturamento"], reverse=True)

        total_faturamento = sum(p["faturamento"] for p in enriched)
        total_margem = sum(p["margem"] for p in enriched)

        acumulado = 0.0
        abc_products: list[ProductABC] = []

        for i, p in enumerate(enriched):
            acumulado += p["faturamento"]
            pct_acumulado = (acumulado / total_faturamento * 100) if total_faturamento > 0 else 0

            if pct_acumulado <= self._a_threshold:
                classificacao = ABCClassification.A
            elif pct_acumulado <= self._b_threshold:
                classificacao = ABCClassification.B
            else:
                classificacao = ABCClassification.C

            dias_cobertura = None
            if p["venda_media_diaria"] > 0:
                dias_cobertura = p["estoque_atual"] / p["venda_media_diaria"]

            status = self._determine_stock_status(
                p["estoque_atual"], dias_cobertura, self._default_lead_time
            )

            abc_products.append(ProductABC(
                produto_codigo=p["produto_codigo"],
                produto_nome=p["produto_nome"],
                empresa_codigo=p["empresa_codigo"],
                faturamento=round(p["faturamento"], 2),
                faturamento_acumulado_pct=round(pct_acumulado, 2),
                margem_contribuicao=round(p["margem"], 2),
                margem_pct=round(p["margem_pct"], 2),
                quantidade_vendida=round(p["quantidade"], 2),
                classificacao=classificacao,
                ranking=i + 1,
                estoque_atual=round(p["estoque_atual"], 2),
                venda_media_diaria=round(p["venda_media_diaria"], 4),
                dias_cobertura=round(dias_cobertura, 2) if dias_cobertura is not None else None,
                lead_time_dias=self._default_lead_time,
                status_estoque=status,
            ))

        a_count = sum(1 for p in abc_products if p.classificacao == ABCClassification.A)
        b_count = sum(1 for p in abc_products if p.classificacao == ABCClassification.B)
        c_count = sum(1 for p in abc_products if p.classificacao == ABCClassification.C)

        a_fat = sum(p.faturamento for p in abc_products if p.classificacao == ABCClassification.A)
        b_fat = sum(p.faturamento for p in abc_products if p.classificacao == ABCClassification.B)
        c_fat = sum(p.faturamento for p in abc_products if p.classificacao == ABCClassification.C)

        return ABCCurveSummary(
            period_start=period_start,
            period_end=period_end,
            empresa_codigo=empresa_codigo,
            total_produtos=len(abc_products),
            total_faturamento=round(total_faturamento, 2),
            total_margem=round(total_margem, 2),
            produtos_a=a_count,
            produtos_b=b_count,
            produtos_c=c_count,
            faturamento_a_pct=round(a_fat / total_faturamento * 100, 2) if total_faturamento > 0 else 0,
            faturamento_b_pct=round(b_fat / total_faturamento * 100, 2) if total_faturamento > 0 else 0,
            faturamento_c_pct=round(c_fat / total_faturamento * 100, 2) if total_faturamento > 0 else 0,
            produtos=abc_products,
        )

    def detect_stock_breaks(
        self,
        abc_curve: ABCCurveSummary,
        data_analise: str | None = None,
    ) -> StockBreakSummary:
        breaks: list[StockBreakItem] = []

        for product in abc_curve.produtos:
            if product.status_estoque in {StockStatus.RUPTURA, StockStatus.CRITICO, StockStatus.BAIXO}:
                perda_estimada = None
                if product.venda_media_diaria > 0 and product.margem_pct > 0:
                    preco_medio = product.faturamento / max(product.quantidade_vendida, 1)
                    margem_unitaria = preco_medio * (product.margem_pct / 100)
                    perda_estimada = round(product.venda_media_diaria * margem_unitaria, 2)

                if product.status_estoque == StockStatus.RUPTURA:
                    urgencia = "IMEDIATA"
                elif product.classificacao == ABCClassification.A:
                    urgencia = "ALTA"
                elif product.classificacao == ABCClassification.B:
                    urgencia = "MEDIA"
                else:
                    urgencia = "BAIXA"

                breaks.append(StockBreakItem(
                    produto_codigo=product.produto_codigo,
                    produto_nome=product.produto_nome,
                    empresa_codigo=product.empresa_codigo,
                    classificacao_abc=product.classificacao,
                    estoque_atual=product.estoque_atual,
                    venda_media_diaria=product.venda_media_diaria,
                    dias_cobertura=product.dias_cobertura,
                    lead_time_dias=product.lead_time_dias,
                    status=product.status_estoque,
                    urgencia=urgencia,
                    perda_estimada_dia=perda_estimada,
                ))

        breaks.sort(key=lambda x: (
            0 if x.urgencia == "IMEDIATA" else 1 if x.urgencia == "ALTA" else 2 if x.urgencia == "MEDIA" else 3,
            x.dias_cobertura if x.dias_cobertura is not None else 999
        ))

        rupturas = [b for b in breaks if b.status == StockStatus.RUPTURA]
        riscos = [b for b in breaks if b.status in {StockStatus.CRITICO, StockStatus.BAIXO}]
        rupturas_a = [b for b in rupturas if b.classificacao_abc == ABCClassification.A]
        perda_total = sum(b.perda_estimada_dia or 0 for b in breaks)

        if rupturas_a:
            alert_level = "CRITICAL"
        elif rupturas:
            alert_level = "WARNING"
        elif riscos:
            alert_level = "INFO"
        else:
            alert_level = "OK"

        return StockBreakSummary(
            data_analise=data_analise or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            empresa_codigo=abc_curve.empresa_codigo,
            total_rupturas=len(rupturas),
            total_riscos=len(riscos),
            rupturas_curva_a=len(rupturas_a),
            perda_estimada_dia=round(perda_total, 2),
            items=breaks,
            alert_level=alert_level,
        )

    def detect_idle_stock(
        self,
        products: list[dict[str, Any]],
        data_analise: str | None = None,
        empresa_codigo: int | None = None,
    ) -> IdleStockSummary:
        idle_items: list[IdleStockItem] = []

        for p in products:
            estoque_qtd = float(p.get("estoqueAtual") or p.get("estoque") or 0)
            if estoque_qtd <= 0:
                continue

            dias_sem_venda = int(p.get("diasSemVenda") or p.get("diasParado") or 0)
            if dias_sem_venda < self.IDLE_DAYS_WARNING:
                continue

            preco_custo = float(p.get("precoCusto") or p.get("custo") or 0)
            estoque_valor = estoque_qtd * preco_custo

            ultima_venda = p.get("ultimaVenda") or p.get("dataUltimaVenda")

            classificacao = ABCClassification(p.get("classificacaoAbc", "C"))

            if dias_sem_venda >= self.IDLE_DAYS_CRITICAL:
                acao = "DEVOLUÇÃO ou QUEIMA"
                prioridade = "ALTA"
            elif classificacao == ABCClassification.C:
                acao = "PROMOÇÃO para liberação"
                prioridade = "MEDIA"
            else:
                acao = "MONITORAR movimentação"
                prioridade = "BAIXA"

            idle_items.append(IdleStockItem(
                produto_codigo=int(p.get("produtoCodigo") or p.get("codigo") or 0),
                produto_nome=str(p.get("produtoNome") or p.get("descricao") or ""),
                empresa_codigo=int(p.get("empresaCodigo") or empresa_codigo or 0),
                classificacao_abc=classificacao,
                estoque_quantidade=round(estoque_qtd, 2),
                estoque_valor=round(estoque_valor, 2),
                dias_sem_venda=dias_sem_venda,
                ultima_venda=str(ultima_venda) if ultima_venda else None,
                acao_sugerida=acao,
                prioridade=prioridade,
            ))

        idle_items.sort(key=lambda x: (-x.dias_sem_venda, -x.estoque_valor))

        capital_30 = sum(i.estoque_valor for i in idle_items if i.dias_sem_venda >= 30 and i.dias_sem_venda < 60)
        capital_60 = sum(i.estoque_valor for i in idle_items if i.dias_sem_venda >= 60)
        capital_total = capital_30 + capital_60

        acao_geral = None
        if capital_60 > 10000:
            acao_geral = "AÇÃO IMEDIATA: R$ {:.2f} em estoque parado há mais de 60 dias".format(capital_60)
        elif capital_total > 5000:
            acao_geral = "Revisar política de compras e giro de estoque"

        return IdleStockSummary(
            data_analise=data_analise or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            empresa_codigo=empresa_codigo,
            total_itens_parados=len(idle_items),
            capital_parado_30_dias=round(capital_30, 2),
            capital_parado_60_dias=round(capital_60, 2),
            capital_parado_total=round(capital_total, 2),
            items=idle_items,
            acao_sugerida=acao_geral,
        )

    def _determine_stock_status(
        self,
        estoque: float,
        dias_cobertura: float | None,
        lead_time: int,
    ) -> StockStatus:
        if estoque <= 0:
            return StockStatus.RUPTURA
        if dias_cobertura is None:
            return StockStatus.NORMAL
        if dias_cobertura < lead_time * 0.5:
            return StockStatus.CRITICO
        if dias_cobertura < lead_time:
            return StockStatus.BAIXO
        return StockStatus.NORMAL

    def _days_between(self, start: str, end: str) -> int:
        try:
            d1 = datetime.fromisoformat(start.replace("Z", "+00:00"))
            d2 = datetime.fromisoformat(end.replace("Z", "+00:00"))
            return max(1, (d2 - d1).days)
        except Exception:
            return 30
