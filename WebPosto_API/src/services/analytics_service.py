from __future__ import annotations

import asyncio
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from src.domain.entities.filial_master import filial_name_lookup
from src.models.response_model import WebPostoResponse
from src.services.network_financial_overview_service import FinancialOverviewFilters, NetworkFinancialOverviewService
from src.services.money_normalizer import normalize_webposto_money


FILIAIS_BASE: dict[int, str] = filial_name_lookup()


def _to_dec(value: Any) -> Decimal:
    return normalize_webposto_money(value)


@dataclass
class KpiResult:
    faturamento: Decimal
    despesas_totais: Decimal
    resultado_operacional: Decimal
    margem_pct: Decimal
    ticket_medio: Decimal
    qtd_vendas: int
    qtd_clientes: int
    estoque_total: Decimal
    periodo_inicial: str
    periodo_final: str
    filtros: dict[str, Any]
    empresas_codigos: list[int]
    origem_sistema: str = "webpostos"

    def to_dict(self) -> dict[str, Any]:
        periodo = f"{self.periodo_inicial}..{self.periodo_final}"
        filtro_empresa = self.filtros.get("empresaCodigo")
        filtro_centro = self.filtros.get("centroCusto")
        filtro_tipo = self.filtros.get("tipoDespesa")
        escopo_rede = ",".join(str(c) for c in self.empresas_codigos) if self.empresas_codigos else "rede_completa"
        return {
            "faturamento": str(self.faturamento),
            "despesasTotais": str(self.despesas_totais),
            "despesas": str(self.despesas_totais),
            "resultadoOperacional": str(self.resultado_operacional),
            "resultado": str(self.resultado_operacional),
            "margemPct": str(self.margem_pct),
            "margem": str(self.margem_pct),
            "ticketMedio": str(self.ticket_medio),
            "qtdVendas": self.qtd_vendas,
            "qtdClientes": self.qtd_clientes,
            "estoqueTotal": str(self.estoque_total),
            "periodoInicial": self.periodo_inicial,
            "periodoFinal": self.periodo_final,
            "filtros": self.filtros,
            "empresasCodigos": self.empresas_codigos,
            "origemSistema": self.origem_sistema,
            "lineage": {
                "faturamento": f"endpoint=/INTEGRACAO/VENDA_ITEM_REDE|campo=totalVenda|filtro=empresaCodigo:{filtro_empresa},centroCusto:{filtro_centro},tipoDespesa:{filtro_tipo}|periodo={periodo}|rede={escopo_rede}",
                "despesasTotais": f"endpoint=/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE|campo=valor|filtro=empresaCodigo:{filtro_empresa},centroCusto:{filtro_centro},tipoDespesa:{filtro_tipo}|periodo={periodo}|rede={escopo_rede}",
                "resultadoOperacional": f"endpoint=calculo_backend|campo=faturamento-despesas|filtro=empresaCodigo:{filtro_empresa},centroCusto:{filtro_centro},tipoDespesa:{filtro_tipo}|periodo={periodo}|rede={escopo_rede}",
                "margemPct": f"endpoint=calculo_backend|campo=resultado/faturamento*100|filtro=empresaCodigo:{filtro_empresa},centroCusto:{filtro_centro},tipoDespesa:{filtro_tipo}|periodo={periodo}|rede={escopo_rede}",
                "ticketMedio": f"endpoint=calculo_backend|campo=faturamento/qtdVendas|filtro=empresaCodigo:{filtro_empresa},centroCusto:{filtro_centro},tipoDespesa:{filtro_tipo}|periodo={periodo}|rede={escopo_rede}",
                "estoque": f"endpoint=/INTEGRACAO/PRODUTO_ESTOQUE|campo=quantidade|filtro=empresaCodigo:{filtro_empresa},centroCusto:{filtro_centro}|periodo={periodo}|rede={escopo_rede}",
            },
        }


@dataclass
class DreResult:
    receitas: Decimal
    custos_produto: Decimal
    outras_despesas: Decimal
    resultado_operacional: Decimal
    margem_pct: Decimal
    validacao_ok: bool
    divergencia: Decimal
    periodo_inicial: str
    periodo_final: str
    agrupamento: list[dict[str, Any]]
    filtros: dict[str, Any]
    empresas_codigos: list[int]

    def to_dict(self) -> dict[str, Any]:
        periodo = f"{self.periodo_inicial}..{self.periodo_final}"
        filtro_empresa = self.filtros.get("empresaCodigo")
        filtro_centro = self.filtros.get("centroCusto")
        escopo_rede = ",".join(str(c) for c in self.empresas_codigos) if self.empresas_codigos else "rede_completa"
        return {
            "receitas": str(self.receitas),
            "custosProduto": str(self.custos_produto),
            "custos": str(self.custos_produto),
            "outrasDespesas": str(self.outras_despesas),
            "despesas": str(self.outras_despesas),
            "resultadoOperacional": str(self.resultado_operacional),
            "resultado": str(self.resultado_operacional),
            "margemPct": str(self.margem_pct),
            "margemPercentual": str(self.margem_pct),
            "validacaoOk": self.validacao_ok,
            "divergencia": str(self.divergencia),
            "periodoInicial": self.periodo_inicial,
            "periodoFinal": self.periodo_final,
            "agrupamento": self.agrupamento,
            "formula": "receitas - custosProduto - outrasDespesas = resultadoOperacional",
            "lineage": {
                "receitas": f"endpoint=/INTEGRACAO/VENDA_ITEM_REDE|campo=totalVenda|filtro=empresaCodigo:{filtro_empresa},centroCusto:{filtro_centro}|periodo={periodo}|rede={escopo_rede}",
                "custosProduto": f"endpoint=/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE|campo=valor(classificado_custo)|filtro=empresaCodigo:{filtro_empresa},centroCusto:{filtro_centro}|periodo={periodo}|rede={escopo_rede}",
                "outrasDespesas": f"endpoint=/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE|campo=valor(classificado_outra)|filtro=empresaCodigo:{filtro_empresa},centroCusto:{filtro_centro}|periodo={periodo}|rede={escopo_rede}",
                "resultadoOperacional": f"endpoint=calculo_backend|campo=receitas-custosProduto-outrasDespesas|filtro=empresaCodigo:{filtro_empresa},centroCusto:{filtro_centro}|periodo={periodo}|rede={escopo_rede}",
                "margemPct": f"endpoint=calculo_backend|campo=resultado/receitas*100|filtro=empresaCodigo:{filtro_empresa},centroCusto:{filtro_centro}|periodo={periodo}|rede={escopo_rede}",
            },
        }


class AnalyticsService:
    def __init__(self, overview_service: NetworkFinancialOverviewService) -> None:
        self.overview = overview_service

    @staticmethod
    def _rows_from_response(resp: WebPostoResponse, key: str | None = None) -> list[dict[str, Any]]:
        if not resp.success:
            return []
        data = resp.data
        if isinstance(data, dict):
            if key and key in data:
                rows = data[key]
            else:
                rows = (
                    data.get("data")
                    or data.get("resultados")
                    or data.get("venda_item")
                    or []
                )
        elif isinstance(data, list):
            rows = data
        else:
            rows = []
        return [r for r in rows if isinstance(r, dict)]

    @staticmethod
    def _consolidado_total(resp: WebPostoResponse, key: str) -> Decimal:
        """Extrai total pre-calculado do campo consolidado da resposta."""
        if not resp.success or not isinstance(resp.data, dict):
            return Decimal("0")
        consolidado = resp.data.get("consolidado") or {}
        raw = consolidado.get(key)
        if raw is None:
            return Decimal("0")
        return _to_dec(raw)

    @staticmethod
    def _classify_expense(row: dict[str, Any]) -> str:
        tipo = str(row.get("tipoDespesa") or "").lower()
        plano = str(row.get("planoConta") or "").lower()
        if any(kw in tipo or kw in plano for kw in ("custo", "fornecedor", "mercadoria", "combustivel")):
            return "custo_produto"
        return "outra_despesa"

    async def get_kpis(self, filters: FinancialOverviewFilters) -> WebPostoResponse:
        exp_resp, sales_resp, stock_resp = await asyncio.gather(
            self.overview.get_financial_expenses(filters, page=1, limit=500),
            self.overview.get_sales(filters, page=1, limit=500),
            self.overview.get_stock(filters, page=1, limit=500),
        )

        expenses = self._rows_from_response(exp_resp)
        sales = self._rows_from_response(sales_resp)
        stock = self._rows_from_response(stock_resp)

        # Faturamento: prioriza consolidado.total_vendas (pre-calculado pelo servico de vendas)
        # pois os rows paginados podem nao ter todos os registros
        faturamento = self._consolidado_total(sales_resp, "total_vendas")
        if faturamento == Decimal("0"):
            # Fallback: somar totalVenda dos rows individuais
            faturamento = sum(_to_dec(r.get("totalVenda") or r.get("valor")) for r in sales)

        despesas_totais = sum(_to_dec(r.get("valor")) for r in expenses)
        resultado = faturamento - despesas_totais
        margem = (resultado / faturamento * 100) if faturamento else Decimal("0")

        # qtdVendas: do consolidado quando disponivel
        consolidado = (sales_resp.data or {}).get("consolidado") or {} if sales_resp.success else {}
        qtd_vendas_consolidado = consolidado.get("qtd_vendas")
        qtd_vendas = int(qtd_vendas_consolidado) if qtd_vendas_consolidado is not None else len(sales)

        clientes: set[str] = set()
        for r in sales:
            c = str(r.get("cliente") or "").strip()
            if c and c != "consumidor final":
                clientes.add(c)
        ticket = (faturamento / qtd_vendas) if qtd_vendas else Decimal("0")
        estoque_total = sum(_to_dec(r.get("quantidade")) for r in stock)

        codigos_set: set[int] = set()
        for rows in (expenses, sales, stock):
            for r in rows:
                c = r.get("empresaCodigo")
                if c is not None:
                    try:
                        codigos_set.add(int(c))
                    except Exception:
                        pass

        resultado_kpi = KpiResult(
            faturamento=faturamento,
            despesas_totais=despesas_totais,
            resultado_operacional=resultado,
            margem_pct=margem.quantize(Decimal("0.01")),
            ticket_medio=ticket,
            qtd_vendas=qtd_vendas,
            qtd_clientes=len(clientes),
            estoque_total=estoque_total,
            periodo_inicial=filters.data_inicial,
            periodo_final=filters.data_final,
            filtros={
                "empresaCodigo": filters.empresa_codigo,
                "centroCusto": filters.centro_custo,
                "tipoDespesa": filters.tipo_despesa,
            },
            empresas_codigos=sorted(codigos_set),
        )
        return WebPostoResponse.ok(resultado_kpi.to_dict())

    async def get_dre(self, filters: FinancialOverviewFilters) -> WebPostoResponse:
        exp_resp, sales_resp = await asyncio.gather(
            self.overview.get_financial_expenses(filters, page=1, limit=500),
            self.overview.get_sales(filters, page=1, limit=500),
        )

        expenses = self._rows_from_response(exp_resp)
        sales = self._rows_from_response(sales_resp)

        codigos_set: set[int] = set()
        for rows in (expenses, sales):
            for r in rows:
                c = r.get("empresaCodigo")
                if c is not None:
                    try:
                        codigos_set.add(int(c))
                    except Exception:
                        pass

        receitas = sum(_to_dec(r.get("totalVenda") or r.get("valor")) for r in sales)

        custos: Decimal = Decimal("0")
        outras: Decimal = Decimal("0")
        agrupamento: dict[str, Any] = {}

        for r in expenses:
            valor = _to_dec(r.get("valor"))
            kind = self._classify_expense(r)
            if kind == "custo_produto":
                custos += valor
            else:
                outras += valor

            plano = str(r.get("planoConta") or "Sem plano de conta")
            agrupamento.setdefault(plano, Decimal("0"))
            agrupamento[plano] += valor

        resultado_op = receitas - custos - outras
        divergencia = abs(resultado_op - (receitas - custos - outras))
        margem = (resultado_op / receitas * 100) if receitas else Decimal("0")

        agrup_list = [
            {"planoConta": k, "valor": str(v)}
            for k, v in sorted(agrupamento.items(), key=lambda x: x[1], reverse=True)
        ]

        dre = DreResult(
            receitas=receitas,
            custos_produto=custos,
            outras_despesas=outras,
            resultado_operacional=resultado_op,
            margem_pct=margem.quantize(Decimal("0.01")),
            validacao_ok=divergencia < Decimal("0.01"),
            divergencia=divergencia,
            periodo_inicial=filters.data_inicial,
            periodo_final=filters.data_final,
            agrupamento=agrup_list,
            filtros={
                "empresaCodigo": filters.empresa_codigo,
                "centroCusto": filters.centro_custo,
            },
            empresas_codigos=sorted(codigos_set),
        )
        return WebPostoResponse.ok(dre.to_dict())

    async def get_fuel_summary(self, filters: FinancialOverviewFilters, combustivel_filtro: str | None = None, filial_filtro: str | None = None) -> WebPostoResponse:
        from src.services.network_financial_overview_service import is_active_fuel_product

        empresas, error = await self.overview._resolve_empresas(filters)
        if error is not None:
            return error

        summary_acc = {}
        total_litros_geral = Decimal("0")

        # Filtros de empresa adicionais para suportar multisseleção via vírgula no string de filtros
        filiais_permitidas = set()
        if filters.empresa_codigo is not None:
            filiais_permitidas.add(filters.empresa_codigo)
        elif filial_filtro:
            # Se for passada uma string contendo códigos de filiais separados por vírgula
            try:
                for cod in filial_filtro.split(","):
                    if cod.strip().isdigit():
                        filiais_permitidas.add(int(cod.strip()))
            except ValueError:
                pass

        for empresa in empresas:
            empresa_codigo = empresa.get("empresaCodigo")
            if empresa_codigo is None:
                continue

            # Se houver filtro específico de empresa_codigo ativo
            if filters.empresa_codigo is not None and empresa_codigo != filters.empresa_codigo:
                continue
                
            if filiais_permitidas and empresa_codigo not in filiais_permitidas:
                continue

            # Se houver filtro por nome de filial
            filial_nome = self.overview._normalize_empresa_name(empresa)
            if filial_filtro and not filiais_permitidas and filial_filtro.casefold() not in filial_nome.casefold():
                continue

            produto_resp = await self.overview.client.call_endpoint(
                "produto",
                params={
                    "dataInicial": filters.data_inicial,
                    "dataFinal": filters.data_final,
                    "empresaCodigo": empresa_codigo,
                },
            )
            produtos = []
            if produto_resp.success:
                produtos = self.overview._rows(produto_resp.data)

            produtos_by_codigo = {}
            for p in produtos:
                p_cod = p.get("produtoCodigo") or p.get("codigo")
                if p_cod is not None:
                    produtos_by_codigo[p_cod] = p

            vendas_resp = await self.overview._fetch_vendas_produtos(filters, empresa_codigo)
            if not vendas_resp.success:
                continue

            item_rows = self.overview._rows((vendas_resp.data or {}).get("venda_item"))

            for item in item_rows:
                p_cod = item.get("produtoCodigo")
                if p_cod is None:
                    continue

                prod_ref = produtos_by_codigo.get(p_cod)
                is_fuel = False
                nome_combustivel = ""

                if prod_ref:
                    if is_active_fuel_product(prod_ref):
                        is_fuel = True
                        nome_combustivel = prod_ref.get("descricao") or prod_ref.get("produto") or ""
                else:
                    descr = item.get("descricao") or item.get("produto") or item.get("descricaoProduto") or ""
                    dummy = {"descricao": descr, "ativo": True}
                    if is_active_fuel_product(dummy):
                        is_fuel = True
                        nome_combustivel = descr

                if not is_fuel or not nome_combustivel:
                    continue

                nome_combustivel = str(nome_combustivel).strip()
                
                # Se for passada uma string contendo combustíveis separados por vírgula
                combustiveis_filtrados = set()
                if combustivel_filtro:
                    combustiveis_filtrados = {c.strip().casefold() for c in combustivel_filtro.split(",") if c.strip()}

                if combustiveis_filtrados:
                    if not any(cf in nome_combustivel.casefold() for cf in combustiveis_filtrados):
                        continue
                elif combustivel_filtro and combustivel_filtro.casefold() not in nome_combustivel.casefold():
                    continue

                quant = self.overview._to_decimal(item.get("quantidade") or item.get("litros") or Decimal("0"))
                total_venda_item = self.overview._to_decimal(item.get("totalVenda") or item.get("valorTotal") or item.get("valor") or Decimal("0"))

                if quant is None:
                    quant = Decimal("0")
                if total_venda_item is None:
                    total_venda_item = Decimal("0")

                total_litros_geral += quant

                key_acc = (empresa_codigo, nome_combustivel)
                if key_acc not in summary_acc:
                    summary_acc[key_acc] = {
                        "litros": Decimal("0"),
                        "valor": Decimal("0"),
                    }

                summary_acc[key_acc]["litros"] += quant
                summary_acc[key_acc]["valor"] += total_venda_item

        results = []
        for (emp_cod, fuel_name), data in summary_acc.items():
            litros = data["litros"]
            valor = data["valor"]

            tk_medio = (valor / litros) if litros > Decimal("0") else Decimal("0")
            participacao = (litros / total_litros_geral * 100) if total_litros_geral > Decimal("0") else Decimal("0")

            results.append({
                "empresaCodigo": emp_cod,
                "combustivel": fuel_name,
                "litros": float(litros),
                "valor": float(valor),
                "precoMedio": round(float(tk_medio), 2),
                "participacao": round(float(participacao), 1),
            })

        results.sort(key=lambda x: x["litros"], reverse=True)

        return WebPostoResponse.ok(results)
