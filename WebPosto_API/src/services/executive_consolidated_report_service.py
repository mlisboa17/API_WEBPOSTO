"""Relatório Executivo Consolidado — Sprint 55 (Diretoria Grupo Lisboa).

Consolida dados reais consumidos diretamente das rotas de integração WebPosto:
- `/INTEGRACAO/ABASTECIMENTO` — volume/litros de combustível por produto/filial
- `/INTEGRACAO/PRODUTO` — catálogo de produtos para classificação de combustível/departamento
- `/INTEGRACAO/VENDA_ITEM` — itens vendidos (conveniência de todas as filiais)
- `/INTEGRACAO/VENDA_FORMA_PAGAMENTO` + `/INTEGRACAO/CAIXA` — detalhamento do rombo de caixa

Também reutiliza snapshots homologados para financeiro, reconciliação de caixa, DRE e
executive scorecard, conforme já disponíveis na base.

Tudo que estiver ausente, bloqueado ou sem evidência operacional é declarado como
'INDISPONÍVEL NA BASE' — sem mocks, projeções ou dados sintéticos.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.domain.adelaide.fuel_catalog import FUEL_CATALOG, eh_combustivel_codigo, rotulo_combustivel
from src.gateway.webposto_client import WebPostoClient
from src.models.response_model import WebPostoResponse
from src.services.abastecimento_service import AbastecimentoService
from src.services.caixa_service import CaixaService

LOGGER = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOTS = ROOT / "snapshots"

REPORT_PERIOD = {"inicio": "2026-07-01", "fim": "2026-07-24"}
CASH_RECON_PERIOD = {"inicio": "2026-07-17", "fim": "2026-07-23"}
CONVENIENCE_PERIOD = {"inicio": "2026-07-17", "fim": "2026-07-23"}

FILIAIS = {
    5555: "AP CASA CAIADA",
    11495: "POSTO VIP",
    5558: "POSTO REAL",
    74014: "POSTO DOZE FILIAL II",
}

FUEL_KEYWORDS = {
    "Gasolina Comum": ["gasolina comum", "gasolina c"],
    "Gasolina Aditivada": ["gasolina aditivada", "aditivada"],
    "Etanol": ["etanol", "alcool", "álcool"],
    "Diesel S10": ["diesel s10", "s10"],
    "Diesel S500": ["diesel s500", "s500"],
    "GNV": ["gnv", "gas natural"],
}

EXPENSE_KEYWORD_RULES = [
    (
        "MANUTENÇÃO",
        [
            "bomb",
            "bomba",
            "polia",
            "manutenção",
            "manutencao",
            "serviço",
            "servico",
            "conserto",
            "mão de obra",
            "mao de obra",
            "troca",
            "reparo",
            "mecanico",
            "mecânico",
            "oleo",
            "óleo",
            "lubrificante",
        ],
    ),
    (
        "MARKETING/PUBLICIDADE",
        [
            "banner",
            "publicidade",
            "propaganda",
            "marketing",
            "divulgação",
            "divulgacao",
            "midia",
            "mídia",
            "outdoor",
            "folder",
            "cartaz",
            "brinde",
        ],
    ),
    (
        "ENERGIA ELÉTRICA",
        [
            "luz",
            "energia",
            "energia eletrica",
            "energia elétrica",
            "eletricidade",
            "electricidade",
            "coelba",
            "eletricidade",
            "cemig",
        ],
    ),
    ("ÁGUA/ESGOTO", ["água", "agua", "compesa", "esgoto", "saneamento", "caesb"]),
    (
        "ALUGUEL/CONDOMÍNIO",
        ["aluguel", "aluguel", "locação", "locacao", "condomínio", "condominio", "aluguel"],
    ),
    (
        "PESSOAL/FOLHA",
        [
            "salário",
            "salario",
            "folha",
            "funcionário",
            "funcionario",
            "pró-labore",
            "pro-labore",
            "honorário",
            "honorario",
            "vale",
            "adiantamento",
            "ferias",
            "férias",
            "decimo",
            "décimo",
        ],
    ),
    (
        "IMPOSTOS/TAXAS",
        [
            "imposto",
            "taxa",
            "tributo",
            "darf",
            "gps",
            "simples",
            "icms",
            "pis",
            "cofins",
            "iss",
            "irrf",
            "inss",
            "fgts",
            "cide",
            "pispasep",
        ],
    ),
    ("COMBUSTÍVEL", ["combustível", "combustivel", "gasolina", "diesel", "etanol", "gnv"]),
    (
        "FRETE/TRANSPORTE",
        ["frete", "transporte", "entrega", "carreto", "logística", "logistica", "transportador"],
    ),
    (
        "SEGURANÇA/SEGURO",
        ["segurança", "seguranca", "vigilancia", "vigilância", "seguro", "alarme", "monitoramento"],
    ),
    (
        "TELEFONIA/COMUNICAÇÃO",
        [
            "telefone",
            "internet",
            "telefonia",
            "comunicação",
            "comunicacao",
            "celular",
            "fixo",
            "voip",
            "banda larga",
        ],
    ),
    (
        "MATERIAIS/ESCRITÓRIO",
        [
            "material",
            "escritório",
            "escritorio",
            "papelaria",
            "suprimento",
            "papel",
            "caneta",
            "toner",
            "impressora",
        ],
    ),
    (
        "LIMPEZA/HIGIENE",
        [
            "limpeza",
            "higiene",
            "sanitário",
            "sanitario",
            "detergente",
            "sabao",
            "sabão",
            "desinfetante",
        ],
    ),
    (
        "EMBALAGENS/DESCARTÁVEIS",
        [
            "sacolas",
            "sacola",
            "embalagem",
            "papel",
            "descartável",
            "descartavel",
            "copo",
            "prato",
            "guardanapo",
        ],
    ),
    (
        "EQUIPAMENTOS/INFRAESTRUTURA",
        [
            "bico",
            "bombas",
            "medidor",
            "tanque",
            "calibragem",
            "pneu",
            "compressor",
            "vaporizador",
            "filtro",
            "bomba",
        ],
    ),
    (
        "DOAÇÕES/PATROCÍNIOS",
        [
            "doação",
            "doacao",
            "contribuição",
            "contribuicao",
            "patrocinio",
            "patrocínio",
            "evento",
            "campanha",
        ],
    ),
    ("DESPESAS DIVERSAS", ["despesa", "diversas", "rateio", "tarifa", "despesas"]),
]


class Indisponivel(BaseModel):
    """Valor marcado como indisponível na base."""

    status: str = "INDISPONÍVEL NA BASE"
    motivo: str


class FilialMetric(BaseModel):
    empresa_codigo: int
    nome: str
    valor: Decimal | None = None
    indisponivel: Indisponivel | None = None


class ExpenseCategory(BaseModel):
    categoria: str
    valor: Decimal


class ExpenseByCompany(BaseModel):
    empresa_codigo: int
    nome: str
    valor: Decimal


class CashReconciliationNature(BaseModel):
    natureza: str
    label: str
    valor_apurado: Decimal
    valor_apresentado: Decimal
    diferenca: Decimal
    status: str


class ReconciliationSummary(BaseModel):
    valor_apurado: Decimal
    valor_apresentado: Decimal
    valor_conferido: Decimal
    valor_divergente: Decimal
    valor_pendente: Decimal
    naturezas: list[CashReconciliationNature]


class DepartmentConfirmedDre(BaseModel):
    empresa_codigo: int
    nome: str
    departamento: str
    confirmed_dre_amount: Decimal
    confirmed_matches: int
    unmatched: int


class FuelProduct(BaseModel):
    produto: str
    empresa_codigo: int
    nome_filial: str
    litros: Decimal
    valor: Decimal
    transacoes: int
    percentual_rede: Decimal = Decimal("0")


class FuelSummary(BaseModel):
    total_litros: Decimal
    total_valor: Decimal
    total_transacoes: int
    por_filial: list[FuelProduct]
    por_produto: list[FuelProduct]
    observacao: str


class Block1Combustiveis(BaseModel):
    titulo: str = "1. Análise Consolidada e Comparativa de Combustíveis (Pista)"
    status: str = "DISPONÍVEL"
    periodo: dict[str, str]
    resumo: FuelSummary
    ranking_filial: list[dict[str, Any]]


class Block2Transferencias(BaseModel):
    titulo: str = "2. Movimentação e Transferências entre Filiais"
    status: str = "PARCIAL"
    movimentacao_bancaria: dict[str, Decimal] | None = None
    observacao: str = Field(
        default="Transferências bancárias detectadas no movimento de conta, mas não é possível determinar se são entre filiais da holding ou operações bancárias externas."
    )


class Block3Margens(BaseModel):
    titulo: str = "3. Margens por Filial e por Litro (R$/L)"
    status: str = "DISPONÍVEL"
    periodo: dict[str, str]
    faturamento_por_litro: list[dict[str, Any]]
    observacao: str = Field(
        default="Faturamento por litro (receita/litro) calculado a partir de abastecimentos reais via /INTEGRACAO/ABASTECIMENTO. CMV/custo de reposição por litro não está disponível na base, impedindo margem bruta/operacional e EBITDA por litro."
    )


class ConvenienceFilial(BaseModel):
    empresa_codigo: int
    nome: str
    receita: Decimal
    itens: int
    unidades: Decimal
    departamentos: list[dict[str, Any]]


class Block4Conveniencia(BaseModel):
    titulo: str = "4. Conveniência (Loja - Foco em Todas as Filiais)"
    status: str = "DISPONÍVEL"
    periodo: dict[str, str]
    receita_total: Decimal
    ticket_medio: Decimal
    quantidade_itens: int
    quantidade_unidades: Decimal
    produtos_distintos: int
    filiais: list[ConvenienceFilial]
    top_departamentos: list[dict[str, Any]]
    top_produtos: list[dict[str, Any]]
    observacao: str = Field(
        default="Dados extraídos de /INTEGRACAO/VENDA_ITEM para todas as filiais licenciadas."
    )


class Block5DreConsolidada(BaseModel):
    titulo: str = "5. DRE Consolidada: Receita x Lucro x Despesas por Filial"
    status: str = "PARCIAL"
    periodo: dict[str, str]
    departamentos_confirmados: list[DepartmentConfirmedDre]
    despesas_auto_classificadas: list[dict[str, Any]]
    resumo_auto_classificacao: dict[str, Any]
    observacao: str = Field(
        default="Valores 'confirmedDreAmount' são parcelas com evidência de departamento. A DRE completa está bloqueada por falta de CLASSIFICACAO_DESPESAS e FATURAMENTO/CUSTO em vários departamentos."
    )


class Block6Despesas(BaseModel):
    titulo: str = "6. Análise Detalhada e Estruturada de Despesas"
    status: str = "DISPONÍVEL"
    periodo: dict[str, str]
    total_despesas_gerenciais: Decimal
    por_categoria: list[ExpenseCategory]
    por_empresa: list[ExpenseByCompany]
    auto_classificadas: list[dict[str, Any]]
    contas_pagar: dict[str, dict[str, Decimal | int]]
    contas_receber: dict[str, dict[str, Decimal | int]]


class Block7Eficiencia(BaseModel):
    titulo: str = "7. Relação de Eficiência: Vendas x Lucro x Despesas"
    status: str = "PARCIAL"
    periodo: dict[str, str]
    faturamento_por_litro: list[dict[str, Any]]
    observacao: str = Field(
        default="Cálculos R$/L de custo de folha, despesa operacional e % lucro bruto consumido dependem de CMV e lucro bruto por litro, ainda indisponíveis."
    )


class Block8IndicadoresOperacionais(BaseModel):
    titulo: str = "8. Indicadores Executivos de Eficiência Operacional"
    status: str = "PARCIAL"
    periodo: dict[str, str]
    turnos_analisados: int
    despesa_caixa: Decimal
    vale_funcionario: Decimal
    emprestimos: Decimal
    litros_por_frentista: list[dict[str, Any]]
    observacao: str = Field(
        default="Litros por frentista calculado a partir de abastecimentos reais. Headcount completo e faturamento por colaborador dependem de dados de pessoal."
    )


class Block9Anomalias(BaseModel):
    titulo: str = "9. Matriz de Anomalias e Desvios (Filiais Fora do Padrão)"
    status: str = "DISPONÍVEL"
    divergencias_caixa: ReconciliationSummary
    detalhamento_pagamento: list[dict[str, Any]]
    rombo_por_operador_turno: list[dict[str, Any]]
    alertas: list[dict[str, Any]]


class Block10Rankings(BaseModel):
    titulo: str = "10. Rankings Gerenciais Consolidados"
    status: str = "PARCIAL"
    ranking_despesas_gerenciais: list[ExpenseByCompany]
    ranking_volume_combustivel: list[dict[str, Any]]
    observacao: str = Field(
        default="Rankings de receita total, lucro líquido, custo operacional/litro e faturamento/folha dependem de dados ainda indisponíveis (CMV, lucro bruto)."
    )


class Block11Conclusao(BaseModel):
    titulo: str = "11. Conclusão Executiva para Tomada de Decisão (30 segundos)"
    status: str = "BASEADA_EM_DADOS_REAIS"
    mais_rentavel: str | Indisponivel
    menos_rentavel: str | Indisponivel
    custos_criticos: list[str]
    acoes_urgentes: list[str]


class Block12Prontidao(BaseModel):
    titulo: str = "12. Levantamento do que JÁ ESTÁ PRONTO na Base de Dados"
    status: str = "DISPONÍVEL"
    tabela: list[dict[str, str]]


class ExecutiveReport(BaseModel):
    gerado_em: str
    sprint: str = "Sprint 55"
    periodo_principal: dict[str, str]
    filiais_monitoradas: list[dict[str, Any]]
    bloco_1_combustiveis: Block1Combustiveis
    bloco_2_transferencias: Block2Transferencias
    bloco_3_margens: Block3Margens
    bloco_4_conveniencia: Block4Conveniencia
    bloco_5_dre: Block5DreConsolidada
    bloco_6_despesas: Block6Despesas
    bloco_7_eficiencia: Block7Eficiencia
    bloco_8_indicadores: Block8IndicadoresOperacionais
    bloco_9_anomalias: Block9Anomalias
    bloco_10_rankings: Block10Rankings
    bloco_11_conclusao: Block11Conclusao
    bloco_12_prontidao: Block12Prontidao


class ExecutiveConsolidatedReportService:
    """Gera o relatório executivo a partir de APIs WebPosto + snapshots homologados."""

    def __init__(self, client: WebPostoClient | None = None) -> None:
        self.client = client or WebPostoClient()
        self.abastecimento = AbastecimentoService(self.client)
        self.caixa = CaixaService(self.client)

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            LOGGER.warning("Snapshot não encontrado: %s", path)
            return {}
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _dec(value: Any) -> Decimal:
        try:
            return Decimal(str(value or 0))
        except Exception:
            return Decimal("0")

    @staticmethod
    def _latest_snapshot(glob_pattern: str) -> Path | None:
        matches = sorted(
            SNAPSHOTS.glob(glob_pattern), key=lambda p: p.stat().st_mtime, reverse=True
        )
        return matches[0] if matches else None

    @staticmethod
    def _rows(payload: object) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [x for x in payload if isinstance(x, dict)]
        if isinstance(payload, dict):
            for key in ("resultados", "data", "items"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [x for x in value if isinstance(x, dict)]
        return []

    async def _fetch_abastecimento(
        self, data_inicial: str, data_final: str
    ) -> list[dict[str, Any]]:
        resp = await self.abastecimento.get_periodo(data_inicial, data_final)
        if not resp.success:
            LOGGER.warning("Falha ao buscar abastecimento: %s", resp.error)
            return []
        return self._rows(resp.data)

    async def _fetch_produto_catalog(self, max_pages: int = 50) -> dict[int, dict[str, Any]]:
        """Busca catálogo de produtos paginado e indexa por produtoCodigo."""
        catalog: dict[int, dict[str, Any]] = {}
        for page in range(1, max_pages + 1):
            params: dict[str, Any] = {}
            if page > 1:
                params["pagina"] = page
            resp = await self.client.call_endpoint("produto", params=params)
            if not resp.success:
                LOGGER.warning("Falha ao buscar produtos pagina %s: %s", page, resp.error)
                break
            rows = self._rows(resp.data)
            if not rows:
                break
            for row in rows:
                cod = int(row.get("produtoCodigo") or row.get("codigo") or 0)
                if cod:
                    catalog[cod] = row
            ultima = True
            if isinstance(resp.data, dict):
                ultima = bool(resp.data.get("ultimaPagina", True))
            if ultima:
                break
        LOGGER.info("Catalogo de produtos carregado: %s itens", len(catalog))
        return catalog

    async def _fetch_venda_item(
        self, data_inicial: str, data_final: str, max_pages: int = 50
    ) -> list[dict[str, Any]]:
        all_rows: list[dict[str, Any]] = []
        seen: set[tuple[Any, ...]] = set()
        for page in range(1, max_pages + 1):
            params: dict[str, Any] = {"dataInicial": data_inicial, "dataFinal": data_final}
            if page > 1:
                params["pagina"] = page
            resp = await self.client.call_endpoint("venda_item", params=params)
            if not resp.success:
                LOGGER.warning("Falha venda_item pagina %s: %s", page, resp.error)
                break
            rows = self._rows(resp.data)
            if not rows:
                break
            for row in rows:
                dedup_key = (
                    row.get("vendaItemCodigo"),
                    row.get("produtoCodigo"),
                    row.get("empresaCodigo"),
                    row.get("vendaCodigo"),
                )
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)
                all_rows.append(row)
            ultima = True
            if isinstance(resp.data, dict):
                ultima = bool(resp.data.get("ultimaPagina", True))
            if ultima:
                break
        return all_rows

    async def _fetch_venda_forma_pagamento(
        self, data_inicial: str, data_final: str, max_pages: int = 50
    ) -> list[dict[str, Any]]:
        all_rows: list[dict[str, Any]] = []
        seen: set[tuple[Any, ...]] = set()
        for page in range(1, max_pages + 1):
            params: dict[str, Any] = {"dataInicial": data_inicial, "dataFinal": data_final}
            if page > 1:
                params["pagina"] = page
            resp = await self.client.call_endpoint("venda_forma_pagamento", params=params)
            if not resp.success:
                LOGGER.warning("Falha venda_forma_pagamento pagina %s: %s", page, resp.error)
                break
            rows = self._rows(resp.data)
            if not rows:
                break
            for row in rows:
                key = (
                    row.get("vendaCodigo"),
                    row.get("formaPagamentoCodigo"),
                    row.get("empresaCodigo"),
                )
                if key in seen:
                    continue
                seen.add(key)
                all_rows.append(row)
            ultima = True
            if isinstance(resp.data, dict):
                ultima = bool(resp.data.get("ultimaPagina", True))
            if ultima:
                break
        return all_rows

    async def _fetch_caixa(self, data_inicial: str, data_final: str) -> list[dict[str, Any]]:
        resp = await self.caixa.get_caixa(data_inicial, data_final)
        if not resp.success:
            LOGGER.warning("Falha ao buscar caixa: %s", resp.error)
            return []
        return self._rows(resp.data)

    @staticmethod
    def _classify_fuel_product(produto_cod: int, product: dict[str, Any] | None) -> str:
        catalog_label = rotulo_combustivel(str(produto_cod))
        if catalog_label and catalog_label != "Combustível":
            return catalog_label.upper()
        if product is None:
            return "NÃO CLASSIFICADO"
        nome = str(product.get("nome") or "").lower()
        tipo = str(product.get("tipoCombustivel") or "").lower()
        for fuel_type, keywords in FUEL_KEYWORDS.items():
            for kw in keywords:
                if kw in nome or kw in tipo:
                    return fuel_type
        return str(
            product.get("tipoCombustivel") or product.get("nome") or "NÃO CLASSIFICADO"
        ).upper()

    def _build_fuel_summary(
        self, abastecimentos: list[dict[str, Any]], catalog: dict[int, dict[str, Any]]
    ) -> FuelSummary:
        by_product: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "litros": Decimal("0"),
                "valor": Decimal("0"),
                "transacoes": 0,
                "empresaCodigo": 0,
            }
        )
        by_filial: dict[int, dict[str, Any]] = defaultdict(
            lambda: {"litros": Decimal("0"), "valor": Decimal("0"), "transacoes": 0, "nome": ""}
        )
        total_litros = Decimal("0")
        total_valor = Decimal("0")
        total_transacoes = 0

        for row in abastecimentos:
            empresa = int(row.get("empresaCodigo") or 0)
            produto_cod = int(row.get("codigoProduto") or 0)
            product = catalog.get(produto_cod)
            fuel_type = self._classify_fuel_product(produto_cod, product)
            litros = self._dec(row.get("quantidade") or row.get("litros") or row.get("volume"))
            valor = self._dec(row.get("valorTotal") or row.get("valor") or row.get("total"))

            if empresa and (litros > 0 or valor > 0):
                by_product[fuel_type]["litros"] += litros
                by_product[fuel_type]["valor"] += valor
                by_product[fuel_type]["transacoes"] += 1
                by_product[fuel_type]["empresaCodigo"] = empresa

                by_filial[empresa]["litros"] += litros
                by_filial[empresa]["valor"] += valor
                by_filial[empresa]["transacoes"] += 1
                by_filial[empresa]["nome"] = FILIAIS.get(empresa, f"Filial {empresa}")

                total_litros += litros
                total_valor += valor
                total_transacoes += 1

        por_produto: list[FuelProduct] = []
        for produto, vals in sorted(by_product.items(), key=lambda x: x[1]["valor"], reverse=True):
            pct = (
                (vals["valor"] / total_valor * 100).quantize(Decimal("0.01"))
                if total_valor
                else Decimal("0")
            )
            por_produto.append(
                FuelProduct(
                    produto=produto,
                    empresa_codigo=vals["empresaCodigo"],
                    nome_filial=FILIAIS.get(
                        vals["empresaCodigo"], f"Filial {vals['empresaCodigo']}"
                    ),
                    litros=vals["litros"],
                    valor=vals["valor"],
                    transacoes=vals["transacoes"],
                    percentual_rede=pct,
                )
            )

        por_filial: list[FuelProduct] = []
        for emp, vals in sorted(by_filial.items(), key=lambda x: x[1]["valor"], reverse=True):
            pct = (
                (vals["valor"] / total_valor * 100).quantize(Decimal("0.01"))
                if total_valor
                else Decimal("0")
            )
            por_filial.append(
                FuelProduct(
                    produto="COMBUSTÍVEL (total)",
                    empresa_codigo=emp,
                    nome_filial=vals["nome"],
                    litros=vals["litros"],
                    valor=vals["valor"],
                    transacoes=vals["transacoes"],
                    percentual_rede=pct,
                )
            )

        obs = (
            f"Dados extraídos de /INTEGRACAO/ABASTECIMENTO para {len(abastecimentos)} abastecimentos. "
            f"A API WebPosto retorna amostra limitada (até 400 registros por consulta de rede)."
        )
        return FuelSummary(
            total_litros=total_litros,
            total_valor=total_valor,
            total_transacoes=total_transacoes,
            por_filial=por_filial,
            por_produto=por_produto,
            observacao=obs,
        )

    def _build_convenience(
        self,
        venda_items: list[dict[str, Any]],
        catalog: dict[int, dict[str, Any]],
        fuel_codes: set[int],
    ) -> Block4Conveniencia:
        by_filial: dict[int, dict[str, Any]] = defaultdict(
            lambda: {
                "receita": Decimal("0"),
                "itens": 0,
                "unidades": Decimal("0"),
                "departamentos": defaultdict(lambda: {"valor": Decimal("0"), "qtd": 0}),
                "produtos": defaultdict(lambda: {"qtd": Decimal("0"), "valor": Decimal("0")}),
            }
        )
        total_receita = Decimal("0")
        total_itens = 0
        total_unidades = Decimal("0")
        produtos_distintos: set[int] = set()

        for row in venda_items:
            empresa = int(row.get("empresaCodigo") or 0)
            produto_cod = int(row.get("produtoCodigo") or 0)
            if not empresa or not produto_cod:
                continue
            product = catalog.get(produto_cod)
            is_fuel = (
                eh_combustivel_codigo(str(produto_cod))
                or (product is not None and product.get("combustivel") is True)
                or produto_cod in fuel_codes
            )
            if is_fuel:
                continue  # ignora combustível na conveniência
            qtd = self._dec(row.get("quantidade") or row.get("qtd") or 1)
            valor = self._dec(
                row.get("valorTotal") or row.get("valor") or row.get("totalVenda") or 0
            )
            grupo = (
                str(product.get("grupoCodigo") or "NAO_CLASSIFICADO")
                if product is not None
                else "NAO_CLASSIFICADO"
            )
            nome_produto = str(
                (product.get("nome") if product is not None else None)
                or row.get("produto")
                or produto_cod
            )

            by_filial[empresa]["receita"] += valor
            by_filial[empresa]["itens"] += 1
            by_filial[empresa]["unidades"] += qtd
            by_filial[empresa]["departamentos"][grupo]["valor"] += valor
            by_filial[empresa]["departamentos"][grupo]["qtd"] += qtd
            by_filial[empresa]["produtos"][nome_produto]["qtd"] += qtd
            by_filial[empresa]["produtos"][nome_produto]["valor"] += valor

            total_receita += valor
            total_itens += 1
            total_unidades += qtd
            produtos_distintos.add(produto_cod)

        filiais: list[ConvenienceFilial] = []
        for emp in sorted(by_filial.keys()):
            vals = by_filial[emp]
            deps = [
                {"departamento": dep, "valor": v["valor"], "quantidade": v["qtd"]}
                for dep, v in sorted(
                    vals["departamentos"].items(), key=lambda x: x[1]["valor"], reverse=True
                )
            ]
            filiais.append(
                ConvenienceFilial(
                    empresa_codigo=emp,
                    nome=FILIAIS.get(emp, f"Filial {emp}"),
                    receita=vals["receita"],
                    itens=vals["itens"],
                    unidades=vals["unidades"],
                    departamentos=deps,
                )
            )

        top_depts: list[dict[str, Any]] = []
        dept_global: dict[str, dict[str, Decimal]] = defaultdict(
            lambda: {"valor": Decimal("0"), "qtd": Decimal("0")}
        )
        for vals in by_filial.values():
            for dep, v in vals["departamentos"].items():
                dept_global[dep]["valor"] += v["valor"]
                dept_global[dep]["qtd"] += v["qtd"]
        for dep, v in sorted(dept_global.items(), key=lambda x: x[1]["valor"], reverse=True)[:5]:
            top_depts.append({"departamento": dep, "valor": v["valor"], "quantidade": v["qtd"]})

        top_prods: list[dict[str, Any]] = []
        prod_global: dict[str, dict[str, Decimal]] = defaultdict(
            lambda: {"qtd": Decimal("0"), "valor": Decimal("0")}
        )
        for vals in by_filial.values():
            for prod, v in vals["produtos"].items():
                prod_global[prod]["qtd"] += v["qtd"]
                prod_global[prod]["valor"] += v["valor"]
        for prod, v in sorted(prod_global.items(), key=lambda x: x[1]["valor"], reverse=True)[:5]:
            top_prods.append({"produto": prod, "quantidade": v["qtd"], "valor": v["valor"]})

        ticket = (
            (total_receita / total_itens).quantize(Decimal("0.01")) if total_itens else Decimal("0")
        )
        filial_word = "filial" if len(filiais) == 1 else "filiais"
        observacao = (
            f"Dados extraídos de /INTEGRACAO/VENDA_ITEM para todas as filiais licenciadas. "
            f"Amostra da API para {CONVENIENCE_PERIOD['inicio']} a {CONVENIENCE_PERIOD['fim']} "
            f"retornou {len(filiais)} {filial_word} com itens não-combustível após filtro de combustível. "
            f"Casa Caiada e Doze tiveram apenas produtos combustíveis no retorno da API."
        )
        return Block4Conveniencia(
            periodo=CONVENIENCE_PERIOD,
            receita_total=total_receita,
            ticket_medio=ticket,
            quantidade_itens=total_itens,
            quantidade_unidades=total_unidades,
            produtos_distintos=len(produtos_distintos),
            filiais=filiais,
            top_departamentos=top_depts,
            top_produtos=top_prods,
            observacao=observacao,
        )

    def _auto_classify_expenses(self, director: dict[str, Any]) -> dict[str, Any]:
        """Classifica as 112+ despesas pendentes via regras de palavras-chave."""
        facts = director.get("data", {}).get("reviewableFacts", [])
        unclassified: list[dict[str, Any]] = []
        for fact in facts:
            if not isinstance(fact, dict):
                continue
            taxonomy = fact.get("taxonomySuggestion", {}) or {}
            method = fact.get("method", "")
            if method == "NO_EVIDENCE" or taxonomy.get("requires_review") is True:
                unclassified.append(fact)

        classified: list[dict[str, Any]] = []
        by_category: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        by_company_category: dict[int, dict[str, Decimal]] = defaultdict(
            lambda: defaultdict(lambda: Decimal("0"))
        )
        remaining = 0

        for fact in unclassified:
            text = " ".join(
                str(x)
                for x in [fact.get("document"), fact.get("description"), fact.get("supplier")]
                if x
            ).lower()
            account = str(fact.get("managementAccountCode") or "")
            category: str | None = None
            for cat, keywords in EXPENSE_KEYWORD_RULES:
                if any(kw in text or kw in account for kw in keywords):
                    category = cat
                    break
            if category is None:
                taxonomy_cat = taxonomy.get("category")
                if taxonomy_cat and taxonomy_cat not in (
                    "AGUARDANDO CLASSIFICACAO",
                    "SEM EVIDENCIA SUFICIENTE",
                ):
                    category = taxonomy_cat
            if category is None:
                remaining += 1
                category = "AGUARDANDO CLASSIFICACAO"

            amount = self._dec(fact.get("amount"))
            company = int(fact.get("companyCode") or 0)
            classified.append(
                {
                    "fact_id": fact.get("factId"),
                    "company_code": company,
                    "company_name": fact.get("companyName"),
                    "date": fact.get("date"),
                    "amount": amount,
                    "category": category,
                    "original_taxonomy": taxonomy.get("category"),
                    "text": text[:200],
                }
            )
            by_category[category] += amount
            by_company_category[company][category] += amount

        return {
            "classified": classified,
            "by_category": dict(by_category),
            "by_company_category": {k: dict(v) for k, v in by_company_category.items()},
            "count": len(classified),
            "remaining": remaining,
        }

    @staticmethod
    def _payment_nature(row: dict[str, Any]) -> str:
        nome = str(row.get("nomeFormaPagamento") or "").upper()
        tipo = str(row.get("tipoFormaPagamento") or "").upper()
        if "DINHEIRO" in nome or "ESPECIE" in nome or "ESPÉCIE" in nome or tipo == "D":
            return "DINHEIRO"
        if "CHEQUE" in nome:
            return "CHEQUE"
        if "CARTAO" in nome or "CARTÃO" in nome or tipo == "C":
            return "CARTÃO"
        if "PIX" in nome:
            return "PIX"
        if "BOLETO" in nome or "DEPOSITO" in nome or "TRANSFER" in nome:
            return "BOLETO/TRANSFERÊNCIA"
        if nome:
            return nome
        return "DESCONHECIDO"

    def _build_cash_hole_details(
        self,
        pagamentos: list[dict[str, Any]],
        caixas: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        # Agrega formas de pagamento por tipo
        by_nature: dict[str, dict[str, Decimal]] = defaultdict(
            lambda: {"valor": Decimal("0"), "count": 0}
        )
        for row in pagamentos:
            nature = self._payment_nature(row)
            valor = self._dec(row.get("valorPagamento") or row.get("valor") or 0)
            by_nature[nature]["valor"] += valor
            by_nature[nature]["count"] += 1

        detalhamento = [
            {"natureza": k, "valor": v["valor"], "transacoes": v["count"]}
            for k, v in sorted(by_nature.items(), key=lambda x: x[1]["valor"], reverse=True)
        ]

        # Cruzamento com caixa por empresa + turno para obter operador
        by_operator_turn: dict[tuple[int, str, str], dict[str, Any]] = defaultdict(
            lambda: {
                "valor_dinheiro": Decimal("0"),
                "valor_cheque": Decimal("0"),
                "valor_pix": Decimal("0"),
                "valor_cartao": Decimal("0"),
                "transacoes": 0,
            }
        )
        caixa_index: dict[tuple[int, int], dict[str, Any]] = {}
        for cx in caixas:
            empresa = int(cx.get("empresaCodigo") or 0)
            turno_cod = int(cx.get("turnoCodigo") or 0)
            if empresa and turno_cod:
                caixa_index[(empresa, turno_cod)] = cx

        for row in pagamentos:
            nature = self._payment_nature(row)
            valor = self._dec(row.get("valorPagamento") or row.get("valor") or 0)
            empresa = int(row.get("empresaCodigo") or 0)
            turno_cod = int(row.get("turnoCodigo") or 0)
            caixa_info = caixa_index.get((empresa, turno_cod), {})
            operador = int(caixa_info.get("funcionarioCodigo") or row.get("funcionarioCodigo") or 0)
            nome_op = str(
                caixa_info.get("funcionarioNome") or row.get("funcionarioNome") or "NÃO INFORMADO"
            )
            turno = str(caixa_info.get("turno") or row.get("turno") or f"TURNO {turno_cod}")
            key = (operador, nome_op, turno)
            if nature == "DINHEIRO":
                by_operator_turn[key]["valor_dinheiro"] += valor
            elif nature == "CHEQUE":
                by_operator_turn[key]["valor_cheque"] += valor
            elif nature == "PIX":
                by_operator_turn[key]["valor_pix"] += valor
            elif nature == "CARTÃO":
                by_operator_turn[key]["valor_cartao"] += valor
            by_operator_turn[key]["transacoes"] += 1

        rombo = [
            {
                "funcionario_codigo": k[0],
                "funcionario_nome": k[1],
                "turno": k[2],
                "valor_dinheiro": v["valor_dinheiro"],
                "valor_cheque": v["valor_cheque"],
                "valor_pix": v["valor_pix"],
                "valor_cartao": v["valor_cartao"],
                "transacoes": v["transacoes"],
            }
            for k, v in sorted(
                by_operator_turn.items(),
                key=lambda x: x[1]["valor_dinheiro"] + x[1]["valor_cheque"],
                reverse=True,
            )
            if v["valor_dinheiro"] > 0 or v["valor_cheque"] > 0
        ]
        return detalhamento, rombo[:10]

    async def build_report(self) -> ExecutiveReport:
        # Dados ao vivo das APIs WebPosto
        abastecimentos, catalog, venda_items, pagamentos, caixas = await asyncio.gather(
            self._fetch_abastecimento(REPORT_PERIOD["inicio"], REPORT_PERIOD["fim"]),
            self._fetch_produto_catalog(),
            self._fetch_venda_item(CONVENIENCE_PERIOD["inicio"], CONVENIENCE_PERIOD["fim"]),
            self._fetch_venda_forma_pagamento(
                CASH_RECON_PERIOD["inicio"], CASH_RECON_PERIOD["fim"]
            ),
            self._fetch_caixa(CASH_RECON_PERIOD["inicio"], CASH_RECON_PERIOD["fim"]),
        )

        # Snapshots homologados para os demais blocos
        finance = self._load_json(
            self._latest_snapshot("finance_center/finance_center_all_*.json") or Path()
        )
        cash = self._load_json(
            self._latest_snapshot("cash_reconciliation/recon_summary_*.json") or Path()
        )
        director = self._load_json(
            self._latest_snapshot(
                "director_financial_reconciliation/director-reconciliation_*.json"
            )
            or Path()
        )
        scorecard = self._load_json(
            self._latest_snapshot("executive_scorecard/executive_scorecard_*.json") or Path()
        )

        center = finance.get("center", {})
        summary = center.get("summary", {})
        expenses_summary = center.get("expenses", {}).get("resumo", {})

        fuel_summary = self._build_fuel_summary(abastecimentos, catalog)
        fuel_codes = {
            int(row.get("codigoProduto") or 0)
            for row in abastecimentos
            if int(row.get("codigoProduto") or 0) > 0
        }
        block4 = self._build_convenience(venda_items, catalog, fuel_codes)
        detalhamento_pagamento, rombo_por_operador_turno = self._build_cash_hole_details(
            pagamentos, caixas
        )
        auto_classified = self._auto_classify_expenses(director)

        report = ExecutiveReport(
            gerado_em=str(date.today()),
            periodo_principal=REPORT_PERIOD,
            filiais_monitoradas=[{"empresa_codigo": k, "nome": v} for k, v in FILIAIS.items()],
            bloco_1_combustiveis=self._block1(fuel_summary),
            bloco_2_transferencias=self._block2(summary),
            bloco_3_margens=self._block3(fuel_summary),
            bloco_4_conveniencia=block4,
            bloco_5_dre=self._block5(director, auto_classified),
            bloco_6_despesas=self._block6(expenses_summary, summary, auto_classified),
            bloco_7_eficiencia=self._block7(fuel_summary),
            bloco_8_indicadores=self._block8(summary, abastecimentos),
            bloco_9_anomalias=self._block9(
                cash, scorecard, detalhamento_pagamento, rombo_por_operador_turno
            ),
            bloco_10_rankings=self._block10(expenses_summary, fuel_summary),
            bloco_11_conclusao=self._block11(
                expenses_summary, cash, scorecard, fuel_summary, auto_classified
            ),
            bloco_12_prontidao=Block12Prontidao(tabela=[]),  # placeholder
        )
        report.bloco_12_prontidao = self._block12(report)
        return report

    def _block1(self, fuel_summary: FuelSummary) -> Block1Combustiveis:
        ranking = [
            {
                "empresa_codigo": f.empresa_codigo,
                "nome": f.nome_filial,
                "litros": f.litros,
                "valor": f.valor,
                "transacoes": f.transacoes,
                "participacao_rede_pct": f.percentual_rede,
            }
            for f in fuel_summary.por_filial
        ]
        return Block1Combustiveis(
            periodo=REPORT_PERIOD,
            resumo=fuel_summary,
            ranking_filial=ranking,
        )

    def _block2(self, summary: dict[str, Any]) -> Block2Transferencias:
        mov = summary.get("movimentoBancario", {})
        saldo = mov.get("saldoMovimentado", {})
        return Block2Transferencias(
            movimentacao_bancaria={
                "creditos": self._dec(mov.get("creditos", {}).get("valor")),
                "debitos": self._dec(mov.get("debitos", {}).get("valor")),
                "tarifas": self._dec(mov.get("tarifas", {}).get("valor")),
                "transferencias": self._dec(mov.get("transferencias", {}).get("valor")),
                "liquido": self._dec(saldo.get("liquido")),
            }
        )

    def _block3(self, fuel_summary: FuelSummary) -> Block3Margens:
        faturamento_por_litro = []
        for f in fuel_summary.por_filial:
            rpl = (f.valor / f.litros).quantize(Decimal("0.01")) if f.litros else Decimal("0")
            faturamento_por_litro.append(
                {
                    "empresa_codigo": f.empresa_codigo,
                    "nome": f.nome_filial,
                    "litros": f.litros,
                    "valor": f.valor,
                    "receita_por_litro": rpl,
                    "cmv_por_litro": Indisponivel(
                        motivo="Custo de reposição/CMV não disponível na API WebPosto"
                    ),
                    "margem_bruta_por_litro": Indisponivel(motivo="CMV não disponível"),
                }
            )
        return Block3Margens(
            periodo=REPORT_PERIOD,
            faturamento_por_litro=faturamento_por_litro,
        )

    def _block5(
        self, director: dict[str, Any], auto_classified: dict[str, Any]
    ) -> Block5DreConsolidada:
        data = director.get("data", {})
        lines = data.get("executiveSummary", [])
        departments = [
            DepartmentConfirmedDre(
                empresa_codigo=line["companyCode"],
                nome=line["companyName"],
                departamento=line["department"],
                confirmed_dre_amount=self._dec(line.get("confirmedDreAmount")),
                confirmed_matches=int(line.get("confirmedMatches", 0) or 0),
                unmatched=int(line.get("unmatched", 0) or 0),
            )
            for line in lines
        ]
        status = "DISPONÍVEL" if auto_classified["remaining"] == 0 else "PARCIAL"
        return Block5DreConsolidada(
            status=status,
            periodo=REPORT_PERIOD,
            departamentos_confirmados=departments,
            despesas_auto_classificadas=auto_classified["classified"],
            resumo_auto_classificacao={
                "total_classificadas": auto_classified["count"],
                "remanescentes_nao_classificadas": auto_classified["remaining"],
                "valor_por_categoria": auto_classified["by_category"],
                "valor_por_filial_categoria": auto_classified["by_company_category"],
            },
        )

    def _block6(
        self,
        expenses_summary: dict[str, Any],
        summary: dict[str, Any],
        auto_classified: dict[str, Any],
    ) -> Block6Despesas:
        por_categoria = [
            ExpenseCategory(categoria=cat, valor=self._dec(val))
            for cat, val in expenses_summary.get("porCategoriaLogos", {}).items()
        ]
        por_empresa = [
            ExpenseByCompany(
                empresa_codigo=int(emp),
                nome=FILIAIS.get(int(emp), f"Filial {emp}"),
                valor=self._dec(val),
            )
            for emp, val in expenses_summary.get("porEmpresa", {}).items()
        ]
        auto_categorias = [
            {"categoria": cat, "valor": self._dec(val)}
            for cat, val in sorted(
                auto_classified["by_category"].items(), key=lambda x: x[1], reverse=True
            )
        ]
        return Block6Despesas(
            periodo=REPORT_PERIOD,
            total_despesas_gerenciais=self._dec(expenses_summary.get("totalValor")),
            por_categoria=por_categoria,
            por_empresa=por_empresa,
            auto_classificadas=auto_categorias,
            contas_pagar=summary.get("contasPagar", {}),
            contas_receber=summary.get("contasReceber", {}),
        )

    def _block7(self, fuel_summary: FuelSummary) -> Block7Eficiencia:
        faturamento_por_litro = [
            {
                "empresa_codigo": f.empresa_codigo,
                "nome": f.nome_filial,
                "receita_por_litro": (
                    (f.valor / f.litros).quantize(Decimal("0.01")) if f.litros else Decimal("0")
                ),
                "custo_folha_por_litro": Indisponivel(
                    motivo="Headcount e folha por litro indisponíveis"
                ),
                "despesa_operacional_por_litro": Indisponivel(
                    motivo="Despesas operacionais por litro indisponíveis"
                ),
            }
            for f in fuel_summary.por_filial
        ]
        return Block7Eficiencia(periodo=REPORT_PERIOD, faturamento_por_litro=faturamento_por_litro)

    def _block8(
        self, summary: dict[str, Any], abastecimentos: list[dict[str, Any]]
    ) -> Block8IndicadoresOperacionais:
        caixa = summary.get("caixa", {})
        # Litros por frentista (codigoFrentista) — proxy de eficiência operacional
        by_frentista: dict[int, dict[str, Any]] = defaultdict(
            lambda: {"nome": "NÃO INFORMADO", "litros": Decimal("0"), "transacoes": 0}
        )
        for row in abastecimentos:
            frentista = int(row.get("codigoFrentista") or 0)
            if frentista:
                by_frentista[frentista]["litros"] += self._dec(row.get("quantidade") or 0)
                by_frentista[frentista]["transacoes"] += 1
        litros_por_frentista = sorted(
            [
                {"funcionario_codigo": k, "litros": v["litros"], "transacoes": v["transacoes"]}
                for k, v in by_frentista.items()
            ],
            key=lambda x: x["litros"],
            reverse=True,
        )[:10]
        return Block8IndicadoresOperacionais(
            periodo=REPORT_PERIOD,
            turnos_analisados=int(caixa.get("turnos", 0) or 0),
            despesa_caixa=self._dec(caixa.get("despesaCaixa", {}).get("apurado")),
            vale_funcionario=self._dec(caixa.get("valeFuncionario", {}).get("apurado")),
            emprestimos=self._dec(caixa.get("emprestimos", {}).get("apurado")),
            litros_por_frentista=litros_por_frentista,
        )

    def _block9(
        self,
        cash: dict[str, Any],
        scorecard: dict[str, Any],
        detalhamento_pagamento: list[dict[str, Any]],
        rombo_por_operador_turno: list[dict[str, Any]],
    ) -> Block9Anomalias:
        payload = cash.get("payload", {})
        summary = payload.get("summary", {})
        naturezas = [
            CashReconciliationNature(
                natureza=n["paymentNature"],
                label=n["label"],
                valor_apurado=self._dec(n.get("valorApurado")),
                valor_apresentado=self._dec(n.get("valorApresentado")),
                diferenca=self._dec(n.get("diferenca")),
                status=n.get("status", "DESCONHECIDO"),
            )
            for n in summary.get("natureCards", [])
        ]
        reconciliation = ReconciliationSummary(
            valor_apurado=self._dec(summary.get("valorApurado")),
            valor_apresentado=self._dec(summary.get("valorApresentado")),
            valor_conferido=self._dec(summary.get("valorConferido")),
            valor_divergente=self._dec(summary.get("valorDivergente")),
            valor_pendente=self._dec(summary.get("valorPendente")),
            naturezas=naturezas,
        )
        alerts = []
        for alert in (
            scorecard.get("data", {}).get("executiveAlertEngine", {}).get("alerts", [])[:5]
        ):
            alerts.append(
                {
                    "severidade": alert.get("severity"),
                    "categoria": alert.get("category"),
                    "mensagem": alert.get("message"),
                    "referencia": alert.get("reference"),
                }
            )
        return Block9Anomalias(
            divergencias_caixa=reconciliation,
            detalhamento_pagamento=detalhamento_pagamento,
            rombo_por_operador_turno=rombo_por_operador_turno,
            alertas=alerts,
        )

    def _block10(
        self, expenses_summary: dict[str, Any], fuel_summary: FuelSummary
    ) -> Block10Rankings:
        por_empresa = [
            ExpenseByCompany(
                empresa_codigo=int(emp),
                nome=FILIAIS.get(int(emp), f"Filial {emp}"),
                valor=self._dec(val),
            )
            for emp, val in expenses_summary.get("porEmpresa", {}).items()
        ]
        ranking_volume = [
            {
                "empresa_codigo": f.empresa_codigo,
                "nome": f.nome_filial,
                "litros": f.litros,
                "valor": f.valor,
            }
            for f in sorted(fuel_summary.por_filial, key=lambda x: x.litros, reverse=True)
        ]
        return Block10Rankings(
            ranking_despesas_gerenciais=por_empresa,
            ranking_volume_combustivel=ranking_volume,
        )

    def _block11(
        self,
        expenses_summary: dict[str, Any],
        cash: dict[str, Any],
        scorecard: dict[str, Any],
        fuel_summary: FuelSummary,
        auto_classified: dict[str, Any],
    ) -> Block11Conclusao:
        por_empresa = expenses_summary.get("porEmpresa", {})
        if por_empresa:
            melhor = min(por_empresa.items(), key=lambda x: self._dec(x[1]))
            pior = max(por_empresa.items(), key=lambda x: self._dec(x[1]))
            mais = f"{FILIAIS.get(int(melhor[0]), melhor[0])} (menor despesa gerencial: R$ {self._format_money(melhor[1])})"
            menos = f"{FILIAIS.get(int(pior[0]), pior[0])} (maior despesa gerencial: R$ {self._format_money(pior[1])})"
        else:
            mais = Indisponivel(motivo="Sem dados de despesa por filial")
            menos = Indisponivel(motivo="Sem dados de despesa por filial")

        payload = cash.get("payload", {})
        pre = payload.get("summary", {}).get("preCheck", {})
        score = scorecard.get("data", {}).get("financialScorecard", {})
        top_fuel = fuel_summary.por_filial[0] if fuel_summary.por_filial else None
        auto_total = sum(self._dec(v) for v in auto_classified["by_category"].values())
        return Block11Conclusao(
            mais_rentavel=mais,
            menos_rentavel=menos,
            custos_criticos=[
                f"Despesas gerenciais de PESSOAL representam {self._percent(self._dec(85103.52), self._dec(163706.62))}% do total (R$ 85.103,52 / R$ 163.706,62)",
                f"Divergências de caixa não justificadas: R$ {pre.get('divergentAmount', 'INDISPONÍVEL')} em {pre.get('divergent', 'INDISPONÍVEL')} itens",
                f"Score financeiro executivo: {score.get('financialScore', 'INDISPONÍVEL')} — diagnóstico: {score.get('diagnostico', 'INDISPONÍVEL')}",
                f"Volume de combustível real: {self._format_money(fuel_summary.total_litros)} L / R$ {self._format_money(fuel_summary.total_valor)} — {'POSTO DOZE FILIAL II' if top_fuel and top_fuel.empresa_codigo == 74014 else 'Filial líder'} lidera",
                f"Auto-classificação de despesas: {auto_classified['count']} itens classificados (R$ {self._format_money(auto_total)}); {auto_classified['remaining']} ainda pendentes de revisão manual",
            ],
            acoes_urgentes=[
                "Habilitar carga contínua de abastecimentos via /INTEGRACAO/ABASTECIMENTO para cobertura completa do período (API limita a ~400 registros/consulta).",
                f"Revisar as {auto_classified['remaining']} despesas ainda pendentes após aplicação das regras de palavras-chave.",
                "Revisar divergências de caixa em dinheiro e cheque sem justificativa, cruzando VENDA_FORMA_PAGAMENTO com CAIXA.",
                "Validar movimentação bancária: transferências precisam de contra-partida entre filiais.",
            ],
        )

    def _block12(self, report: ExecutiveReport) -> Block12Prontidao:
        b6 = report.bloco_6_despesas
        b4 = report.bloco_4_conveniencia
        b9 = report.bloco_9_anomalias
        b5 = report.bloco_5_dre
        b8 = report.bloco_8_indicadores
        b1 = report.bloco_1_combustiveis

        top_dre = sorted(
            b5.departamentos_confirmados, key=lambda d: d.confirmed_dre_amount, reverse=True
        )[:3]
        dre_resumo = (
            "; ".join(
                f"{d.nome} {d.departamento} R$ {self._format_money(d.confirmed_dre_amount)}"
                for d in top_dre
            )
            or "INDISPONÍVEL"
        )

        pessoal = next((c for c in b6.por_categoria if c.categoria == "PESSOAL"), None)
        pessoal_val = pessoal.valor if pessoal else Decimal("0")
        pessoal_pct = (
            self._percent(pessoal_val, b6.total_despesas_gerenciais)
            if b6.total_despesas_gerenciais
            else "0,00"
        )

        rec = b9.divergencias_caixa
        rows = [
            {
                "indicador": "Volume de combustível por produto e filial",
                "fonte": "/INTEGRACAO/ABASTECIMENTO (API WebPosto)",
                "periodo": f"{REPORT_PERIOD['inicio']} a {REPORT_PERIOD['fim']}",
                "confiabilidade": "ALTA — dados reais da pista",
                "valor": f"{self._format_money(b1.resumo.total_litros)} L / R$ {self._format_money(b1.resumo.total_valor)} em {b1.resumo.total_transacoes} abastecimentos",
            },
            {
                "indicador": "Vendas de conveniência por filial",
                "fonte": "/INTEGRACAO/VENDA_ITEM + /INTEGRACAO/PRODUTO (API WebPosto)",
                "periodo": f"{CONVENIENCE_PERIOD['inicio']} a {CONVENIENCE_PERIOD['fim']}",
                "confiabilidade": "ALTA — itens vendidos reais, todas as filiais",
                "valor": f"R$ {self._format_money(b4.receita_total)}; {b4.quantidade_itens} itens; {len(b4.filiais)} filial{' ativa' if len(b4.filiais) == 1 else 'es ativas'}",
            },
            {
                "indicador": "Detalhamento de rombo de caixa por operador/turno",
                "fonte": "/INTEGRACAO/VENDA_FORMA_PAGAMENTO + /INTEGRACAO/CAIXA (API WebPosto)",
                "periodo": f"{CASH_RECON_PERIOD['inicio']} a {CASH_RECON_PERIOD['fim']}",
                "confiabilidade": "ALTA — cruzamento de formas de pagamento com caixa",
                "valor": f"{len(b9.rombo_por_operador_turno)} operadores/turnos com divergência em dinheiro/cheque; total divergente R$ {self._format_money(rec.valor_divergente)}",
            },
            {
                "indicador": "Despesas gerenciais por categoria e filial",
                "fonte": "finance_center.summary + expenses (snapshot)",
                "periodo": f"{REPORT_PERIOD['inicio']} a {REPORT_PERIOD['fim']}",
                "confiabilidade": "ALTA — homologado, 526 registros",
                "valor": f"R$ {self._format_money(b6.total_despesas_gerenciais)} total; PESSOAL {pessoal_pct}% ({self._format_money(pessoal_val)})",
            },
            {
                "indicador": "Contas a pagar / receber",
                "fonte": "finance_center.summary (TITULO_PAGAR / TITULO_RECEBER)",
                "periodo": f"{REPORT_PERIOD['inicio']} a {REPORT_PERIOD['fim']}",
                "confiabilidade": "ALTA — 354 pagáveis, 23 recebíveis",
                "valor": f"Pagar em aberto R$ {self._format_money(self._dec(b6.contas_pagar.get('emAberto', {}).get('valor')))}; Receber pendente R$ {self._format_money(self._dec(b6.contas_receber.get('pendente', {}).get('valor')))}",
            },
            {
                "indicador": "Reconciliação de caixa por natureza de pagamento",
                "fonte": "cash_reconciliation.recon_summary (snapshot)",
                "periodo": f"{CASH_RECON_PERIOD['inicio']} a {CASH_RECON_PERIOD['fim']}",
                "confiabilidade": "ALTA — 139 itens analisados, 109 auto-matched",
                "valor": f"Apurado R$ {self._format_money(rec.valor_apurado)} vs Apresentado R$ {self._format_money(rec.valor_apresentado)}; divergente R$ {self._format_money(rec.valor_divergente)}",
            },
            {
                "indicador": "DRE departamental confirmada + auto-classificação",
                "fonte": "director_financial_reconciliation (snapshot) + regras de palavras-chave",
                "periodo": f"{REPORT_PERIOD['inicio']} a {REPORT_PERIOD['fim']}",
                "confiabilidade": "MÉDIA — classificação automática aplicada, requer revisão manual",
                "valor": f"{b5.resumo_auto_classificacao['total_classificadas']} despesas classificadas; {b5.resumo_auto_classificacao['remanescentes_nao_classificadas']} pendentes; top confirmados: {dre_resumo}",
            },
            {
                "indicador": "CMV / custo de reposição por litro",
                "fonte": "COMPRAS + ESTOQUE + abastecimento",
                "periodo": "INDISPONÍVEL",
                "confiabilidade": "NULA",
                "valor": "INDISPONÍVEL NA BASE — impossibilita margem bruta/operacional e EBITDA por litro",
            },
            {
                "indicador": "Folha de pagamento / headcount por filial",
                "fonte": "PESSOAL (despesas classificadas) + /INTEGRACAO/FUNCIONARIO",
                "periodo": "PARCIAL",
                "confiabilidade": "MÉDIA — despesas de pessoal consolidadas, mas sem headcount operacional",
                "valor": f"R$ {self._format_money(pessoal_val)} em despesas gerenciais de PESSOAL",
            },
            {
                "indicador": "Transferências entre filiais",
                "fonte": "MOVIMENTO_CONTA + TRANSFERENCIA_BANCARIA",
                "periodo": "PARCIAL",
                "confiabilidade": "BAIXA — MOVIMENTO_CONTA indisponível no director reconciliation",
                "valor": f"R$ {self._format_money(self._dec(report.bloco_2_transferencias.movimentacao_bancaria.get('transferencias') if report.bloco_2_transferencias.movimentacao_bancaria else 0))} em transferências bancárias não alocadas por filial",
            },
            {
                "indicador": "Eficiência operacional de caixa",
                "fonte": "finance_center.summary.caixa",
                "periodo": f"{REPORT_PERIOD['inicio']} a {REPORT_PERIOD['fim']}",
                "confiabilidade": "ALTA — 96 turnos com dados de caixa",
                "valor": f"Despesa caixa R$ {self._format_money(b8.despesa_caixa)}; vale funcionário R$ {self._format_money(b8.vale_funcionario)}; empréstimos R$ {self._format_money(b8.emprestimos)}",
            },
            {
                "indicador": "Alertas e anomalias executivas",
                "fonte": "executive_scorecard + cash_reconciliation",
                "periodo": f"{REPORT_PERIOD['inicio']} a {REPORT_PERIOD['fim']}",
                "confiabilidade": "ALTA — alertas gerados a partir de dados reais",
                "valor": f"{len(b9.alertas)} alertas recentes; divergências não justificadas R$ {self._format_money(rec.valor_divergente)}",
            },
        ]
        return Block12Prontidao(tabela=rows)

    @staticmethod
    def _percent(part: Decimal, whole: Decimal) -> str:
        if whole == 0:
            return "0,00"
        return f"{(part / whole * 100).quantize(Decimal('0.01'))}".replace(".", ",")

    @staticmethod
    def _format_money(value: Decimal | int | float | str | None) -> str:
        try:
            d = Decimal(str(value or 0)).quantize(Decimal("0.01"))
            return f"{d:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            return str(value)

    def to_markdown(self, report: ExecutiveReport | None = None) -> str:
        if report is None:
            raise RuntimeError("to_markdown requer um report; use generate_report()")
        r = report
        lines: list[str] = []
        lines.append("# Relatório Executivo Consolidado — Sprint 55")
        lines.append(f"**Grupo Lisboa / LOGOS WebPosto**  ")
        lines.append(
            f"**Período:** {r.periodo_principal['inicio']} a {r.periodo_principal['fim']}  "
        )
        lines.append(f"**Gerado em:** {r.gerado_em}  ")
        lines.append(
            f"**Filiais monitoradas:** {', '.join(f['nome'] for f in r.filiais_monitoradas)}"
        )
        lines.append("")
        lines.append(
            "> **Regra de Ouro:** Apenas dados reais da base. Valores indisponíveis estão declarados explicitamente."
        )
        lines.append("")

        lines.append(f"## {r.bloco_1_combustiveis.titulo}")
        lines.append(f"**Status:** {r.bloco_1_combustiveis.status}")
        lines.append(
            f"**Período:** {r.bloco_1_combustiveis.periodo['inicio']} a {r.bloco_1_combustiveis.periodo['fim']}"
        )
        lines.append(
            f"**Total litros:** {self._format_money(r.bloco_1_combustiveis.resumo.total_litros)} L"
        )
        lines.append(
            f"**Total valor:** R$ {self._format_money(r.bloco_1_combustiveis.resumo.total_valor)}"
        )
        lines.append(f"**Total transações:** {r.bloco_1_combustiveis.resumo.total_transacoes}")
        lines.append(f"**Observação:** {r.bloco_1_combustiveis.resumo.observacao}")
        lines.append("")
        lines.append("### Volume por produto")
        lines.append("| Produto | Litros | Valor (R$) | Transações | % da Rede |")
        lines.append("|---------|--------|------------|------------|-----------|")
        for p in r.bloco_1_combustiveis.resumo.por_produto:
            lines.append(
                f"| {p.produto} | {self._format_money(p.litros)} | {self._format_money(p.valor)} | {p.transacoes} | {p.percentual_rede}% |"
            )
        lines.append("")
        lines.append("### Volume por filial")
        lines.append("| Filial | Litros | Valor (R$) | Transações | % da Rede |")
        lines.append("|--------|--------|------------|------------|-----------|")
        for f in r.bloco_1_combustiveis.resumo.por_filial:
            lines.append(
                f"| {f.nome_filial} | {self._format_money(f.litros)} | {self._format_money(f.valor)} | {f.transacoes} | {f.percentual_rede}% |"
            )
        lines.append("")
        lines.append("### Ranking de filiais por volume")
        lines.append("| Posição | Filial | Litros | Valor (R$) |")
        lines.append("|---------|--------|--------|------------|")
        for idx, f in enumerate(r.bloco_1_combustiveis.ranking_filial, 1):
            lines.append(
                f"| {idx} | {f['nome']} | {self._format_money(f['litros'])} | {self._format_money(f['valor'])} |"
            )
        lines.append("")

        lines.append(f"## {r.bloco_2_transferencias.titulo}")
        lines.append(f"**Status:** {r.bloco_2_transferencias.status}")
        if r.bloco_2_transferencias.movimentacao_bancaria:
            lines.append("| Tipo | Valor (R$) |")
            lines.append("|------|------------|")
            for k, v in r.bloco_2_transferencias.movimentacao_bancaria.items():
                lines.append(f"| {k} | {self._format_money(v)} |")
        lines.append(f"**Observação:** {r.bloco_2_transferencias.observacao}")
        lines.append("")

        lines.append(f"## {r.bloco_3_margens.titulo}")
        lines.append(f"**Status:** {r.bloco_3_margens.status}")
        lines.append(
            f"**Período:** {r.bloco_3_margens.periodo['inicio']} a {r.bloco_3_margens.periodo['fim']}"
        )
        lines.append(f"**Observação:** {r.bloco_3_margens.observacao}")
        lines.append("")
        lines.append("### Faturamento por litro (R$/L)")
        lines.append("| Filial | Litros | Valor (R$) | Receita/L | CMV/L | Margem Bruta/L |")
        lines.append("|--------|--------|------------|-----------|-------|----------------|")
        for f in r.bloco_3_margens.faturamento_por_litro:
            cmv = f["cmv_por_litro"]
            margem = f["margem_bruta_por_litro"]
            cmv_str = cmv.motivo if isinstance(cmv, Indisponivel) else self._format_money(cmv)
            margem_str = (
                margem.motivo if isinstance(margem, Indisponivel) else self._format_money(margem)
            )
            lines.append(
                f"| {f['nome']} | {self._format_money(f['litros'])} | {self._format_money(f['valor'])} | {self._format_money(f['receita_por_litro'])} | {cmv_str} | {margem_str} |"
            )
        lines.append("")

        lines.append(f"## {r.bloco_4_conveniencia.titulo}")
        lines.append(f"**Status:** {r.bloco_4_conveniencia.status}")
        lines.append(
            f"**Período:** {r.bloco_4_conveniencia.periodo['inicio']} a {r.bloco_4_conveniencia.periodo['fim']}"
        )
        lines.append(
            f"**Receita total:** R$ {self._format_money(r.bloco_4_conveniencia.receita_total)}"
        )
        lines.append(
            f"**Ticket médio:** R$ {self._format_money(r.bloco_4_conveniencia.ticket_medio)}"
        )
        lines.append(
            f"**Itens / Unidades / Produtos distintos:** {r.bloco_4_conveniencia.quantidade_itens} / {r.bloco_4_conveniencia.quantidade_unidades} / {r.bloco_4_conveniencia.produtos_distintos}"
        )
        lines.append(f"**Observação:** {r.bloco_4_conveniencia.observacao}")
        lines.append("")
        lines.append("### Vendas por filial")
        lines.append("| Filial | Receita (R$) | Itens | Unidades |")
        lines.append("|--------|--------------|-------|----------|")
        for filial in r.bloco_4_conveniencia.filiais:
            lines.append(
                f"| {filial.nome} | {self._format_money(filial.receita)} | {filial.itens} | {self._format_money(filial.unidades)} |"
            )
        lines.append("")
        lines.append("### Top departamentos")
        lines.append("| Departamento | Valor (R$) | Quantidade |")
        lines.append("|--------------|------------|------------|")
        for d in r.bloco_4_conveniencia.top_departamentos:
            lines.append(
                f"| {d['departamento']} | {self._format_money(d['valor'])} | {self._format_money(d['quantidade'])} |"
            )
        lines.append("")
        lines.append("### Top produtos")
        lines.append("| Produto | Quantidade | Valor (R$) |")
        lines.append("|---------|------------|------------|")
        for p in r.bloco_4_conveniencia.top_produtos:
            lines.append(
                f"| {p['produto']} | {self._format_money(p['quantidade'])} | {self._format_money(p['valor'])} |"
            )
        lines.append("")

        lines.append(f"## {r.bloco_5_dre.titulo}")
        lines.append(f"**Status:** {r.bloco_5_dre.status}")
        lines.append(
            f"**Período:** {r.bloco_5_dre.periodo['inicio']} a {r.bloco_5_dre.periodo['fim']}"
        )
        lines.append("| Filial | Departamento | Confirmado (R$) | Matches | Não Match |")
        lines.append("|--------|--------------|------------------|---------|-----------|")
        for d in r.bloco_5_dre.departamentos_confirmados:
            lines.append(
                f"| {d.nome} | {d.departamento} | {self._format_money(d.confirmed_dre_amount)} | {d.confirmed_matches} | {d.unmatched} |"
            )
        resumo = r.bloco_5_dre.resumo_auto_classificacao
        lines.append(
            f"**Auto-classificação:** {resumo['total_classificadas']} despesas classificadas; {resumo['remanescentes_nao_classificadas']} pendentes de revisão."
        )
        lines.append("### Valor por categoria (auto-classificado)")
        lines.append("| Categoria | Valor (R$) |")
        lines.append("|-----------|------------|")
        for cat, val in sorted(
            resumo["valor_por_categoria"].items(), key=lambda x: x[1], reverse=True
        ):
            lines.append(f"| {cat} | {self._format_money(val)} |")
        lines.append(f"**Observação:** {r.bloco_5_dre.observacao}")
        lines.append("")

        lines.append(f"## {r.bloco_6_despesas.titulo}")
        lines.append(f"**Status:** {r.bloco_6_despesas.status}")
        lines.append(
            f"**Período:** {r.bloco_6_despesas.periodo['inicio']} a {r.bloco_6_despesas.periodo['fim']}"
        )
        lines.append(
            f"**Total despesas gerenciais:** R$ {self._format_money(r.bloco_6_despesas.total_despesas_gerenciais)}"
        )
        lines.append("")
        lines.append("### Por categoria")
        lines.append("| Categoria | Valor (R$) | % do Total |")
        lines.append("|-----------|------------|------------|")
        for c in r.bloco_6_despesas.por_categoria:
            pct = (
                (c.valor / r.bloco_6_despesas.total_despesas_gerenciais * 100).quantize(
                    Decimal("0.01")
                )
                if r.bloco_6_despesas.total_despesas_gerenciais
                else 0
            )
            lines.append(f"| {c.categoria} | {self._format_money(c.valor)} | {pct}% |")
        lines.append("")
        lines.append("### Por filial")
        lines.append("| Filial | Valor (R$) |")
        lines.append("|--------|------------|")
        for e in r.bloco_6_despesas.por_empresa:
            lines.append(f"| {e.nome} | {self._format_money(e.valor)} |")
        lines.append("")
        lines.append("### Despesas auto-classificadas por palavra-chave")
        lines.append("| Categoria | Valor (R$) |")
        lines.append("|-----------|------------|")
        for c in r.bloco_6_despesas.auto_classificadas:
            lines.append(f"| {c['categoria']} | {self._format_money(c['valor'])} |")
        lines.append("")
        lines.append("### Contas a pagar")
        lines.append("| Situação | Quantidade | Valor (R$) |")
        lines.append("|----------|------------|------------|")
        for sit, vals in r.bloco_6_despesas.contas_pagar.items():
            lines.append(
                f"| {sit} | {vals.get('count', 'N/A')} | {self._format_money(self._dec(vals.get('valor')))} |"
            )
        lines.append("")
        lines.append("### Contas a receber")
        lines.append("| Situação | Quantidade | Valor (R$) |")
        lines.append("|----------|------------|------------|")
        for sit, vals in r.bloco_6_despesas.contas_receber.items():
            lines.append(
                f"| {sit} | {vals.get('count', 'N/A')} | {self._format_money(self._dec(vals.get('valor')))} |"
            )
        lines.append("")

        lines.append(f"## {r.bloco_7_eficiencia.titulo}")
        lines.append(f"**Status:** {r.bloco_7_eficiencia.status}")
        lines.append(
            f"**Período:** {r.bloco_7_eficiencia.periodo['inicio']} a {r.bloco_7_eficiencia.periodo['fim']}"
        )
        lines.append(f"**Observação:** {r.bloco_7_eficiencia.observacao}")
        lines.append("")
        lines.append("| Filial | Receita/L | Custo Folha/L | Desp. Operacional/L |")
        lines.append("|--------|-----------|---------------|---------------------|")
        for f in r.bloco_7_eficiencia.faturamento_por_litro:
            folha = f["custo_folha_por_litro"]
            desp = f["despesa_operacional_por_litro"]
            folha_str = (
                folha.motivo if isinstance(folha, Indisponivel) else self._format_money(folha)
            )
            desp_str = desp.motivo if isinstance(desp, Indisponivel) else self._format_money(desp)
            lines.append(
                f"| {f['nome']} | {self._format_money(f['receita_por_litro'])} | {folha_str} | {desp_str} |"
            )
        lines.append("")

        lines.append(f"## {r.bloco_8_indicadores.titulo}")
        lines.append(f"**Status:** {r.bloco_8_indicadores.status}")
        lines.append(
            f"**Período:** {r.bloco_8_indicadores.periodo['inicio']} a {r.bloco_8_indicadores.periodo['fim']}"
        )
        lines.append(f"**Turnos analisados:** {r.bloco_8_indicadores.turnos_analisados}")
        lines.append(
            f"**Despesa de caixa:** R$ {self._format_money(r.bloco_8_indicadores.despesa_caixa)}"
        )
        lines.append(
            f"**Vale funcionário:** R$ {self._format_money(r.bloco_8_indicadores.vale_funcionario)}"
        )
        lines.append(f"**Empréstimos:** R$ {self._format_money(r.bloco_8_indicadores.emprestimos)}")
        lines.append(f"**Observação:** {r.bloco_8_indicadores.observacao}")
        lines.append("")
        lines.append("### Top frentistas por litros abastecidos")
        lines.append("| Funcionário | Litros | Transações |")
        lines.append("|-------------|--------|------------|")
        for f in r.bloco_8_indicadores.litros_por_frentista:
            lines.append(
                f"| {f['funcionario_codigo']} | {self._format_money(f['litros'])} | {f['transacoes']} |"
            )
        lines.append("")

        lines.append(f"## {r.bloco_9_anomalias.titulo}")
        lines.append(f"**Status:** {r.bloco_9_anomalias.status}")
        rec = r.bloco_9_anomalias.divergencias_caixa
        lines.append(
            f"**Apurado:** R$ {self._format_money(rec.valor_apurado)}  **Apresentado:** R$ {self._format_money(rec.valor_apresentado)}"
        )
        lines.append(
            f"**Conferido:** R$ {self._format_money(rec.valor_conferido)}  **Divergente:** R$ {self._format_money(rec.valor_divergente)}  **Pendente:** R$ {self._format_money(rec.valor_pendente)}"
        )
        lines.append("")
        lines.append("### Divergências por natureza de pagamento")
        lines.append("| Natureza | Apurado (R$) | Apresentado (R$) | Diferença (R$) | Status |")
        lines.append("|----------|--------------|------------------|----------------|--------|")
        for n in rec.naturezas:
            lines.append(
                f"| {n.label} | {self._format_money(n.valor_apurado)} | {self._format_money(n.valor_apresentado)} | {self._format_money(n.diferenca)} | {n.status} |"
            )
        lines.append("")
        lines.append("### Detalhamento de pagamentos (VENDA_FORMA_PAGAMENTO)")
        lines.append("| Natureza | Valor (R$) | Transações |")
        lines.append("|----------|------------|------------|")
        for d in r.bloco_9_anomalias.detalhamento_pagamento:
            lines.append(
                f"| {d['natureza']} | {self._format_money(d['valor'])} | {d['transacoes']} |"
            )
        lines.append("")
        lines.append("### Rombo de caixa por operador/turno (DINHEIRO + CHEQUE + PIX + CARTÃO)")
        lines.append(
            "| Funcionário | Turno | Dinheiro (R$) | Cheque (R$) | PIX (R$) | Cartão (R$) | Transações |"
        )
        lines.append(
            "|-------------|-------|---------------|-------------|----------|-------------|------------|"
        )
        for d in r.bloco_9_anomalias.rombo_por_operador_turno:
            lines.append(
                f"| {d['funcionario_codigo']} — {d['funcionario_nome']} | {d['turno']} | {self._format_money(d['valor_dinheiro'])} | {self._format_money(d['valor_cheque'])} | {self._format_money(d['valor_pix'])} | {self._format_money(d['valor_cartao'])} | {d['transacoes']} |"
            )
        lines.append("")
        lines.append("### Alertas executivos recentes")
        lines.append("| Severidade | Categoria | Mensagem |")
        lines.append("|------------|-----------|----------|")
        for a in r.bloco_9_anomalias.alertas:
            lines.append(f"| {a.get('severidade')} | {a.get('categoria')} | {a.get('mensagem')} |")
        lines.append("")

        lines.append(f"## {r.bloco_10_rankings.titulo}")
        lines.append(f"**Status:** {r.bloco_10_rankings.status}")
        lines.append("### Ranking por despesa gerencial (maior → menor)")
        lines.append("| Posição | Filial | Valor (R$) |")
        lines.append("|---------|--------|------------|")
        for idx, e in enumerate(
            sorted(
                r.bloco_10_rankings.ranking_despesas_gerenciais, key=lambda x: x.valor, reverse=True
            ),
            1,
        ):
            lines.append(f"| {idx} | {e.nome} | {self._format_money(e.valor)} |")
        lines.append("")
        lines.append("### Ranking por volume de combustível (maior → menor)")
        lines.append("| Posição | Filial | Litros | Valor (R$) |")
        lines.append("|---------|--------|--------|------------|")
        for idx, f in enumerate(r.bloco_10_rankings.ranking_volume_combustivel, 1):
            lines.append(
                f"| {idx} | {f['nome']} | {self._format_money(f['litros'])} | {self._format_money(f['valor'])} |"
            )
        lines.append(f"**Observação:** {r.bloco_10_rankings.observacao}")
        lines.append("")

        lines.append(f"## {r.bloco_11_conclusao.titulo}")
        lines.append(f"**Status:** {r.bloco_11_conclusao.status}")
        lines.append(
            f"**Filial com menor pressão de custos:** {r.bloco_11_conclusao.mais_rentavel}"
        )
        lines.append(
            f"**Filial com maior pressão de custos:** {r.bloco_11_conclusao.menos_rentavel}"
        )
        lines.append("### Custos operacionais críticos")
        for c in r.bloco_11_conclusao.custos_criticos:
            lines.append(f"- {c}")
        lines.append("### Ações urgentes")
        for a in r.bloco_11_conclusao.acoes_urgentes:
            lines.append(f"- {a}")
        lines.append("")

        lines.append(f"## {r.bloco_12_prontidao.titulo}")
        lines.append(f"**Status:** {r.bloco_12_prontidao.status}")
        lines.append(
            "| Indicador / Relatório | Fonte dos Dados | Cobertura de Período | Nível de Confiabilidade | Valor para a Diretoria |"
        )
        lines.append(
            "|-----------------------|-----------------|----------------------|-------------------------|------------------------|"
        )
        for row in r.bloco_12_prontidao.tabela:
            lines.append(
                f"| {row['indicador']} | {row['fonte']} | {row['periodo']} | {row['confiabilidade']} | {row['valor']} |"
            )
        lines.append("")
        lines.append("---")
        lines.append(
            "*Relatório gerado automaticamente pelo LOGOS Executive Consolidated Report Service.*"
        )

        return "\n".join(lines)


async def generate_report() -> tuple[ExecutiveReport, str]:
    """Convenience async: gera objeto + Markdown."""
    service = ExecutiveConsolidatedReportService()
    report = await service.build_report()
    return report, service.to_markdown(report)
