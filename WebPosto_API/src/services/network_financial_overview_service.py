from __future__ import annotations

import asyncio

from dataclasses import dataclass
from decimal import Decimal
import json
import logging
from typing import Any

from src.domain.entities.filial_master import filial_name_lookup, list_filiais_master
from src.core.management_scope import LICENSED_COMPANIES, LICENSED_COMPANY_CODES
from src.gateway.webposto_client import WebPostoClient
from src.infrastructure.config.settings import settings
from src.models.error_model import WebPostoError
from src.models.response_model import WebPostoResponse
from src.services.money_normalizer import (
    normalize_webposto_account_value,
    normalize_webposto_expense_value,
    normalize_webposto_sale_value,
)


LOGGER = logging.getLogger(__name__)

FILIAIS_FALLBACK: dict[int, str] = filial_name_lookup()


def is_active_fuel_product(row: dict[str, Any]) -> bool:
    if not isinstance(row, dict):
        return False

    # Check if active / status / situacao
    def _is_active(v: Any) -> bool:
        if v is None:
            return True
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        if s in ("false", "0", "inativo", "inativos", "n", "nao", "não", "inactive", "i"):
            return False
        return True

    active = True
    for key in ("ativo", "status", "situacao", "situação", "produtoAtivo"):
        if key in row and row[key] is not None:
            if not _is_active(row[key]):
                active = False
                break
    if not active:
        return False

    import unicodedata
    def _normalize(val: Any) -> str:
        if val is None:
            return ""
        s = str(val).strip().casefold()
        s = "".join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
        return s

    fuel_keywords = {"combustivel", "combustiveis", "fuel"}
    for key in (
        "tipoProduto", "tipoProdutoCodigo", "grupoProduto", "grupoProdutoCodigo",
        "produtoTipo", "produtoGrupo", "descricaoTipo", "descricaoGrupo", "tipoCombustivel"
    ):
        val = _normalize(row.get(key))
        if val in fuel_keywords or any(kw in val for kw in fuel_keywords):
            return True

    if row.get("combustivel") is True:
        return True

    tp = str(row.get("tipoProduto") or row.get("produtoTipo") or "").strip().upper()
    if tp == "C":
        return True

    desc = _normalize(row.get("nome") or row.get("descricao") or row.get("produto") or "")
    for kw in fuel_keywords:
        if kw in desc:
            return True
    for kw in {"gasolina", "etanol", "diesel", "gnv", "comb."}:
        if kw in desc:
            return True

    return False


@dataclass(frozen=True)
class FinancialOverviewFilters:
    data_inicial: str
    data_final: str
    empresa_codigo: int | None = None
    empresa_codigos: tuple[int, ...] | None = None
    tipo_despesa: str | None = None
    plano_conta_codigo: int | None = None
    plano_conta: str | None = None
    centro_custo: str | None = None
    valor_min: Decimal | None = None
    valor_max: Decimal | None = None
    status: str | None = None
    origem: str | None = None
    fornecedor: str | None = None
    vencimento_inicial: str | None = None
    vencimento_final: str | None = None
    categoria_logos: str | None = None
    texto: str | None = None
    expense_natures: tuple[str, ...] | None = None
    expense_management_groups: tuple[str, ...] | None = None
    expense_management_classes: tuple[str, ...] | None = None
    dre_impact: str | None = None
    cashflow_impact: str | None = None


class NetworkFinancialOverviewService:
    def __init__(self, client: WebPostoClient) -> None:
        self.client = client

    _MONEY_DEBUG_DESCRIPTIONS = {
        "ref ao abastecimento do caminhao",
        "sr. moises / com pedro",
        "salario josinaldo",
    }

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

    @staticmethod
    def _to_decimal(value: Any) -> Decimal | None:
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None

    @staticmethod
    def _norm_text(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip().casefold()

    @staticmethod
    def _contains(value: Any, query: str | None) -> bool:
        if not query:
            return True
        return query.casefold() in str(value or "").casefold()

    @staticmethod
    def _eq_text(value: Any, expected: str | None) -> bool:
        if not expected:
            return True
        return str(value or "").strip().casefold() == expected.casefold()

    @staticmethod
    def _expense_origem(row: dict[str, Any]) -> str:
        if row.get("caixaCodigo") is not None:
            return "caixa"
        if row.get("tituloPagarCodigo") is not None:
            return "titulos_a_pagar"
        return "financeiro"

    @staticmethod
    def _expense_status(row: dict[str, Any]) -> str:
        situacao = str(row.get("situacao") or "").casefold()
        if "pago" in situacao or row.get("dataPagamento"):
            return "pago"
        if "aberto" in situacao or "pend" in situacao:
            return "pendente"
        return situacao or "desconhecido"

    @classmethod
    def _should_debug_money(cls, description: str) -> bool:
        return description.strip().casefold() in cls._MONEY_DEBUG_DESCRIPTIONS

    @staticmethod
    def _dedupe_rows(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
        seen: set[tuple[Any, ...]] = set()
        deduped: list[dict[str, Any]] = []
        for row in rows:
            row_key = tuple(row.get(k) for k in keys)
            if row_key in seen:
                continue
            seen.add(row_key)
            deduped.append(row)
        return deduped

    _EXPENSE_DEDUPE_KEYS = (
        "empresaCodigo",
        "data",
        "valor",
        "planoConta",
        "tipoDespesa",
        "centroCusto",
        "origem",
        "status",
    )

    def _expense_matches_empresa(self, row: dict[str, Any], filters: FinancialOverviewFilters) -> bool:
        code = row.get("empresaCodigo")
        if code is None:
            return False
        try:
            code_int = int(code)
        except (TypeError, ValueError):
            return False
        if filters.empresa_codigo is not None:
            return code_int == filters.empresa_codigo
        if filters.empresa_codigos:
            return code_int in filters.empresa_codigos
        return True

    def _normalize_expense(self, row: dict[str, Any]) -> dict[str, Any] | None:
        data = row.get("data") or row.get("dataMovimento")
        valor_raw = row.get("valor") or row.get("valorTotal") or row.get("valorDespesa")
        valor_convertido_atual = self._to_decimal(valor_raw)
        valor = normalize_webposto_expense_value(valor_raw)
        if not (data and valor is not None):
            return None

        plano_codigo = row.get("planoContaCodigo") or row.get("planoContaGerencialCodigo")
        plano_desc = (
            row.get("planoConta")
            or row.get("descricaoPlanoConta")
            or row.get("planoContaGerencialDescricao")
            or row.get("descricaoDocumento")
        )
        tipo = row.get("tipoDespesa") or row.get("tipo") or row.get("tipoLancamento") or ""
        centro = row.get("centroCusto") or row.get("descricaoCentroCusto") or row.get("subCentro") or ""

        if settings.webposto_money_debug and self._should_debug_money(str(plano_desc or "")):
            LOGGER.info(
                {
                    "event": "webposto_money_debug",
                    "descricao": str(plano_desc or ""),
                    "valor_bruto": valor_raw,
                    "tipo_bruto": type(valor_raw).__name__,
                    "valor_convertido_atual": str(valor_convertido_atual) if valor_convertido_atual is not None else None,
                    "valor_normalizado_novo": str(valor),
                    "endpoint_origem": "/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
                }
            )

        return {
            "empresaCodigo": row.get("empresaCodigo"),
            "data": str(data),
            "valor": str(valor),
            "planoContaCodigo": plano_codigo,
            "planoConta": str(plano_desc or ""),
            "tipoDespesa": str(tipo),
            "centroCusto": str(centro),
            "status": self._expense_status(row),
            "origem": self._expense_origem(row),
            "raw": row,
            "synthetic": False,
        }

    def _expense_matches(self, row: dict[str, Any], filters: FinancialOverviewFilters) -> bool:
        if not self._expense_matches_empresa(row, filters):
            return False

        valor = self._to_decimal(row.get("valor"))
        if filters.valor_min is not None and (valor is None or valor < filters.valor_min):
            return False
        if filters.valor_max is not None and (valor is None or valor > filters.valor_max):
            return False

        if filters.tipo_despesa and not self._contains(row.get("tipoDespesa"), filters.tipo_despesa):
            return False

        if filters.plano_conta_codigo is not None and row.get("planoContaCodigo") != filters.plano_conta_codigo:
            return False

        if filters.plano_conta and not self._contains(row.get("planoConta"), filters.plano_conta):
            return False

        if filters.centro_custo and not self._contains(row.get("centroCusto"), filters.centro_custo):
            return False

        if filters.status and not self._eq_text(row.get("status"), filters.status):
            return False

        if filters.origem and not self._expense_origem_matches(row, filters.origem):
            return False

        if filters.texto:
            blob = " ".join(
                str(row.get(key) or "")
                for key in ("descricao", "planoConta", "centroCusto", "tipoDespesa")
            )
            if not self._contains(blob, filters.texto):
                return False

        if filters.categoria_logos:
            cat = str(row.get("categoria") or row.get("categoriaLogos") or "")
            if cat.casefold() != filters.categoria_logos.casefold():
                return False

        return True

    def _normalize_titulo_pagar(self, row: dict[str, Any]) -> dict[str, Any] | None:
        valor = normalize_webposto_account_value(row.get("valor") or row.get("valorPago") or row.get("valorTotal"))
        vencimento = row.get("vencimento")
        if valor is None:
            return None
        valor_pago = normalize_webposto_account_value(row.get("valorPago"))
        return {
            "empresaCodigo": row.get("empresaCodigo"),
            "vencimento": str(vencimento) if vencimento is not None else None,
            "fornecedor": row.get("fornecedor") or row.get("fornecedorNome") or row.get("razao") or "",
            "situacao": str(row.get("situacao") or ""),
            "valor": str(valor),
            "valorPago": str(valor_pago),
            "raw": row,
            "synthetic": False,
        }

    def _titulo_matches(self, row: dict[str, Any], filters: FinancialOverviewFilters) -> bool:
        if filters.empresa_codigo is not None and row.get("empresaCodigo") != filters.empresa_codigo:
            return False

        if filters.status and not self._contains(row.get("situacao"), filters.status):
            return False

        if filters.fornecedor and not self._contains(row.get("fornecedor"), filters.fornecedor):
            return False

        vencimento = str(row.get("vencimento") or "")
        if filters.vencimento_inicial and vencimento and vencimento < filters.vencimento_inicial:
            return False
        if filters.vencimento_final and vencimento and vencimento > filters.vencimento_final:
            return False

        return True

    @staticmethod
    def _sum_values(rows: list[dict[str, Any]], key: str) -> Decimal:
        total = Decimal("0")
        for row in rows:
            try:
                total += Decimal(str(row.get(key) or 0))
            except Exception:
                continue
        return total

    async def _fetch_empresas(self) -> WebPostoResponse:
        return await self.client.call_endpoint("empresas", params={})

    async def _fetch_despesas_rede(self, filters: FinancialOverviewFilters) -> WebPostoResponse:
        """Uma chamada à rede — API ignora empresaCodigo."""
        params: dict[str, Any] = {
            "dataInicial": filters.data_inicial,
            "dataFinal": filters.data_final,
        }
        return await self.client.call_endpoint("despesas_financeiro_rede", params=params)

    async def _fetch_despesas(self, filters: FinancialOverviewFilters, empresa_codigo: int | None = None) -> WebPostoResponse:
        del empresa_codigo  # mantido por compatibilidade; endpoint retorna rede inteira
        return await self._fetch_despesas_rede(filters)

    async def _load_filtered_expenses(
        self,
        filters: FinancialOverviewFilters,
    ) -> tuple[list[dict[str, Any]], WebPostoResponse | None]:
        despesas_resp = await self._fetch_despesas_rede(filters)
        if not despesas_resp.success:
            return [], despesas_resp

        normalized: list[dict[str, Any]] = []
        for row in self._rows(despesas_resp.data):
            item = self._normalize_expense(row)
            if item and self._expense_matches(item, filters):
                normalized.append(item)

        return self._dedupe_rows(normalized, keys=self._EXPENSE_DEDUPE_KEYS), None

    _SCREEN_EXPENSE_DEDUPE_KEYS = (
        "origem",
        "empresaCodigo",
        "data",
        "caixaCodigo",
        "turnoCodigo",
        "pdvCodigo",
        "funcionarioCodigo",
    )

    _CLOSURE_RAW_DEDUPE_KEYS = (
        "empresaCodigo",
        "caixaCodigo",
        "turnoCodigo",
        "pdvCodigo",
    )

    @classmethod
    def _closure_key(cls, row: dict[str, Any], data: str | None = None) -> tuple[Any, ...]:
        dt = data or cls._shift_expense_date(row)
        return (
            row.get("empresaCodigo") or row.get("ap_empresaCodigo"),
            str(dt or "")[:10],
            row.get("caixaCodigo") or row.get("ap_caixaCodigo"),
            row.get("turnoCodigo") or row.get("ap_turnoCodigo"),
            row.get("pdvCodigo") or row.get("ap_pdvCodigo"),
        )

    @classmethod
    def _dedupe_closure_source_rows(cls, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[tuple[Any, ...]] = set()
        deduped: list[dict[str, Any]] = []
        for row in rows:
            key = cls._closure_key(row)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(row)
        return deduped

    @staticmethod
    def _shift_expense_date(row: dict[str, Any]) -> str:
        return str(
            row.get("dataMovimento")
            or row.get("fechamento")
            or row.get("abertura")
            or row.get("data")
            or row.get("dataLancamento")
            or ""
        )[:10]

    @staticmethod
    def _expense_description(row: dict[str, Any]) -> str:
        return str(
            row.get("descricaoDocumento")
            or row.get("descricao")
            or row.get("planoContaGerencialDescricao")
            or row.get("planoConta")
            or row.get("descricaoPlanoConta")
            or ""
        ).strip()

    def _expense_categoria(self, descricao: str, plano: str, centro: str) -> str:
        from src.services.logos_expense_classifier_v3 import classify_with_all_versions

        classified = classify_with_all_versions(
            descricao,
            plano,
            "",
            centro,
            descricao,
        )
        return str(classified.get("categoriaLogos") or "OUTROS")

    def _normalize_financeiro_screen_expense(self, row: dict[str, Any]) -> dict[str, Any] | None:
        item = self._normalize_expense(row)
        if not item:
            return None
        descricao = self._expense_description(row) or str(item.get("planoConta") or "")
        item["origem"] = "financeiro"
        item["descricao"] = descricao
        item["caixaCodigo"] = row.get("caixaCodigo")
        item["pdvCodigo"] = row.get("pdvCodigo")
        item["funcionarioCodigo"] = row.get("funcionarioCodigo")
        item["matchFinanceiro"] = False
        item["fonte"] = "DESPESAS_FINANCEIRO_REDE"
        item["categoria"] = self._expense_categoria(descricao, str(item.get("planoConta") or ""), str(item.get("centroCusto") or ""))
        return item

    @classmethod
    def _expense_origem_matches(cls, row: dict[str, Any], origem_filter: str) -> bool:
        wanted = str(origem_filter or "").strip().casefold()
        if not wanted:
            return True
        row_origem = str(row.get("origem") or "").strip().casefold()
        if row_origem == wanted:
            return True
        if wanted == "pdv" and row_origem == "caixa":
            apurado = cls._to_decimal(row.get("despesaApurado") or row.get("valor"))
            return apurado is not None and apurado > 0
        if wanted == "caixa" and row_origem == "caixa":
            apresentado = cls._to_decimal(row.get("despesaApresentado") or row.get("valor"))
            return apresentado is not None and apresentado > 0
        return False

    def _normalize_closure_screen_expense(self, merged: dict[str, Any]) -> dict[str, Any] | None:
        apurado = normalize_webposto_expense_value(
            merged.get("ap_despesaApurado") or merged.get("despesaApurado")
        )
        apresentado = normalize_webposto_expense_value(
            merged.get("ap_despesaApresentado") or merged.get("despesaApresentado")
        )
        if (apurado is None or apurado == 0) and (apresentado is None or apresentado == 0):
            return None

        data = self._shift_expense_date(merged)
        if not data:
            return None

        diff_raw = merged.get("ap_despesaDiferenca") if merged.get("ap_despesaDiferenca") is not None else merged.get("despesaDiferenca")
        if diff_raw is not None:
            diferenca = normalize_webposto_expense_value(diff_raw) or Decimal("0")
        elif apurado is not None and apresentado is not None:
            diferenca = apresentado - apurado
        else:
            diferenca = Decimal("0")

        valor = apurado if apurado not in (None, Decimal("0")) else apresentado
        if valor is None or valor == 0:
            return None

        turno = merged.get("turno") or merged.get("turnoCodigo") or merged.get("ap_turno") or ""
        pdv = merged.get("pdvCodigo") or merged.get("ap_pdvCodigo") or "?"
        descricao = self._expense_description(merged)
        if not descricao:
            descricao = f"Despesa turno {turno} · PDV {pdv}".strip(" ·")

        centro = str(
            merged.get("centroCusto")
            or merged.get("descricaoCentroCusto")
            or merged.get("subCentro")
            or merged.get("ap_centroCusto")
            or ""
        )
        return {
            "empresaCodigo": merged.get("empresaCodigo") or merged.get("ap_empresaCodigo"),
            "data": data,
            "valor": str(valor),
            "descricao": descricao,
            "planoConta": descricao,
            "planoContaCodigo": merged.get("planoContaCodigo") or merged.get("planoContaGerencialCodigo"),
            "tipoDespesa": "operacional",
            "centroCusto": centro,
            "status": "apurado",
            "origem": "caixa",
            "caixaCodigo": merged.get("caixaCodigo") or merged.get("ap_caixaCodigo"),
            "pdvCodigo": merged.get("pdvCodigo") or merged.get("ap_pdvCodigo"),
            "funcionarioCodigo": merged.get("funcionarioCodigo") or merged.get("ap_funcionarioCodigo"),
            "turnoCodigo": merged.get("turnoCodigo") or merged.get("ap_turnoCodigo"),
            "turno": turno,
            "despesaApurado": str(apurado or Decimal("0")),
            "despesaApresentado": str(apresentado or Decimal("0")),
            "despesaDiferenca": str(diferenca.quantize(Decimal("0.01"))),
            "matchFinanceiro": False,
            "fonte": "CAIXA_APRESENTADO+CAIXA_REDE",
            "categoria": "OPERACIONAL",
            "raw": merged,
            "synthetic": False,
        }

    def _normalize_operational_screen_expense(
        self,
        row: dict[str, Any],
        *,
        origem: str,
        fonte: str,
        valor_fields: tuple[str, ...],
    ) -> dict[str, Any] | None:
        valor_raw = None
        for field in valor_fields:
            if row.get(field) not in (None, "", 0, "0", "0.0", "0.00"):
                valor_raw = row.get(field)
                break
        valor = normalize_webposto_expense_value(valor_raw)
        if valor is None or valor == 0:
            return None

        data = self._shift_expense_date(row)
        if not data:
            return None

        turno = row.get("turno") or row.get("turnoCodigo") or row.get("ap_turno") or ""
        pdv = row.get("pdvCodigo") or row.get("ap_pdvCodigo") or "?"
        descricao = self._expense_description(row)
        if not descricao:
            descricao = f"Despesa {origem} · turno {turno} · PDV {pdv}".strip(" ·")

        centro = str(
            row.get("centroCusto")
            or row.get("descricaoCentroCusto")
            or row.get("subCentro")
            or row.get("ap_centroCusto")
            or ""
        )
        return {
            "empresaCodigo": row.get("empresaCodigo") or row.get("ap_empresaCodigo"),
            "data": data,
            "valor": str(valor),
            "descricao": descricao,
            "planoConta": descricao,
            "planoContaCodigo": row.get("planoContaCodigo") or row.get("planoContaGerencialCodigo"),
            "tipoDespesa": "operacional",
            "centroCusto": centro,
            "status": "apurado",
            "origem": origem,
            "caixaCodigo": row.get("caixaCodigo") or row.get("ap_caixaCodigo"),
            "pdvCodigo": row.get("pdvCodigo") or row.get("ap_pdvCodigo"),
            "funcionarioCodigo": row.get("funcionarioCodigo") or row.get("ap_funcionarioCodigo"),
            "matchFinanceiro": False,
            "fonte": fonte,
            "categoria": "OPERACIONAL",
            "raw": row,
            "synthetic": False,
        }

    async def _fetch_paginated_endpoint(
        self,
        endpoint_key: str,
        filters: FinancialOverviewFilters,
        max_pages: int = 15,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "dataInicial": filters.data_inicial,
            "dataFinal": filters.data_final,
        }
        all_rows: list[dict[str, Any]] = []
        seen_pages: set[str] = set()
        for page in range(max_pages):
            page_params = {**params, "pagina": page + 1} if page else params
            resp = await self.client.call_endpoint(endpoint_key, params=page_params)
            if not resp.success:
                break
            chunk = self._rows(resp.data)
            if not chunk:
                break
            signature = json.dumps(chunk, sort_keys=True, ensure_ascii=False, default=str)
            if signature in seen_pages:
                LOGGER.warning(
                    "WebPosto ignorou paginacao em %s; coleta interrompida na pagina repetida %s",
                    endpoint_key,
                    page + 1,
                )
                break
            seen_pages.add(signature)
            all_rows.extend(chunk)
            if isinstance(resp.data, dict) and resp.data.get("ultimaPagina", True):
                break
        return all_rows

    @staticmethod
    def _financeiro_match_key(row: dict[str, Any]) -> tuple[Any, str, Decimal] | None:
        empresa = row.get("empresaCodigo")
        data = str(row.get("data") or "")[:10]
        valor = NetworkFinancialOverviewService._to_decimal(row.get("valor"))
        if empresa is None or not data or valor is None:
            return None
        return (empresa, data, valor.quantize(Decimal("0.01")))

    def _apply_financeiro_matches(self, rows: list[dict[str, Any]]) -> None:
        financeiro_index: dict[tuple[Any, str, Decimal], list[dict[str, Any]]] = {}
        for row in rows:
            if row.get("origem") != "financeiro":
                continue
            key = self._financeiro_match_key(row)
            if key is not None:
                financeiro_index.setdefault(key, []).append(row)

        used_financeiro: set[int] = set()
        for row in rows:
            if row.get("origem") == "financeiro":
                continue
            key = self._financeiro_match_key(row)
            if key is None:
                continue
            for candidate in financeiro_index.get(key, []):
                cid = id(candidate)
                if cid in used_financeiro:
                    continue
                row["matchFinanceiro"] = True
                used_financeiro.add(cid)
                if not self._expense_description(row.get("raw") or {}):
                    row["descricao"] = candidate.get("descricao") or candidate.get("planoConta") or row.get("descricao")
                    row["planoConta"] = row["descricao"]
                    row["categoria"] = candidate.get("categoria") or row.get("categoria")
                break

        for row in rows:
            if row.get("origem") == "financeiro":
                row["matchFinanceiro"] = id(row) in used_financeiro

    async def _load_screen_expenses(
        self,
        filters: FinancialOverviewFilters,
    ) -> tuple[list[dict[str, Any]], WebPostoResponse | None]:
        import asyncio

        despesas_resp = await self._fetch_despesas_rede(filters)
        if not despesas_resp.success:
            return [], despesas_resp

        caixa_rede, caixa, apresentado, apresentado_rede = await asyncio.gather(
            self._fetch_paginated_endpoint("caixa_rede", filters),
            self._fetch_paginated_endpoint("caixa", filters),
            self._fetch_paginated_endpoint("caixa_apresentado", filters),
            self._fetch_paginated_endpoint("caixa_apresentado_rede", filters),
        )

        normalized: list[dict[str, Any]] = []
        for row in self._rows(despesas_resp.data):
            item = self._normalize_financeiro_screen_expense(row)
            if item and self._expense_matches(item, filters):
                normalized.append(item)

        ap_map = {
            (row.get("empresaCodigo"), row.get("caixaCodigo")): row
            for row in (apresentado + apresentado_rede)
        }
        caixa_rows = caixa_rede or caixa
        if caixa_rede and caixa:
            seen_keys = {(r.get("empresaCodigo"), r.get("caixaCodigo")) for r in caixa_rede}
            caixa_rows = caixa_rede + [
                r for r in caixa if (r.get("empresaCodigo"), r.get("caixaCodigo")) not in seen_keys
            ]
        caixa_rows = self._dedupe_closure_source_rows(caixa_rows)

        for row in caixa_rows:
            ap = ap_map.get((row.get("empresaCodigo"), row.get("caixaCodigo")), {})
            merged = {**row, **{f"ap_{k}": v for k, v in ap.items()}}

            closure_item = self._normalize_closure_screen_expense(merged)
            if closure_item and self._expense_matches(closure_item, filters):
                normalized.append(closure_item)

        self._apply_financeiro_matches(normalized)
        financeiro = self._dedupe_rows(
            [row for row in normalized if row.get("origem") == "financeiro"],
            keys=self._EXPENSE_DEDUPE_KEYS,
        )
        operational = self._dedupe_rows(
            [row for row in normalized if row.get("origem") != "financeiro"],
            keys=self._SCREEN_EXPENSE_DEDUPE_KEYS,
        )
        return financeiro + operational, None

    async def _fetch_titulo_pagar(self, filters: FinancialOverviewFilters, empresa_codigo: int | None) -> WebPostoResponse:
        params: dict[str, Any] = {
            "dataInicial": filters.data_inicial,
            "dataFinal": filters.data_final,
        }
        if empresa_codigo is not None:
            params["empresaCodigo"] = empresa_codigo
        primary = await self.client.call_endpoint("financeiro", params=params)
        if primary.success:
            return primary

        fallback = await self.client.call_endpoint("conta", params=params)
        if fallback.success:
            return fallback

        return primary

    async def _fetch_vendas_produtos(self, filters: FinancialOverviewFilters, empresa_codigo: int | None) -> WebPostoResponse:
        params: dict[str, Any] = {
            "dataInicial": filters.data_inicial,
            "dataFinal": filters.data_final,
        }
        if empresa_codigo is not None:
            params["empresaCodigo"] = empresa_codigo

        from src.services.webposto_cursor_paginator import WebPostoCursorPaginator

        paginator = WebPostoCursorPaginator(self.client)

        async def _collect_with_cursor(primary_key: str, fallback_key: str) -> WebPostoResponse:
            return await paginator.collect(primary_key, fallback_key, params)

        venda = await paginator.collect(
            "venda", "venda", params, cursor_field="vendaCodigo"
        )
        if not venda.success:
            return venda

        venda_rows = self._rows(venda.data)
        # Caminho executivo: o total da venda é suficiente para faturamento e
        # evita baixar milhares de itens/formas de pagamento sem necessidade.
        has_complete_totals = bool(venda_rows) and all(
            row.get("totalVenda") not in (None, "")
            or row.get("valorTotal") not in (None, "")
            for row in venda_rows
        )
        if has_complete_totals:
            return WebPostoResponse.ok({
                "venda": venda_rows,
                "venda_item": [],
                "venda_forma_pagamento": [],
                "detailCoverage": "SALES_TOTALS_ONLY",
                "synthetic": False,
            })

        venda_item, venda_fp = await asyncio.gather(
            _collect_with_cursor("venda_item_rede", "venda_item"),
            _collect_with_cursor("venda_forma_pagamento_rede", "venda_forma_pagamento"),
        )
        if not venda_item.success:
            return venda_item
        if not venda_fp.success:
            return venda_fp

        item_rows = self._rows(venda_item.data)
        fp_rows = self._rows(venda_fp.data)

        vendas_codigos = {r.get("vendaCodigo") for r in venda_rows if r.get("vendaCodigo") is not None}
        filtered_items = [
            r for r in item_rows if r.get("vendaCodigo") in vendas_codigos and self._to_decimal(r.get("totalVenda")) is not None
        ]
        filtered_fp = [r for r in fp_rows if r.get("vendaCodigo") in vendas_codigos]

        return WebPostoResponse.ok(
            {
                "venda": venda_rows,
                "venda_item": filtered_items,
                "venda_forma_pagamento": filtered_fp,
                "synthetic": False,
            }
        )

    async def _fetch_vendas_combustivel(self) -> WebPostoResponse:
        return await self.client.call_endpoint("analise_vendas_combustivel", params={})

    @staticmethod
    def _normalize_empresa_name(row: dict[str, Any]) -> str:
        name = row.get("fantasia") or row.get("razao") or row.get("nome") or ""
        return str(name).strip()

    @staticmethod
    def _empresa_lookup(empresas: list[dict[str, Any]]) -> dict[int, str]:
        lookup: dict[int, str] = {}
        for empresa in empresas:
            codigo = empresa.get("empresaCodigo")
            if codigo is None:
                continue
            try:
                lookup[int(codigo)] = NetworkFinancialOverviewService._normalize_empresa_name(empresa)
            except Exception:
                continue
        return lookup

    @staticmethod
    def _empresa_name_by_codigo(codigo: Any, lookup: dict[int, str]) -> str:
        try:
            codigo_int = int(codigo)
            return lookup.get(codigo_int, FILIAIS_FALLBACK.get(codigo_int, ""))
        except Exception:
            return ""

    @staticmethod
    def _extract_combustivel_total_for_posto(payload: object, posto_nome: str) -> Decimal:
        if not isinstance(payload, dict):
            return Decimal("0")

        alvo = posto_nome.casefold()
        total = Decimal("0")
        for value in payload.values():
            if not isinstance(value, list):
                continue
            for bloco in value:
                if not isinstance(bloco, dict):
                    continue
                posto = str(bloco.get("posto") or "").casefold()
                if posto != alvo:
                    continue
                for produto in bloco.get("produtos") or []:
                    if not isinstance(produto, dict):
                        continue
                    amount = produto.get("amount")
                    if isinstance(amount, dict):
                        amount = amount.get("amount")
                    try:
                        total += Decimal(str(amount or 0))
                    except Exception:
                        continue
        return total

    async def _resolve_empresas(self, filters: FinancialOverviewFilters) -> tuple[list[dict[str, Any]], WebPostoResponse | None]:
        if filters.empresa_codigo in LICENSED_COMPANY_CODES:
            company = next(
                item for item in LICENSED_COMPANIES
                if item.empresa_codigo == filters.empresa_codigo
            )
            return [{
                "empresaCodigo": company.empresa_codigo,
                "codigo": company.empresa_codigo,
                "fantasia": company.nome,
                "nome": company.nome,
                "scopeSource": "LICENSED_COMPANY_REGISTRY",
            }], None

        companies_resp = await self.get_companies()
        if not companies_resp.success:
            return [], companies_resp

        empresas = (companies_resp.data or {}).get("data") or []
        if filters.empresa_codigos:
            targets = set(filters.empresa_codigos)
            empresas = [
                e for e in empresas
                if e.get("empresaCodigo") in targets or e.get("codigo") in targets
            ]
            if not empresas:
                return [], None
        elif filters.empresa_codigo is not None:
            target = filters.empresa_codigo
            empresas = [
                e for e in empresas
                if e.get("empresaCodigo") == target or e.get("codigo") == target
            ]
            if not empresas:
                return [], None

        if not empresas:
            return [], WebPostoResponse.fail(
                WebPostoError(
                    endpoint="/v1/financial/companies",
                    status=404,
                    type="NO_COMPANIES_FOUND",
                    message="Nenhuma empresa encontrada para os filtros informados",
                )
            )

        return empresas, None

    async def get_companies(self) -> WebPostoResponse:
        import re
        empresas_rows = []
        empresas_response = await self._fetch_empresas()
        if empresas_response.success:
            empresas_rows = self._rows(empresas_response.data)

        # Build maps of API companies for easy matching
        api_by_codigo = {}
        api_by_cnpj = {}
        for row in empresas_rows:
            cod = row.get("empresaCodigo") or row.get("codigo")
            if cod is not None:
                api_by_codigo[int(cod)] = row
            cnpj = "".join(re.findall(r"\d+", str(row.get("cnpj") or row.get("cnpjCpf") or row.get("documento") or "")))
            if cnpj:
                api_by_cnpj[cnpj] = row

        normalized = []
        for official in list_filiais_master():
            cod = official.empresa_codigo
            cnpj_clean = "".join(re.findall(r"\d+", str(official.cnpj)))
            status_operacional = "ATIVA" if official.status == "CONFIRMADA" else official.status
            status_detalhado = "Dados operacionais"
            possui_dados_operacionais = False

            if official.status == "INATIVA":
                status_operacional = "INATIVA"
                status_detalhado = "Inativa"
            elif official.status == "PENDENTE_IDENTIFICACAO":
                status_operacional = "PENDENTE_IDENTIFICACAO"
                status_detalhado = "Pendente identificacao"
            elif cod == 5256:
                status_detalhado = "Token insuficiente"
            elif cod in {5555, 11495}:
                status_detalhado = "Dados operacionais"
                possui_dados_operacionais = True
            elif cod is not None:
                status_detalhado = "Dados operacionais em rede"
                possui_dados_operacionais = True
            
            match_row = api_by_codigo.get(cod) or api_by_cnpj.get(cnpj_clean)
            if match_row:
                normalized.append(
                    {
                        "codWeb": official.cod_web,
                        "empresaCodigo": cod,
                        "codigoApi": match_row.get("empresaCodigo") or match_row.get("codigo"),
                        "nome": self._normalize_empresa_name(match_row) or official.nome_fantasia,
                        "nomeFantasia": self._normalize_empresa_name(match_row) or official.nome_fantasia,
                        "razaoSocial": str(match_row.get("razao") or match_row.get("razaoSocial") or official.razao_social),
                        "cnpj": str(match_row.get("cnpj") or match_row.get("cnpjCpf") or match_row.get("documento") or official.cnpj),
                        "status": official.status,
                        "statusOperacional": status_operacional,
                        "statusDetalhado": status_detalhado,
                        "status_detalhado": status_detalhado,
                        "origem": official.origem,
                        "dataEncerramento": official.data_encerramento,
                        "possuiDadosOperacionais": possui_dados_operacionais,
                        "apiEncontrada": True,
                        "raw": match_row,
                    }
                )
            else:
                normalized.append(
                    {
                        "codWeb": official.cod_web,
                        "empresaCodigo": cod,
                        "codigoApi": None,
                        "nome": official.nome_fantasia,
                        "nomeFantasia": official.nome_fantasia,
                        "razaoSocial": official.razao_social,
                        "cnpj": official.cnpj,
                        "status": official.status,
                        "statusOperacional": status_operacional,
                        "statusDetalhado": status_detalhado,
                        "status_detalhado": status_detalhado,
                        "origem": official.origem,
                        "dataEncerramento": official.data_encerramento,
                        "possuiDadosOperacionais": possui_dados_operacionais,
                        "apiEncontrada": False,
                        "raw": {
                            "empresaCodigo": cod,
                            "codigo": cod,
                            "razao": official.razao_social,
                            "fantasia": official.nome_fantasia,
                            "cnpj": official.cnpj,
                        },
                    }
                )

        return WebPostoResponse.ok(
            {
                "data": normalized,
                "total": len(normalized),
                "synthetic": False,
            }
        )

    @staticmethod
    def _paginate(rows: list[dict[str, Any]], page: int, limit: int) -> tuple[list[dict[str, Any]], int]:
        page = max(page, 1)
        limit = min(max(limit, 1), 500)
        start = (page - 1) * limit
        end = start + limit
        return rows[start:end], len(rows)

    async def get_financial_expenses(self, filters: FinancialOverviewFilters, page: int = 1, limit: int = 50) -> WebPostoResponse:
        from src.services.employee_cash_ledger_service import EmployeeCashLedgerService
        from src.services.expense_lineage_service import ExpenseLineageService
        from src.services.expense_semantic_service import ExpenseSemanticService
        from src.services.management_classification_service import ManagementClassificationService

        empresas, error = await self._resolve_empresas(filters)
        if error is not None:
            return error
        empresa_lookup = self._empresa_lookup(empresas)

        all_expenses, fetch_error = await self._load_screen_expenses(filters)
        if fetch_error is not None:
            return fetch_error

        lineage_svc = ExpenseLineageService()
        semantic_svc = ExpenseSemanticService()
        mgmt_svc = ManagementClassificationService()
        ledger_svc = EmployeeCashLedgerService()
        ctx = await lineage_svc.build_context(self, filters)
        enriched = [
            mgmt_svc.classify_row(semantic_svc.classify_row(lineage_svc.enrich_row(row, ctx)))
            for row in all_expenses
        ]
        lineage_summary = lineage_svc.summarize(enriched)
        semantic_summary = semantic_svc.summarize(enriched)
        management_summary = mgmt_svc.summarize(enriched)
        resumo_cards = semantic_svc.build_resumo_cards(semantic_summary)
        resumo_gerencial = mgmt_svc.build_resumo_cards(management_summary)

        caixa_rows = list(ctx.closure_by_key.values())
        caixa_events = ledger_svc.build_caixa_events(caixa_rows)
        expense_events = ledger_svc.build_expense_events(enriched)
        balance_by_op = ledger_svc.build_balance_by_operator(caixa_events, expense_events)
        forensics = ledger_svc.summarize_forensics(caixa_events)
        balance_summary = ledger_svc.summarize_balance(balance_by_op)
        accountability = ledger_svc.build_accountability(
            caixa_events, ctx.titulos, ctx.despesas_rede, ctx.movimentos
        )
        recovery = ledger_svc.build_recovery(balance_by_op, accountability)
        employee_balance_card = ledger_svc.build_employee_balance_card(balance_summary)

        filtered = mgmt_svc.filter_rows(semantic_svc.filter_by_natures(enriched, filters), filters)
        filtered.sort(key=lambda x: str(x.get("data") or ""), reverse=True)
        page_data, total = self._paginate(filtered, page=page, limit=limit)

        employee_index: dict[int, dict[str, Any]] = {}
        if any(row.get("funcionarioCodigo") not in (None, "", 0) for row in page_data):
            from src.services.employee_dimension_service import EmployeeDimensionService

            try:
                employee_ctx = await EmployeeDimensionService(self.client).build(
                    filters.data_inicial, filters.data_final
                )
                employee_index = employee_ctx.get("index") or {}
            except Exception:
                LOGGER.warning("Dimensão de funcionários indisponível para despesas", exc_info=True)

        def _employee_name(codigo: Any) -> str | None:
            if codigo in (None, "", 0):
                return None
            try:
                info = employee_index.get(int(codigo))
            except (TypeError, ValueError):
                return None
            if not info:
                return None
            name = info.get("employeeName")
            return str(name).strip() if name else None

        resumo_por_origem: dict[str, dict[str, Any]] = {}
        for row in enriched:
            origem = str(row.get("origem") or "desconhecido")
            bucket = resumo_por_origem.setdefault(origem, {"count": 0, "valor": Decimal("0")})
            bucket["count"] += 1
            val = self._to_decimal(row.get("valor"))
            if val is not None:
                bucket["valor"] += val

        return WebPostoResponse.ok(
            {
                "page": max(page, 1),
                "limit": min(max(limit, 1), 500),
                "total": total,
                "lineageCoveragePct": lineage_summary.get("coveragePct"),
                "lineageTracedRecords": lineage_summary.get("tracedRecords"),
                "avgLineageConfidence": lineage_summary.get("avgLineageConfidence"),
                "semanticClassificationPct": semantic_summary.get("classificationPct"),
                "avgSemanticConfidence": semantic_summary.get("avgSemanticConfidence"),
                "pctFinancialImpact": semantic_summary.get("pctFinancialImpact"),
                "resumoPorNatureza": resumo_cards,
                "resumoPorGrupoGerencial": resumo_gerencial,
                "employeeCashLedger": {
                    "forensics": forensics,
                    "balanceSummary": balance_summary,
                    "accountability": accountability,
                    "recovery": recovery,
                    "employeeBalanceCard": employee_balance_card,
                },
                "managementClassificationPct": 100.0 if enriched else 0.0,
                "valorDreSim": management_summary.get("valorDreSim"),
                "valorDreNao": management_summary.get("valorDreNao"),
                "valorCashflowSim": management_summary.get("valorCashflowSim"),
                "resumoPorOrigem": {
                    k: {"count": v["count"], "valor": str(v["valor"].quantize(Decimal("0.01")))}
                    for k, v in sorted(resumo_por_origem.items())
                },
                "data": [
                    {
                        "empresaCodigo": row["empresaCodigo"],
                        "filial": self._empresa_name_by_codigo(row["empresaCodigo"], empresa_lookup),
                        "data": row["data"],
                        "valor": row["valor"],
                        "descricao": row.get("descricao") or row.get("planoConta"),
                        "planoConta": row["planoConta"],
                        "tipoDespesa": row["tipoDespesa"],
                        "centroCusto": row["centroCusto"],
                        "origem": row["origem"],
                        "origemReal": row.get("origemReal"),
                        "origemTecnica": row.get("origemTecnica"),
                        "origemNegocio": row.get("origemNegocio"),
                        "expenseNature": row.get("expenseNature"),
                        "expenseSubNature": row.get("expenseSubNature"),
                        "expenseNatureLabel": row.get("expenseNatureLabel"),
                        "semanticConfidence": row.get("semanticConfidence"),
                        "impactsFinancialResult": bool(row.get("impactsFinancialResult")),
                        "expenseManagementGroup": row.get("expenseManagementGroup"),
                        "expenseManagementClass": row.get("expenseManagementClass"),
                        "expenseManagementGroupLabel": row.get("expenseManagementGroupLabel"),
                        "expenseManagementClassLabel": row.get("expenseManagementClassLabel"),
                        "dreImpact": row.get("dreImpact"),
                        "cashFlowImpact": row.get("cashFlowImpact"),
                        "employeeAccountability": bool(row.get("employeeAccountability")),
                        "categoriaOperacional": row.get("categoriaOperacional"),
                        "classificacaoLineage": row.get("classificacaoLineage"),
                        "documento": row.get("documento"),
                        "fornecedor": row.get("fornecedor"),
                        "eventoOperacional": row.get("eventoOperacional"),
                        "operationalFinancialMatch": row.get("operationalFinancialMatch"),
                        "lineageConfidence": row.get("lineageConfidence"),
                        "lineagePath": row.get("lineagePath"),
                        "primarySource": row.get("primarySource"),
                        "rastreabilidadeOk": bool(row.get("rastreabilidadeOk")),
                        "categoria": row.get("categoria"),
                        "status": row["status"],
                        "caixaCodigo": row.get("caixaCodigo"),
                        "pdvCodigo": row.get("pdvCodigo"),
                        "funcionarioCodigo": row.get("funcionarioCodigo"),
                        "employeeName": _employee_name(row.get("funcionarioCodigo")),
                        "turnoCodigo": row.get("turnoCodigo"),
                        "turno": row.get("turno"),
                        "despesaApurado": row.get("despesaApurado"),
                        "despesaApresentado": row.get("despesaApresentado"),
                        "despesaDiferenca": row.get("despesaDiferenca"),
                        "matchFinanceiro": bool(row.get("matchFinanceiro")),
                        "fonte": row.get("fonte"),
                        "synthetic": False,
                    }
                    for row in page_data
                ],
                "synthetic": False,
            }
        )

    async def get_accounts_payable(self, filters: FinancialOverviewFilters, page: int = 1, limit: int = 50) -> WebPostoResponse:
        empresas, error = await self._resolve_empresas(filters)
        if error is not None:
            return error
        empresa_lookup = self._empresa_lookup(empresas)

        dados: list[dict[str, Any]] = []
        for empresa in empresas:
            empresa_codigo = empresa.get("empresaCodigo")
            if empresa_codigo is None:
                continue

            titulo_resp = await self._fetch_titulo_pagar(filters, empresa_codigo)
            if not titulo_resp.success:
                LOGGER.warning(f"Erro ao buscar contas a pagar para empresa {empresa_codigo}: {titulo_resp.error}")
                continue

            for row in self._rows(titulo_resp.data):
                normalized = self._normalize_titulo_pagar(row)
                if not normalized:
                    continue
                if self._titulo_matches(normalized, filters):
                    status = "pago" if "pago" in self._norm_text(normalized.get("situacao")) else "pendente"
                    dados.append(
                        {
                            "empresaCodigo": normalized["empresaCodigo"],
                            "filial": self._empresa_name_by_codigo(normalized["empresaCodigo"], empresa_lookup),
                            "fornecedor": normalized["fornecedor"],
                            "valor": normalized["valor"],
                            "vencimento": normalized["vencimento"],
                            "status": status,
                            "synthetic": False,
                        }
                    )

        dados = self._dedupe_rows(dados, keys=("empresaCodigo", "fornecedor", "valor", "vencimento", "status"))

        dados.sort(key=lambda x: str(x.get("vencimento") or ""))
        page_data, total = self._paginate(dados, page=page, limit=limit)
        return WebPostoResponse.ok(
            {
                "page": max(page, 1),
                "limit": min(max(limit, 1), 500),
                "total": total,
                "data": page_data,
                "synthetic": False,
            }
        )

    async def get_financial_overview_only(self, filters: FinancialOverviewFilters) -> WebPostoResponse:
        empresas, error = await self._resolve_empresas(filters)
        if error is not None:
            return error

        all_despesas, fetch_error = await self._load_filtered_expenses(filters)
        if fetch_error is not None:
            return fetch_error

        despesas_por_empresa: dict[Any, list[dict[str, Any]]] = {}
        for row in all_despesas:
            code = row.get("empresaCodigo")
            despesas_por_empresa.setdefault(code, []).append(row)

        postos: list[dict[str, Any]] = []
        total_despesas = Decimal("0")
        total_a_pagar = Decimal("0")

        for empresa in empresas:
            empresa_codigo = empresa.get("empresaCodigo")
            if empresa_codigo is None:
                continue

            filtro_empresa = FinancialOverviewFilters(
                data_inicial=filters.data_inicial,
                data_final=filters.data_final,
                empresa_codigo=empresa_codigo,
                tipo_despesa=filters.tipo_despesa,
                plano_conta=filters.plano_conta,
                centro_custo=filters.centro_custo,
                valor_min=filters.valor_min,
                valor_max=filters.valor_max,
                origem=filters.origem,
            )

            titulo_resp = await self._fetch_titulo_pagar(filtro_empresa, empresa_codigo)
            if not titulo_resp.success:
                return titulo_resp

            despesas_rows = despesas_por_empresa.get(empresa_codigo, [])
            titulo_rows = [
                x
                for x in (self._normalize_titulo_pagar(r) for r in self._rows(titulo_resp.data))
                if x and self._titulo_matches(x, filtro_empresa)
            ]
            titulo_rows = self._dedupe_rows(titulo_rows, keys=("empresaCodigo", "fornecedor", "valor", "vencimento", "situacao"))

            despesas_total = self._sum_values(despesas_rows, "valor")
            a_pagar_total = Decimal("0")
            for row in titulo_rows:
                if "pago" in self._norm_text(row.get("situacao")):
                    continue
                valor = self._to_decimal(row.get("valor"))
                valor_pago = self._to_decimal(row.get("valorPago")) or Decimal("0")
                if valor is not None:
                    aberto = valor - valor_pago
                    if aberto > 0:
                        a_pagar_total += aberto

            total_despesas += despesas_total
            total_a_pagar += a_pagar_total

            postos.append(
                {
                    "empresaCodigo": empresa_codigo,
                    "nome": self._normalize_empresa_name(empresa),
                    "total_despesas": str(despesas_total),
                    "total_a_pagar": str(a_pagar_total),
                    "synthetic": False,
                }
            )

        return WebPostoResponse.ok(
            {
                "postos": postos,
                "consolidado": {
                    "total_despesas": str(total_despesas),
                    "total_a_pagar": str(total_a_pagar),
                },
                "synthetic": False,
            }
        )

    async def get_sales(self, filters: FinancialOverviewFilters, page: int = 1, limit: int = 50) -> WebPostoResponse:
        empresas, error = await self._resolve_empresas(filters)
        if error is not None:
            return error
        empresa_lookup = self._empresa_lookup(empresas)

        rows: list[dict[str, Any]] = []
        total_vendido = Decimal("0")

        for empresa in empresas:
            empresa_codigo = empresa.get("empresaCodigo")
            if empresa_codigo is None:
                continue

            vendas_resp = await self._fetch_vendas_produtos(filters, empresa_codigo)
            if not vendas_resp.success:
                LOGGER.warning(f"Erro ao buscar vendas para empresa {empresa_codigo}: {vendas_resp.error}")
                continue

            venda_rows = self._rows((vendas_resp.data or {}).get("venda"))
            item_rows = self._rows((vendas_resp.data or {}).get("venda_item"))
            fp_rows = self._rows((vendas_resp.data or {}).get("venda_forma_pagamento"))

            itens_por_venda: dict[Any, list[dict[str, Any]]] = {}
            for item in item_rows:
                venda_codigo = item.get("vendaCodigo")
                if venda_codigo is None:
                    continue
                itens_por_venda.setdefault(venda_codigo, []).append(item)

            fp_por_venda: dict[Any, list[dict[str, Any]]] = {}
            for fp in fp_rows:
                venda_codigo = fp.get("vendaCodigo")
                if venda_codigo is None:
                    continue
                fp_por_venda.setdefault(venda_codigo, []).append(fp)

            for venda in venda_rows:
                venda_codigo = venda.get("vendaCodigo") or venda.get("codigo")
                data_venda = (
                    venda.get("data")
                    or venda.get("dataEmissao")
                    or venda.get("dataVenda")
                    or venda.get("dataHora")
                    or venda.get("dataMovimento")
                )
                # Extrai apenas a parte YYYY-MM-DD se vier como timestamp
                if data_venda and len(str(data_venda)) > 10:
                    data_venda = str(data_venda)[:10]
                if not data_venda:
                    continue

                total_row = self._to_decimal(venda.get("totalVenda") or venda.get("valorTotal"))
                if total_row is None:
                    total_row = self._sum_values(itens_por_venda.get(venda_codigo, []), "totalVenda")
                else:
                    total_row = normalize_webposto_sale_value(total_row)

                total_vendido += total_row
                itens = itens_por_venda.get(venda_codigo, [])
                formas = fp_por_venda.get(venda_codigo, [])

                principal_forma = ""
                if formas:
                    principal_forma = str(
                        formas[0].get("formaPagamento") or formas[0].get("descricaoFormaPagamento") or formas[0].get("descricao") or ""
                    )

                rows.append(
                    {
                        "empresaCodigo": empresa_codigo,
                        "filial": self._empresa_name_by_codigo(empresa_codigo, empresa_lookup),
                        "vendaCodigo": venda_codigo,
                        "data": str(data_venda),
                        "cliente": str(venda.get("cliente") or venda.get("clienteNome") or "consumidor final"),
                        "itens": len(itens),
                        "formaPagamento": principal_forma,
                        "totalVenda": str(total_row),
                        "synthetic": False,
                    }
                )

        rows.sort(key=lambda x: str(x.get("data") or ""), reverse=True)
        page_data, total = self._paginate(rows, page=page, limit=limit)
        return WebPostoResponse.ok(
            {
                "page": max(page, 1),
                "limit": min(max(limit, 1), 500),
                "total": total,
                "data": page_data,
                "consolidado": {
                    "total_vendas": str(total_vendido),
                    "qtd_vendas": total,
                },
                "synthetic": False,
            }
        )

    async def get_stock(self, filters: FinancialOverviewFilters, page: int = 1, limit: int = 50) -> WebPostoResponse:
        empresas, error = await self._resolve_empresas(filters)
        if error is not None:
            return error
        empresa_lookup = self._empresa_lookup(empresas)

        rows: list[dict[str, Any]] = []
        total_estoque = Decimal("0")
        total_tanques = 0

        for empresa in empresas:
            empresa_codigo = empresa.get("empresaCodigo")
            if empresa_codigo is None:
                continue

            params: dict[str, Any] = {
                "dataInicial": filters.data_inicial,
                "dataFinal": filters.data_final,
                "empresaCodigo": empresa_codigo,
            }

            produto_estoque_resp = await self.client.call_endpoint("produto_estoque", params=params)
            produto_estoque_rows: list[dict[str, Any]] = []
            if produto_estoque_resp.success:
                produto_estoque_rows = self._rows(produto_estoque_resp.data)
            elif (produto_estoque_resp.error and produto_estoque_resp.error.status in {400, 422}):
                # Fallback: alguns ambientes exigem outros filtros e retornam 400 sem indicar falta de permissao.
                produto_estoque_rows = []
            else:
                LOGGER.warning(f"Erro produto_estoque para empresa {empresa_codigo}: {produto_estoque_resp.error}")
                continue

            produto_resp = await self.client.call_endpoint("produto", params=params)
            if not produto_resp.success:
                LOGGER.warning(f"Erro produto para empresa {empresa_codigo}: {produto_resp.error}")
                continue

            tanque_resp = await self.client.call_endpoint("tanque", params=params)
            if not tanque_resp.success:
                LOGGER.warning(f"Erro tanque para empresa {empresa_codigo}: {tanque_resp.error}")
                continue

            estoque_periodo_resp = await self.client.call_endpoint("estoque_periodo", params=params)
            if not estoque_periodo_resp.success:
                LOGGER.warning(f"Erro estoque_periodo para empresa {empresa_codigo}: {estoque_periodo_resp.error}")
                continue

            # Filter early: keep only active fuel products from /INTEGRACAO/PRODUTO
            produtos = [p for p in self._rows(produto_resp.data) if is_active_fuel_product(p)]
            produtos_by_codigo: dict[Any, dict[str, Any]] = {p.get("produtoCodigo"): p for p in produtos if p.get("produtoCodigo") is not None}

            for row in produto_estoque_rows:
                produto_codigo = row.get("produtoCodigo")
                if produto_codigo not in produtos_by_codigo:
                    continue
                produto_ref = produtos_by_codigo[produto_codigo]
                quantidade = self._to_decimal(
                    row.get("quantidade") or row.get("estoque") or row.get("saldo") or row.get("quantidadeEstoque")
                )
                if quantidade is None:
                    quantidade = Decimal("0")

                total_estoque += quantidade
                rows.append(
                    {
                        "empresaCodigo": empresa_codigo,
                        "filial": self._empresa_name_by_codigo(empresa_codigo, empresa_lookup),
                        "tipoRegistro": "produto",
                        "codigo": produto_codigo,
                        "descricao": str(
                            row.get("descricao")
                            or produto_ref.get("descricao")
                            or produto_ref.get("produto")
                            or "Produto sem descricao"
                        ),
                        "unidade": str(row.get("unidade") or produto_ref.get("unidade") or ""),
                        "quantidade": str(quantidade),
                        "synthetic": False,
                    }
                )

            if not produto_estoque_rows:
                for row in self._rows(estoque_periodo_resp.data):
                    produto_codigo = row.get("produtoCodigo") or row.get("codigo")
                    if produto_codigo not in produtos_by_codigo:
                        continue
                    quantidade = self._to_decimal(row.get("quantidade") or row.get("saldo") or row.get("volume"))
                    rows.append(
                        {
                            "empresaCodigo": empresa_codigo,
                            "filial": self._empresa_name_by_codigo(empresa_codigo, empresa_lookup),
                            "tipoRegistro": "estoque_periodo",
                            "codigo": produto_codigo,
                            "descricao": str(row.get("descricao") or row.get("produto") or "Movimento estoque"),
                            "unidade": str(row.get("unidade") or ""),
                            "quantidade": str(quantidade if quantidade is not None else ""),
                            "synthetic": False,
                        }
                    )

            for tanque in self._rows(tanque_resp.data):
                produto_codigo = tanque.get("produtoCodigo")
                if produto_codigo not in produtos_by_codigo:
                    continue
                total_tanques += 1
                volume = self._to_decimal(tanque.get("volumeAtual") or tanque.get("volume") or tanque.get("litros"))
                rows.append(
                    {
                        "empresaCodigo": empresa_codigo,
                        "filial": self._empresa_name_by_codigo(empresa_codigo, empresa_lookup),
                        "tipoRegistro": "tanque",
                        "codigo": tanque.get("tanqueCodigo") or tanque.get("codigo"),
                        "descricao": str(tanque.get("descricao") or tanque.get("tanque") or "Tanque"),
                        "unidade": "L",
                        "quantidade": str(volume if volume is not None else ""),
                        "synthetic": False,
                    }
                )

        rows.sort(key=lambda x: (str(x.get("filial") or ""), str(x.get("tipoRegistro") or ""), str(x.get("descricao") or "")))
        page_data, total = self._paginate(rows, page=page, limit=limit)
        return WebPostoResponse.ok(
            {
                "page": max(page, 1),
                "limit": min(max(limit, 1), 500),
                "total": total,
                "data": page_data,
                "consolidado": {
                    "qtd_registros": total,
                    "qtd_tanques": total_tanques,
                    "total_estoque": str(total_estoque),
                },
                "synthetic": False,
            }
        )

    async def get_accounts_receivable(self, filters: FinancialOverviewFilters, page: int = 1, limit: int = 50) -> WebPostoResponse:
        empresas, error = await self._resolve_empresas(filters)
        if error is not None:
            return error
        empresa_lookup = self._empresa_lookup(empresas)

        dados: list[dict[str, Any]] = []
        for empresa in empresas:
            empresa_codigo = empresa.get("empresaCodigo")
            if empresa_codigo is None:
                continue

            params: dict[str, Any] = {
                "dataInicial": filters.data_inicial,
                "dataFinal": filters.data_final,
                "empresaCodigo": empresa_codigo,
            }

            titulo_receber_resp = await self.client.call_endpoint("titulo_receber", params=params)
            if not titulo_receber_resp.success:
                LOGGER.warning(f"Erro ao buscar contas a receber para empresa {empresa_codigo}: {titulo_receber_resp.error}")
                continue

            for row in self._rows(titulo_receber_resp.data):
                valor = self._to_decimal(row.get("valor") or row.get("valorTotal") or row.get("valorReceber"))
                if valor is None:
                    continue
                dados.append(
                    {
                        "empresaCodigo": empresa_codigo,
                        "filial": self._empresa_name_by_codigo(empresa_codigo, empresa_lookup),
                        "cliente": row.get("cliente") or row.get("clienteNome") or "",
                        "valor": str(valor),
                        "vencimento": str(row.get("vencimento") or ""),
                        "situacao": str(row.get("situacao") or ""),
                        "synthetic": False,
                    }
                )

        dados.sort(key=lambda x: str(x.get("vencimento") or ""))
        page_data, total = self._paginate(dados, page=page, limit=limit)
        return WebPostoResponse.ok(
            {
                "page": max(page, 1),
                "limit": min(max(limit, 1), 500),
                "total": total,
                "data": page_data,
                "synthetic": False,
            }
        )

    async def get_financial_overview(self, filters: FinancialOverviewFilters) -> WebPostoResponse:
        empresas, error = await self._resolve_empresas(filters)
        if error is not None:
            return error

        if not empresas:
            return WebPostoResponse.ok(
                {
                    "postos": [],
                    "consolidado": {
                        "total_despesas": "0",
                        "total_a_pagar": "0",
                        "total_vendas_combustivel": "0",
                        "total_vendas_produtos": "0",
                    },
                    "filters": {
                        "empresaCodigo": filters.empresa_codigo,
                        "dataInicial": filters.data_inicial,
                        "dataFinal": filters.data_final,
                    },
                    "synthetic": False,
                }
            )

        all_despesas, fetch_error = await self._load_filtered_expenses(filters)
        if fetch_error is not None:
            return fetch_error

        despesas_por_empresa: dict[Any, list[dict[str, Any]]] = {}
        for row in all_despesas:
            code = row.get("empresaCodigo")
            despesas_por_empresa.setdefault(code, []).append(row)

        combustivel_response = await self._fetch_vendas_combustivel()
        combustivel_payload = combustivel_response.data if combustivel_response.success else {}

        postos: list[dict[str, Any]] = []
        total_despesas = Decimal("0")
        total_a_pagar = Decimal("0")
        total_vendas_combustivel = Decimal("0")
        total_vendas_produtos = Decimal("0")

        for empresa in empresas:
            empresa_codigo = empresa.get("empresaCodigo")
            if empresa_codigo is None:
                continue

            titulo_resp = await self._fetch_titulo_pagar(filters, empresa_codigo)
            if not titulo_resp.success:
                LOGGER.warning(f"Erro titulo_pagar overview para empresa {empresa_codigo}: {titulo_resp.error}")
                continue

            vendas_prod_resp = await self._fetch_vendas_produtos(filters, empresa_codigo)
            if not vendas_prod_resp.success:
                LOGGER.warning(f"Erro vendas_produtos overview para empresa {empresa_codigo}: {vendas_prod_resp.error}")
                continue

            despesas_rows = despesas_por_empresa.get(empresa_codigo, [])
            titulo_rows = [
                x for x in (self._normalize_titulo_pagar(r) for r in self._rows(titulo_resp.data)) if x and self._titulo_matches(x, filters)
            ]
            titulo_rows = self._dedupe_rows(titulo_rows, keys=("empresaCodigo", "fornecedor", "valor", "vencimento", "situacao"))

            venda_item_rows = self._rows((vendas_prod_resp.data or {}).get("venda_item"))
            vendas_prod_total = self._sum_values(venda_item_rows, "totalVenda")

            despesas_total = self._sum_values(despesas_rows, "valor")
            a_pagar_total = Decimal("0")
            for row in titulo_rows:
                situacao = self._norm_text(row.get("situacao"))
                if "pago" in situacao:
                    continue
                valor = self._to_decimal(row.get("valor"))
                valor_pago = self._to_decimal(row.get("valorPago")) or Decimal("0")
                if valor is not None:
                    aberto = valor - valor_pago
                    if aberto > 0:
                        a_pagar_total += aberto

            posto_nome = self._normalize_empresa_name(empresa)
            vendas_combustivel_total = self._extract_combustivel_total_for_posto(combustivel_payload, posto_nome)

            total_despesas += despesas_total
            total_a_pagar += a_pagar_total
            total_vendas_produtos += vendas_prod_total
            total_vendas_combustivel += vendas_combustivel_total

            postos.append(
                {
                    "empresaCodigo": empresa_codigo,
                    "nome": posto_nome,
                    "despesas": str(despesas_total),
                    "a_pagar": str(a_pagar_total),
                    "vendas_combustivel": str(vendas_combustivel_total),
                    "vendas_produtos": str(vendas_prod_total),
                    "despesas_detalhes": despesas_rows,
                    "synthetic": False,
                }
            )

        return WebPostoResponse.ok(
            {
                "postos": postos,
                "consolidado": {
                    "total_despesas": str(total_despesas),
                    "total_a_pagar": str(total_a_pagar),
                    "total_vendas_combustivel": str(total_vendas_combustivel),
                    "total_vendas_produtos": str(total_vendas_produtos),
                },
                "filters": {
                    "empresaCodigo": filters.empresa_codigo,
                    "dataInicial": filters.data_inicial,
                    "dataFinal": filters.data_final,
                    "tipoDespesa": filters.tipo_despesa,
                    "planoContaCodigo": filters.plano_conta_codigo,
                    "planoConta": filters.plano_conta,
                    "centroCusto": filters.centro_custo,
                    "valorMin": str(filters.valor_min) if filters.valor_min is not None else None,
                    "valorMax": str(filters.valor_max) if filters.valor_max is not None else None,
                    "status": filters.status,
                    "origem": filters.origem,
                    "fornecedor": filters.fornecedor,
                    "vencimentoInicial": filters.vencimento_inicial,
                    "vencimentoFinal": filters.vencimento_final,
                },
                "synthetic": False,
            }
        )
