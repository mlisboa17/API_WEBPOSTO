"""Sprint 60 — Homologação de Dados Reais e DRE Diário por Plano de Contas."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections import defaultdict
from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from src.core.config import OFFICIAL_COMPANY_CODES
from src.gateway.shared_client import get_webposto_client
from src.services.company_settings_service import get_company_settings_service
from src.services.expense_reclassify_service import get_expense_reclassify_service
from src.services.plano_contas_resolver import (
    PLANO_CATEGORIA_FALLBACK,
    catalog_as_options,
    enrich_catalog_with_fallbacks,
    format_plano_label,
    resolve_plano_nome,
)
from src.services.dre_regime import (
    classify_period_lock,
    filter_rows_by_regime,
    normalize_regime,
    regime_label,
)
from src.services.webposto_integration_service import get_webposto_integration_service
from src.utils.filial_normalizer import resolve_empresa_codigo

logger = logging.getLogger(__name__)

# Cache em memória do catálogo oficial (TTL 1h)
_PLANO_CACHE: dict[int, dict[str, Any]] = {}
_PLANO_CACHE_TS: float = 0.0
_PLANO_CACHE_TTL_S = 3600.0
_CENTRO_CACHE: dict[int, dict[str, Any]] = {}
_CENTRO_CACHE_TS: float = 0.0

# Hot-path caches (evita N× composition + HTTP síncrono)
_AUDIT_RESP_CACHE: dict[str, tuple[float, "DataAuditResponse"]] = {}
_AUDIT_RESP_TTL_S = 90.0
_DESPESAS_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_DESPESAS_TTL_S = 120.0
_VALES_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_VALES_TTL_S = 120.0
_TANQUE_CACHE: dict[int, tuple[float, Any]] = {}
_TANQUE_TTL_S = 300.0
_CPM_CACHE: dict[int, tuple[float, Any]] = {}
_CPM_TTL_S = 300.0
# Despesas rede: budget realista (0.6s matava CPV/plano de contas → zeros na UI)
_HTTP_BUDGET_S = 8.0
_HTTP_BUDGET_D0_S = 4.0
_TANQUE_BUDGET_S = 0.8

FILIAL_NAMES = {
    5555: "AP Casa Caiada",
    11495: "Posto VIP",
    74014: "Posto Real / Doze",
}

# Classificação executiva por plano de contas / descrição (WebPosto real)
_CPV_KEYS = (
    "cpv",
    "cmv",
    "custo",
    "combust",
    "mercador",
    "produto",
    "lubrif",
    "aquisic",
    "estoque",
    "ref nf",
    "compra",
    "atac",
    "armazem",
    "armazém",
    "seara",
    "doces",
    "bebidas",
    "souza cruz",
    "cigarro",
    "salgado",
    "pudim",
    "convenien",
)
_PESSOAL_KEYS = (
    "salar",
    "folha",
    "pessoal",
    "funcion",
    "frentist",
    "comiss",
    "encarg",
    "benefic",
    "hora extra",
    "inss",
    "fgts",
    "vale ",
    "vale",
    "trabalhador",
    "vem trabalhador",
    "veem ",
    "adiantament",
)

# Vales / adiantamentos a funcionários (subset de Pessoal — destaque na UI)
_VALE_KEYS = (
    "vale ",
    "vale-",
    "vales",
    "vale fun",
    "vale de fun",
    "adiantament",
    "emprestim",
)
_ADMIN_KEYS = (
    "energia",
    "agua",
    "água",
    "internet",
    "telefone",
    "software",
    "sistema",
    "manutenc",
    "manutenç",
    "expediente",
    "aluguel",
    "limpo",
    "consumo",
    "administrat",
    "operacion",
    "detergente",
    "removedor",
    "cadeado",
    "calibrador",
    "ensolamento",
    "piso",
    "banheiro",
    "carregador",
    "automacao",
    "automação",
    "caixa",
    "fita",
    "material",
)
_OUTRAS_KEYS = (
    "cartao",
    "cartão",
    "taxa",
    "tarif",
    "imposto",
    "juros",
    "banc",
    "financeir",
    "mdr",
    "iof",
    "policial",
    "policia",
)

# Heurística por código de plano gerencial observado no Grupo Lisboa
_PLANO_CODE_CATEGORY = {
    **PLANO_CATEGORIA_FALLBACK,
    29019: "CPV",
    29050: "CPV",
    47952: "CPV",
    29073: "PESSOAL",
    48547: "PESSOAL",
    29020: "ADMINISTRATIVA",
    29051: "ADMINISTRATIVA",
    141276: "ADMINISTRATIVA",
    137578: "ADMINISTRATIVA",
    141278: "OUTRAS",
    141275: "OUTRAS",
    148304: "OUTRAS",
}


class ExpenseItem(BaseModel):
    """Lançamento individual para drill-down do Plano de Contas."""

    id: str = ""
    numeroDocumento: str = ""
    numeroNF: str = ""
    descricao: str = ""
    historico: str = ""
    fornecedor: str = ""
    favorecido: str = ""
    categoria: str = "OUTRAS"
    categoriaLabel: str = ""
    valor: float = 0.0
    dataPagamento: str = ""
    dataVencimento: str = ""
    planoConta: str = ""
    planoContaCodigo: int | None = None
    planoContaHierarquia: str = ""
    planoContaOficial: str = ""
    planoContaTipo: str = ""
    grupoConta: str = ""
    grupoContaCodigo: int | None = None
    centroCusto: str = ""
    centroCustoCodigo: int | None = None
    empresaCodigo: int = 0


class ExpenseCategoryBreakdown(BaseModel):
    categoria: str
    categoriaKey: str = ""
    valor: float = 0.0
    qtd_lancamentos: int = 0
    itens: list[dict[str, Any]] = Field(default_factory=list)


class ExpenseDetailsResponse(BaseModel):
    empresaCodigo: int | None = None
    empresaNome: str = ""
    periodo: dict[str, str] = Field(default_factory=dict)
    categoria: str = ""
    categoriaKey: str = ""
    subtotal: float = 0.0
    quantidade: int = 0
    itens: list[ExpenseItem] = Field(default_factory=list)
    success: bool = True
    mensagem: str | None = None


class ValeFuncionarioItem(BaseModel):
    descricao: str = ""
    funcionario: str = ""
    valor: float = 0.0
    planoConta: str = ""
    planoContaCodigo: int | None = None
    fonte: str = "despesa"  # despesa | caixa_apresentado
    dataCaixa: str = ""
    turno: str = ""


class ValesFuncionariosBlock(BaseModel):
    total: float = 0.0
    quantidade: int = 0
    itens: list[ValeFuncionarioItem] = Field(default_factory=list)


class FilialDailyAudit(BaseModel):
    empresaCodigo: int
    empresaNome: str
    faturamentoTotal: float = 0.0
    volumeLitros: float = 0.0
    quantidadeAbastecimentos: int = 0
    ocupacaoTanquesPct: float = 0.0
    despesasTotal: float = 0.0
    despesasPorCategoria: list[ExpenseCategoryBreakdown] = Field(default_factory=list)
    valesFuncionarios: ValesFuncionariosBlock = Field(default_factory=ValesFuncionariosBlock)
    resultadoOperacionalDiario: float = 0.0
    margemBrutaMediaRsLitro: float = 0.0
    cpvCombustivel: float = 0.0
    margemBrutaCombustivel: float = 0.0
    custoMedioRsLitro: float = 0.0
    valorEstoqueImobilizado: float = 0.0
    fallback: bool = False
    mensagem: str | None = None


class DataAuditResponse(BaseModel):
    periodo: dict[str, str]
    filiais: list[FilialDailyAudit] = Field(default_factory=list)
    consolidado: dict[str, Any] = Field(default_factory=dict)
    success: bool = True
    regime: str = "competencia"
    periodLock: dict[str, Any] = Field(default_factory=dict)


def _f(val: Any, default: float = 0.0) -> float:
    try:
        if val is None or val == "":
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def _extract_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("resultados", "dados", "data", "items"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return [r for r in rows if isinstance(r, dict)]
    return []


def classify_expense_category(
    plano: str,
    descricao: str = "",
    plano_codigo: int | None = None,
) -> str:
    from src.services.cash_reconciliation.prestacao_contas_parser import (
        is_operational_expense_text,
    )

    # Consumo/infra nunca vai para Pessoal/Vales
    if is_operational_expense_text(plano, descricao):
        return "ADMINISTRATIVA"
    blob = f"{plano} {descricao}".casefold()
    # Keywords têm prioridade sobre código (ex.: vale vs material no mesmo plano)
    if any(k in blob for k in _PESSOAL_KEYS):
        return "PESSOAL"
    if any(k in blob for k in _ADMIN_KEYS):
        return "ADMINISTRATIVA"
    if any(k in blob for k in _CPV_KEYS):
        return "CPV"
    if any(k in blob for k in _OUTRAS_KEYS):
        return "OUTRAS"
    if plano_codigo is not None:
        mapped = _PLANO_CODE_CATEGORY.get(int(plano_codigo))
        if mapped:
            return mapped
    return "OUTRAS"


def is_vale_funcionario(
    plano: str,
    descricao: str = "",
    plano_codigo: int | None = None,
    funcionario: str | None = None,
) -> bool:
    """Vale legítimo: tipo VALE/ADIANTAMENTO + sem marcadores operacionais.

    Despesas de consumo/infra (crachá, água, graxa, etc.) NUNCA são vale.
    Plano 48547 sozinho não basta — exige keyword de vale ou nome de colaborador.
    """
    from src.services.cash_reconciliation.prestacao_contas_parser import (
        is_operational_expense_text,
        is_valid_employee_identity,
    )

    if is_operational_expense_text(plano, descricao):
        return False
    blob = f"{plano} {descricao}".casefold()
    has_vale_kw = any(k in blob for k in _VALE_KEYS)
    nome = (funcionario or "").strip() or _extract_funcionario_name(descricao)
    if has_vale_kw:
        # Keyword de vale sem identidade ainda pode ser candidata; o block filtra depois
        return True
    # Plano 48547: só com nome/código válido (evita material operacional no mesmo plano)
    if plano_codigo == 48547 and is_valid_employee_identity(nome):
        return True
    return False


def _extract_funcionario_name(descricao: str) -> str:
    """Tenta extrair o nome após 'vale ' na descrição."""
    text = (descricao or "").strip()
    match = re.search(
        r"vale\s+(?:de\s+|do\s+|da\s+|para\s+)?([a-zA-ZÀ-ÿ][\wÀ-ÿ.\s]{1,40})",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        name = match.group(1).strip(" -.")
        # corta em preposições comuns de finalidade
        for stop in (" para ", " de ", " do ", " da "):
            idx = name.casefold().find(stop.strip())
            if idx > 2:
                name = name[:idx].strip()
        return name.title() if name else ""
    return ""


def _extract_nf_from_text(text: str) -> str:
    match = re.search(
        r"(?:nf|n\.?\s*f\.?|nota)\s*:?\s*0*([0-9]{3,})",
        text or "",
        flags=re.IGNORECASE,
    )
    return match.group(1) if match else ""


def _extract_fornecedor_from_text(text: str) -> str:
    """Heurística: 'REF NF:xxx - FORNECEDOR - FORNECEDOR'."""
    raw = (text or "").strip()
    if " - " in raw:
        parts = [p.strip() for p in raw.split(" - ") if p.strip()]
        if len(parts) >= 2:
            # após o trecho da NF
            candidate = parts[1]
            if not re.match(r"^(ref|nf|pag)", candidate, flags=re.IGNORECASE):
                return candidate[:80]
    return ""


def _resolve_categoria_key(categoria: str | None) -> str | None:
    if not categoria:
        return None
    raw = str(categoria).strip()
    upper = raw.upper()
    aliases = {
        "CPV": "CPV",
        "CUSTO DE PRODUTOS VENDIDOS (CPV)": "CPV",
        "CUSTO DE PRODUTOS VENDIDOS": "CPV",
        "PESSOAL": "PESSOAL",
        "DESPESAS COM PESSOAL / FUNCIONÁRIOS": "PESSOAL",
        "DESPESAS COM PESSOAL / FUNCIONARIOS": "PESSOAL",
        "ADMINISTRATIVA": "ADMINISTRATIVA",
        "ADMIN": "ADMINISTRATIVA",
        "DESPESAS ADMINISTRATIVAS & OPERACIONAIS": "ADMINISTRATIVA",
        "OUTRAS": "OUTRAS",
        "OUTRAS DESPESAS / FINANCEIRAS": "OUTRAS",
    }
    if upper in aliases:
        return aliases[upper]
    # match parcial por label amigável
    low = raw.casefold()
    if "cpv" in low or "produtos vendidos" in low:
        return "CPV"
    if "pessoal" in low or "funcion" in low:
        return "PESSOAL"
    if "administrat" in low or "operacion" in low:
        return "ADMINISTRATIVA"
    if "outras" in low or "financeir" in low:
        return "OUTRAS"
    return None


class DataAuditService:
    """Consolida faturamento, volume, abastecimentos, tanques e despesas do dia."""

    def __init__(self) -> None:
        self._integration = get_webposto_integration_service()
        self._client = get_webposto_client()
        self._settings = get_company_settings_service()

    async def _ensure_plano_catalog(self) -> dict[int, dict[str, Any]]:
        """Carrega PLANO_CONTA_GERENCIAL (+ fallback PLANO_DE_CONTAS) com de-para local."""
        global _PLANO_CACHE, _PLANO_CACHE_TS
        now = time.monotonic()
        if _PLANO_CACHE and (now - _PLANO_CACHE_TS) < _PLANO_CACHE_TTL_S:
            return enrich_catalog_with_fallbacks(_PLANO_CACHE)
        catalog: dict[int, dict[str, Any]] = {}
        try:
            ultimo: int | None = None
            for _ in range(30):
                params: dict[str, Any] = {}
                if ultimo is not None:
                    params["ultimoCodigo"] = ultimo
                resp = await self._client.call_endpoint(
                    "plano_conta_gerencial", params=params
                )
                if not resp.success:
                    logger.warning(
                        "plano_conta_gerencial falhou: %s", resp.error
                    )
                    break
                batch = _extract_rows(resp.data)
                if not batch:
                    break
                for row in batch:
                    try:
                        code = int(
                            row.get("planoContaCodigo")
                            or row.get("codigo")
                            or 0
                        )
                    except (TypeError, ValueError):
                        continue
                    if code <= 0:
                        continue
                    hierarquia = str(row.get("hierarquia") or "").strip()
                    descricao = str(row.get("descricao") or "").strip()
                    oficial = format_plano_label(
                        code, descricao=descricao, hierarquia=hierarquia
                    )
                    catalog[code] = {
                        "codigo": code,
                        "descricao": resolve_plano_nome(
                            code, descricao=descricao, hierarquia=hierarquia
                        ),
                        "hierarquia": hierarquia,
                        "oficial": oficial,
                        "tipo": str(row.get("tipo") or ""),
                        "natureza": str(row.get("natureza") or ""),
                        "grupoConta": str(
                            row.get("grupoConta")
                            or row.get("grupoContaDescricao")
                            or ""
                        ),
                        "grupoContaCodigo": row.get("grupoContaCodigo"),
                        "fonte": "plano_conta_gerencial",
                    }
                raw = resp.data if isinstance(resp.data, dict) else {}
                new_u = raw.get("ultimoCodigo")
                try:
                    new_u_int = int(new_u) if new_u is not None else None
                except (TypeError, ValueError):
                    new_u_int = None
                if (
                    new_u_int is None
                    or new_u_int == ultimo
                    or len(batch) < 50
                ):
                    break
                ultimo = new_u_int
            # Complemento via PLANO_DE_CONTAS quando gerencial veio vazio/parcial
            if len(catalog) < 20:
                try:
                    resp2 = await self._client.call_endpoint(
                        "plano_de_contas", params={}
                    )
                    if resp2.success:
                        for row in _extract_rows(resp2.data):
                            try:
                                code = int(
                                    row.get("planoContaCodigo")
                                    or row.get("codigo")
                                    or row.get("id")
                                    or 0
                                )
                            except (TypeError, ValueError):
                                continue
                            if code <= 0 or code in catalog:
                                continue
                            descricao = str(
                                row.get("descricao")
                                or row.get("nome")
                                or row.get("planoConta")
                                or ""
                            )
                            catalog[code] = {
                                "codigo": code,
                                "descricao": resolve_plano_nome(
                                    code, descricao=descricao
                                ),
                                "hierarquia": str(row.get("hierarquia") or ""),
                                "oficial": format_plano_label(
                                    code, descricao=descricao
                                ),
                                "fonte": "plano_de_contas",
                            }
                except Exception as exc2:
                    logger.warning("plano_de_contas fallback: %s", exc2)
            catalog = enrich_catalog_with_fallbacks(catalog)
            if catalog:
                _PLANO_CACHE = catalog
                _PLANO_CACHE_TS = now
                logger.info(
                    "Catálogo plano de contas carregado: %s contas",
                    len(catalog),
                )
        except Exception as exc:
            logger.warning("Erro ao carregar plano_conta_gerencial: %s", exc)
            catalog = enrich_catalog_with_fallbacks(catalog or _PLANO_CACHE or {})
        return enrich_catalog_with_fallbacks(_PLANO_CACHE or catalog)

    async def _ensure_centro_catalog(self) -> dict[int, dict[str, Any]]:
        global _CENTRO_CACHE, _CENTRO_CACHE_TS
        now = time.monotonic()
        if _CENTRO_CACHE and (now - _CENTRO_CACHE_TS) < _PLANO_CACHE_TTL_S:
            return _CENTRO_CACHE
        catalog: dict[int, dict[str, Any]] = {}
        try:
            resp = await self._client.call_endpoint("centro_custo", params={})
            if resp.success:
                for row in _extract_rows(resp.data):
                    try:
                        code = int(
                            row.get("centroCustoCodigo") or row.get("codigo") or 0
                        )
                    except (TypeError, ValueError):
                        continue
                    if code <= 0:
                        continue
                    catalog[code] = {
                        "codigo": code,
                        "descricao": str(row.get("descricao") or ""),
                        "tipo": str(row.get("tipoCentroCusto") or ""),
                    }
                _CENTRO_CACHE = catalog
                _CENTRO_CACHE_TS = now
        except Exception as exc:
            logger.warning("Erro ao carregar centro_custo: %s", exc)
        return _CENTRO_CACHE or catalog

    async def _fetch_despesas(
        self, start: str, end: str, *, budget_s: float | None = None
    ) -> list[dict[str, Any]]:
        cache_key = f"{start}|{end}"
        now = time.monotonic()
        cached = _DESPESAS_CACHE.get(cache_key)
        if cached and (now - cached[0]) < _DESPESAS_TTL_S:
            return cached[1]
        from src.services.webposto.offline_mode import webposto_offline_mode

        if webposto_offline_mode():
            return cached[1] if cached else []
        timeout = float(budget_s if budget_s is not None else _HTTP_BUDGET_S)
        try:
            resp = await asyncio.wait_for(
                self._client.call_endpoint(
                    "despesas_financeiro_rede",
                    params={"dataInicial": start, "dataFinal": end},
                ),
                timeout=timeout,
            )
            if not resp.success:
                logger.warning("Despesas rede falhou: %s", resp.error)
                return cached[1] if cached else []
            plano_cat = await self._ensure_plano_catalog()
            centro_cat = await self._ensure_centro_catalog()
            rows = _extract_rows(resp.data)
            normalized: list[dict[str, Any]] = []
            for row in rows:
                item = self._normalize_expense_row(row, plano_cat, centro_cat)
                if item is None:
                    continue
                normalized.append(item)
            _DESPESAS_CACHE[cache_key] = (time.monotonic(), normalized)
            return normalized
        except asyncio.TimeoutError:
            logger.warning("Despesas rede timeout %.1fs — cache/stale", timeout)
            return cached[1] if cached else []
        except Exception as exc:
            logger.warning("Erro ao buscar despesas: %s", exc)
            return cached[1] if cached else []

    def _normalize_expense_row(
        self,
        row: dict[str, Any],
        plano_cat: dict[int, dict[str, Any]] | None = None,
        centro_cat: dict[int, dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        empresa = int(row.get("empresaCodigo") or row.get("empresa") or 0)
        valor = _f(
            row.get("valor")
            or row.get("valorDespesa")
            or row.get("valorTotal")
            or row.get("valorLancamento")
        )
        if valor <= 0:
            return None
        plano_codigo_raw = (
            row.get("planoContaGerencialCodigo")
            or row.get("planoContaCodigo")
            or row.get("codigoPlano")
        )
        try:
            plano_codigo = int(plano_codigo_raw) if plano_codigo_raw is not None else None
        except (TypeError, ValueError):
            plano_codigo = None

        meta = (plano_cat or {}).get(plano_codigo or -1) or {}
        hierarquia = str(
            row.get("hierarquia")
            or row.get("planoContaHierarquia")
            or meta.get("hierarquia")
            or ""
        )
        plano_desc_raw = str(
            row.get("planoContaGerencialDescricao")
            or row.get("planoConta")
            or row.get("descricaoPlano")
            or meta.get("descricao")
            or ""
        )
        plano_desc = resolve_plano_nome(
            plano_codigo,
            descricao=plano_desc_raw,
            hierarquia=hierarquia,
            catalog=plano_cat,
        )
        plano_oficial = format_plano_label(
            plano_codigo,
            descricao=plano_desc_raw,
            hierarquia=hierarquia,
            catalog=plano_cat,
        )
        plano = plano_oficial or plano_desc

        grupo_codigo_raw = (
            row.get("grupoContaCodigo")
            or row.get("grupoCodigo")
            or meta.get("grupoContaCodigo")
        )
        try:
            grupo_codigo = int(grupo_codigo_raw) if grupo_codigo_raw is not None else None
        except (TypeError, ValueError):
            grupo_codigo = None
        grupo = str(
            row.get("grupoConta")
            or row.get("grupoContaDescricao")
            or meta.get("grupoConta")
            or ""
        )

        centro_codigo_raw = (
            row.get("centroCustoCodigo")
            or row.get("codigoCentroCusto")
            or row.get("centroCusto")
        )
        centro_codigo: int | None
        try:
            if isinstance(centro_codigo_raw, (int, float)) or (
                isinstance(centro_codigo_raw, str) and centro_codigo_raw.strip().isdigit()
            ):
                centro_codigo = int(centro_codigo_raw)
            else:
                centro_codigo = None
        except (TypeError, ValueError):
            centro_codigo = None
        centro_meta = (centro_cat or {}).get(centro_codigo or -1) or {}
        centro = str(
            row.get("centroCustoDescricao")
            or row.get("descricaoCentroCusto")
            or (
                row.get("centroCusto")
                if not isinstance(row.get("centroCusto"), (int, float))
                else ""
            )
            or centro_meta.get("descricao")
            or ""
        )

        desc = str(
            row.get("descricaoDocumento")
            or row.get("descricao")
            or row.get("historico")
            or ""
        )
        historico = str(row.get("historico") or row.get("observacao") or desc)
        numero_doc = str(
            row.get("numeroDocumento")
            or row.get("documento")
            or row.get("numeroDoc")
            or ""
        )
        numero_nf = str(
            row.get("numeroNF")
            or row.get("notaFiscal")
            or row.get("nfNumero")
            or _extract_nf_from_text(desc)
            or ""
        )
        fornecedor = str(
            row.get("fornecedor")
            or row.get("fornecedorNome")
            or row.get("nomeFornecedor")
            or row.get("favorecido")
            or _extract_fornecedor_from_text(desc)
            or ""
        )
        favorecido = str(
            row.get("favorecido")
            or row.get("beneficiario")
            or fornecedor
            or ""
        )
        data_pag = str(
            row.get("dataPagamento")
            or row.get("dataLiquidacao")
            or row.get("dataBaixa")
            or ""
        )[:10]
        data_comp = str(
            row.get("dataEmissao")
            or row.get("dataNota")
            or row.get("data")
            or row.get("dataLancamento")
            or row.get("dataMovimento")
            or row.get("dataCompetencia")
            or ""
        )[:10]
        # Fallback cruzado para não perder linha sem um dos lados preenchido
        if not data_pag:
            data_pag = data_comp
        if not data_comp:
            data_comp = data_pag
        data_venc = str(
            row.get("dataVencimento") or row.get("vencimento") or ""
        )[:10]
        raw_id = (
            row.get("codigo")
            or row.get("despesaCodigo")
            or row.get("lancamentoCodigo")
            or row.get("id")
            or f"{empresa}-{plano_codigo}-{data_pag}-{valor}"
        )
        cat_key = classify_expense_category(plano_desc or plano, desc, plano_codigo)
        item = {
            "id": str(raw_id),
            "empresaCodigo": empresa,
            "valor": valor,
            "planoConta": plano,
            "planoContaCodigo": plano_codigo,
            "planoContaHierarquia": hierarquia,
            "planoContaOficial": plano_oficial,
            "planoContaTipo": str(meta.get("tipo") or row.get("tipo") or ""),
            "grupoConta": grupo,
            "grupoContaCodigo": grupo_codigo,
            "centroCusto": centro,
            "centroCustoCodigo": centro_codigo,
            "descricao": desc,
            "historico": historico,
            "numeroDocumento": numero_doc,
            "numeroNF": numero_nf,
            "fornecedor": fornecedor,
            "favorecido": favorecido,
            "dataPagamento": data_pag,
            "dataCompetencia": data_comp,
            "dataEmissao": data_comp,
            "data": data_comp,
            "dataVencimento": data_venc,
            "categoria": cat_key,
        }
        return get_expense_reclassify_service().apply_to_row(
            item, catalog=plano_cat
        )

    async def build(
        self,
        data_inicial: str | None = None,
        data_final: str | None = None,
        empresa_codigo: int | None = None,
        regime: str | None = None,
    ) -> DataAuditResponse:
        t0 = time.perf_counter()
        hoje = date.today().isoformat()
        start = data_inicial or hoje
        end = data_final or hoje
        empresa = resolve_empresa_codigo(empresa_codigo)
        regime_norm = normalize_regime(regime)
        period_lock = classify_period_lock(start, end)
        # v4: regime competencia/caixa + trava de período
        cache_key = f"v4|{start}|{end}|{empresa}|{regime_norm}"
        now = time.monotonic()
        cached = _AUDIT_RESP_CACHE.get(cache_key)
        if cached and (now - cached[0]) < _AUDIT_RESP_TTL_S:
            return cached[1]

        targets = (
            [int(empresa)]
            if empresa is not None and int(empresa) in OFFICIAL_COMPANY_CODES
            else list(OFFICIAL_COMPANY_CODES)
        )

        # Fuel local (RAM/DB) uma vez — substitui N× SalesCompositionService
        from src.services.fuel_volumetry_service import get_fuel_volumetry_service

        fuel = await get_fuel_volumetry_service().build(start, end, empresa)
        fuel_by_emp = {int(f.empresa_codigo): f for f in fuel.por_filial}

        is_d0 = start == end == hoje
        # D0: tenta HTTP com budget menor; se vazio, usa cache quente (nunca trava CPV em 0 sem tentar).
        if is_d0:
            despesas_rede, vales_caixa_rede = await asyncio.gather(
                self._fetch_despesas(start, end, budget_s=_HTTP_BUDGET_D0_S),
                self._fetch_vales_caixa_apresentado(start, end),
            )
            if not despesas_rede:
                despesas_rede = self._despesas_cache_only(start, end)
            if not vales_caixa_rede:
                vales_caixa_rede = self._vales_cache_only(start, end)
        else:
            despesas_rede, vales_caixa_rede = await asyncio.gather(
                self._fetch_despesas(start, end),
                self._fetch_vales_caixa_apresentado(start, end),
            )

        # Re-filtra despesas pela data do regime escolhido (nota vs boleto)
        despesas_rede = filter_rows_by_regime(despesas_rede, start, end, regime_norm)

        from src.services.webposto.offline_mode import raise_if_offline_without_local

        raise_if_offline_without_local(
            bool(despesas_rede)
            or bool(vales_caixa_rede)
            or float(getattr(fuel, "total_litros", 0) or 0) > 0
            or float(getattr(fuel, "total_valor", 0) or 0) > 0,
            detail="data-audit sem cache/SQLite local",
        )

        fuel_prod_by_emp: dict[int, list[Any]] = defaultdict(list)
        for row in fuel.por_produto or []:
            fuel_prod_by_emp[int(getattr(row, "empresa_codigo", 0) or 0)].append(row)

        filiais = list(
            await asyncio.gather(
                *[
                    self._audit_filial(
                        codigo,
                        start,
                        end,
                        despesas_rede,
                        vales_caixa_rede,
                        fuel_row=fuel_by_emp.get(codigo),
                        fuel_products=fuel_prod_by_emp.get(codigo) or [],
                        fuel_fonte=fuel.fonte,
                        skip_http_tanks=is_d0,
                    )
                    for codigo in targets
                ]
            )
        )

        cpv_total = 0.0
        cpv_comb = 0.0
        for f in filiais:
            for cat in f.despesasPorCategoria or []:
                if (cat.categoriaKey or "").upper() == "CPV":
                    cpv_total += float(cat.valor or 0)
            cpv_comb += float(getattr(f, "cpvCombustivel", 0) or 0)
        if cpv_comb > cpv_total:
            cpv_total = cpv_comb
        fat_total = round(sum(f.faturamentoTotal for f in filiais), 2)
        desp_total = round(sum(f.despesasTotal for f in filiais), 2)
        litros_total = round(sum(f.volumeLitros for f in filiais), 2)
        margem_bruta = round(fat_total - cpv_total, 2)
        margem_rs_l = (
            round(margem_bruta / litros_total, 4) if litros_total > 0 else 0.0
        )
        consolidado = {
            "faturamentoTotal": fat_total,
            "volumeLitros": litros_total,
            "quantidadeAbastecimentos": sum(f.quantidadeAbastecimentos for f in filiais),
            "despesasTotal": desp_total,
            "cpvTotal": round(cpv_total, 2),
            "cpvCombustivel": round(cpv_comb or cpv_total, 2),
            "margemBruta": margem_bruta,
            "margemBrutaCombustivel": round(
                sum(float(getattr(f, "margemBrutaCombustivel", 0) or 0) for f in filiais),
                2,
            ),
            "margemBrutaMediaRsLitro": margem_rs_l,
            "despesasOperacionais": round(max(0.0, desp_total - cpv_total), 2),
            "valesFuncionariosTotal": round(
                sum(f.valesFuncionarios.total for f in filiais), 2
            ),
            "valesFuncionariosQtd": sum(f.valesFuncionarios.quantidade for f in filiais),
            "resultadoOperacionalDiario": round(
                sum(f.resultadoOperacionalDiario for f in filiais), 2
            ),
            "valorEstoqueImobilizado": round(
                sum(f.valorEstoqueImobilizado for f in filiais), 2
            ),
            "ocupacaoTanquesPctMedia": round(
                (
                    sum(f.ocupacaoTanquesPct for f in filiais) / len(filiais)
                    if filiais
                    else 0.0
                ),
                1,
            ),
            "fonteFuel": fuel.fonte,
            "regime": regime_norm,
            "regimeLabel": regime_label(regime_norm),
            "periodLockMode": period_lock.get("mode"),
            "latencyMs": round((time.perf_counter() - t0) * 1000.0, 2),
        }

        result = DataAuditResponse(
            periodo={"inicio": start, "fim": end},
            filiais=filiais,
            consolidado=consolidado,
            success=True,
            regime=regime_norm,
            periodLock=period_lock,
        )
        # Não trava 90s com D0 incompleto (despesas ainda aquecendo)
        incomplete_d0 = is_d0 and not despesas_rede
        if not incomplete_d0:
            _AUDIT_RESP_CACHE[cache_key] = (time.monotonic(), result)
        logger.info(
            "data-audit ok empresa=%s filiais=%d latencyMs=%.1f fonte=%s incomplete=%s",
            empresa,
            len(filiais),
            consolidado["latencyMs"],
            fuel.fonte,
            incomplete_d0,
        )
        return result

    @staticmethod
    def _despesas_cache_only(start: str, end: str) -> list[dict[str, Any]]:
        cached = _DESPESAS_CACHE.get(f"{start}|{end}")
        if cached and (time.monotonic() - cached[0]) < _DESPESAS_TTL_S:
            return cached[1]
        return []

    @staticmethod
    def _vales_cache_only(start: str, end: str) -> list[dict[str, Any]]:
        cached = _VALES_CACHE.get(f"{start}|{end}")
        if cached and (time.monotonic() - cached[0]) < _VALES_TTL_S:
            return cached[1]
        return []

    async def _get_tanks_cached(self, empresa_codigo: int) -> Any:
        now = time.monotonic()
        cached = _TANQUE_CACHE.get(empresa_codigo)
        if cached and (now - cached[0]) < _TANQUE_TTL_S:
            return cached[1]

        class _Empty:
            sucesso = False
            tanques: list = []

        try:
            tanks = await asyncio.wait_for(
                self._integration.get_tank_levels(empresa_codigo),
                timeout=_TANQUE_BUDGET_S,
            )
            _TANQUE_CACHE[empresa_codigo] = (time.monotonic(), tanks)
            return tanks
        except Exception as exc:
            logger.warning("tanques empresa=%s: %s", empresa_codigo, exc)
            return cached[1] if cached else _Empty()

    async def _get_cpm_cached(self, empresa_codigo: int) -> Any:
        now = time.monotonic()
        cached = _CPM_CACHE.get(empresa_codigo)
        if cached and (now - cached[0]) < _CPM_TTL_S:
            return cached[1]

        class _Empty:
            custos: list = []

        try:
            costs = await asyncio.wait_for(
                self._integration.get_weighted_avg_cost(empresa_codigo),
                timeout=_TANQUE_BUDGET_S,
            )
            _CPM_CACHE[empresa_codigo] = (time.monotonic(), costs)
            return costs
        except Exception as exc:
            logger.warning("cpm empresa=%s: %s", empresa_codigo, exc)
            return cached[1] if cached else _Empty()

    async def _audit_filial(
        self,
        empresa_codigo: int,
        start: str,
        end: str,
        despesas_rede: list[dict[str, Any]],
        vales_caixa_rede: list[dict[str, Any]] | None = None,
        *,
        fuel_row: Any = None,
        fuel_products: list[Any] | None = None,
        fuel_fonte: str = "",
        skip_http_tanks: bool = False,
    ) -> FilialDailyAudit:
        try:
            return await self._audit_filial_inner(
                empresa_codigo,
                start,
                end,
                despesas_rede,
                vales_caixa_rede,
                fuel_row=fuel_row,
                fuel_products=fuel_products or [],
                fuel_fonte=fuel_fonte,
                skip_http_tanks=skip_http_tanks,
            )
        except Exception as exc:
            logger.exception("Data audit filial %s falhou: %s", empresa_codigo, exc)
            return FilialDailyAudit(
                empresaCodigo=empresa_codigo,
                empresaNome=FILIAL_NAMES.get(empresa_codigo, f"Empresa {empresa_codigo}"),
                fallback=True,
                mensagem=str(exc),
                despesasPorCategoria=self._empty_categories(),
            )

    async def _audit_filial_inner(
        self,
        empresa_codigo: int,
        start: str,
        end: str,
        despesas_rede: list[dict[str, Any]],
        vales_caixa_rede: list[dict[str, Any]] | None = None,
        *,
        fuel_row: Any = None,
        fuel_products: list[Any] | None = None,
        fuel_fonte: str = "",
        skip_http_tanks: bool = False,
    ) -> FilialDailyAudit:
        nome = FILIAL_NAMES.get(
            empresa_codigo,
            self._settings.get_settings(empresa_codigo).empresa_nome,
        )

        # Vendas / abastecimentos via fuel_volumetry (RAM/DB) — sem composition HTTP
        fat_total = float(getattr(fuel_row, "valor", 0) or 0) if fuel_row else 0.0
        litros = float(getattr(fuel_row, "litros", 0) or 0) if fuel_row else 0.0
        qtd_abast = int(getattr(fuel_row, "transacoes", 0) or 0) if fuel_row else 0
        fuel_ok = fuel_row is not None and (fat_total > 0 or litros > 0)

        if skip_http_tanks:
            # D0: tanques/CPM só cache — sem HTTP nem create_task no request
            now = time.monotonic()
            t_cached = _TANQUE_CACHE.get(empresa_codigo)
            c_cached = _CPM_CACHE.get(empresa_codigo)

            class _EmptyT:
                sucesso = False
                tanques: list = []

            class _EmptyC:
                custos: list = []

            tanks = (
                t_cached[1]
                if t_cached and (now - t_cached[0]) < _TANQUE_TTL_S
                else _EmptyT()
            )
            costs = (
                c_cached[1]
                if c_cached and (now - c_cached[0]) < _CPM_TTL_S
                else _EmptyC()
            )
        else:
            tanks, costs = await asyncio.gather(
                self._get_tanks_cached(empresa_codigo),
                self._get_cpm_cached(empresa_codigo),
            )
        cpm_map = {
            str(c.get("produto_codigo")): _f(c.get("cpm_rs"))
            for c in (getattr(costs, "custos", None) or [])
            if _f(c.get("cpm_rs")) > 0
        }

        ocup_sum = 0.0
        ocup_n = 0
        valor_estoque = 0.0
        margem_sum = 0.0
        margem_n = 0
        tanks_ok = bool(getattr(tanks, "sucesso", False))

        for t in getattr(tanks, "tanques", None) or []:
            vol = _f(t.get("volume_atual_litros"))
            cap = _f(t.get("capacidade_litros"))
            if cap > 0:
                ocup_sum += (vol / cap) * 100
                ocup_n += 1
            codigo = str(t.get("produto_codigo") or "")
            cpm = cpm_map.get(codigo) or self._fallback_custo(
                empresa_codigo, codigo, str(t.get("produto_nome") or "")
            )
            if cpm > 0 and vol > 0:
                valor_estoque += vol * cpm
            preco_medio = (fat_total / litros) if litros > 0 else 0.0
            if cpm > 0 and preco_medio > 0:
                margem_sum += preco_medio - cpm
                margem_n += 1

        ocupacao = round(ocup_sum / ocup_n, 1) if ocup_n else 0.0
        margem_media = round(margem_sum / margem_n, 4) if margem_n else 0.0

        # CPV combustível: litros × custo aquisição (CPM/NF/distribuidora + frete/ST)
        from src.services.fuel_cpv_engine import (
            compute_fuel_cpv,
            ledger_cpv_is_unreliable,
        )

        cpm_weighted = 0.0
        cpm_weight = 0.0
        for t in getattr(tanks, "tanques", None) or []:
            vol = _f(t.get("volume_atual_litros"))
            codigo = str(t.get("produto_codigo") or "")
            cpm = cpm_map.get(codigo) or self._fallback_custo(
                empresa_codigo, codigo, str(t.get("produto_nome") or "")
            )
            if cpm > 0 and vol > 0:
                cpm_weighted += cpm * vol
                cpm_weight += vol
        avg_cpm = (cpm_weighted / cpm_weight) if cpm_weight > 0 else 0.0
        if avg_cpm <= 0 and cpm_map:
            vals = list(cpm_map.values())
            avg_cpm = sum(vals) / len(vals)
        if avg_cpm <= 0:
            avg_cpm = self._resolve_avg_cpm_fallback(empresa_codigo)

        fuel_cpv = compute_fuel_cpv(
            litros_total=litros,
            faturamento_combustivel=fat_total,
            products=list(fuel_products or []),
            cpm_map=cpm_map,
            cost_resolver=lambda cod, nome: self._fallback_custo(empresa_codigo, cod, nome),
            avg_cpm_estoque=avg_cpm,
        )
        cpv_fuel_est = float(fuel_cpv["cpv"])
        cpv_source = str(fuel_cpv["fonte"])
        margem_media = float(fuel_cpv["margem_bruta_rs_litro"]) or margem_media

        despesas_filial = [
            r
            for r in despesas_rede
            if int(r.get("empresaCodigo") or 0) == int(empresa_codigo)
        ]
        cats = self._group_expenses(despesas_filial)
        # CPV autoritativo da pista: substitui ledger zerado OU subestimado (margem ~50%)
        cpv_from_ledger = next(
            (c for c in cats if (c.categoriaKey or "").upper() == "CPV"), None
        )
        cpv_injected = False
        ledger_cpv = float(cpv_from_ledger.valor or 0) if cpv_from_ledger else 0.0
        if cpv_fuel_est > 0 and (
            cpv_from_ledger is None
            or ledger_cpv_is_unreliable(
                ledger_cpv=ledger_cpv,
                fat_combustivel=fat_total,
                litros=litros,
                cpv_estimado=cpv_fuel_est,
            )
        ):
            if cpv_from_ledger is None:
                cats.insert(
                    0,
                    ExpenseCategoryBreakdown(
                        categoria="Custo de Produtos Vendidos (CPV)",
                        categoriaKey="CPV",
                        valor=cpv_fuel_est,
                        qtd_lancamentos=1,
                        itens=[],
                    ),
                )
            else:
                cpv_from_ledger.valor = cpv_fuel_est
                cpv_from_ledger.qtd_lancamentos = max(
                    int(cpv_from_ledger.qtd_lancamentos or 0), 1
                )
            cpv_injected = True

        desp_total = round(sum(c.valor for c in cats), 2)
        # Resultado Líquido = Faturamento − (CPV + Despesas operacionais) = Fat − despesasTotal
        resultado = round(fat_total - desp_total, 2)
        cpv_combustivel = cpv_fuel_est if cpv_fuel_est > 0 else (
            float(cpv_from_ledger.valor or 0) if cpv_from_ledger else 0.0
        )
        margem_bruta_comb = round(fat_total - cpv_combustivel, 2)
        custo_medio_l = float(fuel_cpv["custo_medio_rs_litro"])

        vales_caixa = [
            r
            for r in (vales_caixa_rede or [])
            if int(r.get("empresaCodigo") or 0) == int(empresa_codigo)
        ]
        vales = self._build_vales_block(despesas_filial, vales_caixa)

        msg_parts = []
        if fuel_fonte:
            msg_parts.append(f"fonte={fuel_fonte}")
        if not fuel_ok:
            msg_parts.append("fuel vazio (aguardando cache/DB)")
        if not tanks_ok:
            msg_parts.append("tanques indisponíveis/timeout")
        if cpv_injected:
            msg_parts.append(
                f"CPV combustível via {cpv_source or 'CPM/estoque'} (sem lançamento CPV no período)"
            )

        return FilialDailyAudit(
            empresaCodigo=empresa_codigo,
            empresaNome=nome,
            faturamentoTotal=round(fat_total, 2),
            volumeLitros=round(litros, 2),
            quantidadeAbastecimentos=qtd_abast,
            ocupacaoTanquesPct=ocupacao,
            despesasTotal=desp_total,
            despesasPorCategoria=cats,
            valesFuncionarios=vales,
            resultadoOperacionalDiario=resultado,
            margemBrutaMediaRsLitro=margem_media,
            cpvCombustivel=round(cpv_combustivel, 2),
            margemBrutaCombustivel=margem_bruta_comb,
            custoMedioRsLitro=round(custo_medio_l, 4),
            valorEstoqueImobilizado=round(valor_estoque, 2),
            fallback=not fuel_ok or not tanks_ok,
            mensagem="; ".join(msg_parts) if msg_parts else None,
        )

    def _resolve_avg_cpm_fallback(self, empresa_codigo: int) -> float:
        """CPM médio quando tanques/ledger estão vazios — pricing cadastro → metadata → 5.0."""
        settings = self._settings.get_settings(empresa_codigo)
        custos = [
            float(p.custo_aquisicao_rs)
            for p in (getattr(settings, "precos_produtos", None) or [])
            if float(getattr(p, "custo_aquisicao_rs", 0) or 0) > 0
        ]
        if custos:
            return sum(custos) / len(custos)
        bases = [
            float(p.custo_base)
            for p in (getattr(settings, "produtos", None) or [])
            if float(getattr(p, "custo_base", 0) or 0) > 0
            and bool(getattr(p, "ativo", True))
        ]
        if bases:
            return sum(bases) / len(bases)
        meta = settings.metadata or {}
        g = _f(meta.get("custo_fallback_global"), 0.0)
        return g if g > 0 else 5.0

    def _fallback_custo(self, empresa_codigo: int, produto_codigo: str, nome: str) -> float:
        pricing = self._settings.get_product_pricing(empresa_codigo, produto_codigo)
        if pricing and pricing.custo_aquisicao_rs > 0:
            return float(pricing.custo_aquisicao_rs)
        # metadata global fallback
        settings = self._settings.get_settings(empresa_codigo)
        meta = settings.metadata or {}
        fallback_map = meta.get("custo_fallback_por_produto") or {}
        if isinstance(fallback_map, dict) and produto_codigo and produto_codigo in fallback_map:
            return _f(fallback_map.get(produto_codigo))
        # custo_base por categoria no cadastro de produtos
        if produto_codigo:
            prod = self._settings.get_product_config(empresa_codigo, produto_codigo)
            if prod and prod.custo_base > 0:
                return float(prod.custo_base)
        # match por nome no cadastro (Gasolina C / Etanol Hidratado etc.)
        low = (nome or "").casefold()
        if low:
            for p in getattr(settings, "produtos", None) or []:
                pname = str(getattr(p, "nome", "") or "").casefold()
                if pname and (pname in low or low in pname) and float(getattr(p, "custo_base", 0) or 0) > 0:
                    return float(p.custo_base)
            defaults = meta.get("custo_fallback_defaults") or {}
            if isinstance(defaults, dict):
                if "etanol" in low or "alcool" in low:
                    return _f(defaults.get("ETANOL"), 3.50)
                if "diesel" in low or "s10" in low or "s500" in low:
                    return _f(defaults.get("DIESEL"), 5.50)
                if "gasolina" in low:
                    return _f(defaults.get("GASOLINA"), 5.10)
                if "gnv" in low:
                    return _f(defaults.get("GNV"), 3.80)
        return _f(meta.get("custo_fallback_global"), 0.0)

    async def get_expense_details(
        self,
        data_inicial: str | None = None,
        data_final: str | None = None,
        empresa_codigo: int | None = None,
        categoria: str | None = None,
    ) -> ExpenseDetailsResponse:
        """Drill-down: lançamentos individuais de uma categoria do Plano de Contas."""
        hoje = date.today().isoformat()
        start = data_inicial or hoje
        end = data_final or data_inicial or hoje
        cat_key = _resolve_categoria_key(categoria)
        labels = {
            "CPV": "Custo de Produtos Vendidos (CPV)",
            "PESSOAL": "Despesas com Pessoal / Funcionários",
            "ADMINISTRATIVA": "Despesas Administrativas & Operacionais",
            "OUTRAS": "Outras Despesas / Financeiras",
        }
        if not cat_key:
            return ExpenseDetailsResponse(
                empresaCodigo=empresa_codigo,
                empresaNome=FILIAL_NAMES.get(empresa_codigo or 0, ""),
                periodo={"inicio": start, "fim": end},
                success=False,
                mensagem="categoriaPlanoContas inválida",
            )

        rows = await self._fetch_despesas(start, end)
        if empresa_codigo:
            rows = [
                r
                for r in rows
                if int(r.get("empresaCodigo") or 0) == int(empresa_codigo)
            ]
        filtered = [r for r in rows if r.get("categoria") == cat_key]
        itens = [self._to_expense_item(r, labels[cat_key]) for r in filtered]
        itens.sort(key=lambda i: (i.dataPagamento or "", -i.valor))
        subtotal = round(sum(i.valor for i in itens), 2)
        return ExpenseDetailsResponse(
            empresaCodigo=empresa_codigo,
            empresaNome=FILIAL_NAMES.get(empresa_codigo or 0, "Rede"),
            periodo={"inicio": start, "fim": end},
            categoria=labels[cat_key],
            categoriaKey=cat_key,
            subtotal=subtotal,
            quantidade=len(itens),
            itens=itens,
            success=True,
        )

    async def list_plano_contas_options(self) -> list[dict[str, Any]]:
        catalog = await self._ensure_plano_catalog()
        return catalog_as_options(catalog)

    def invalidate_despesas_cache(self) -> None:
        _DESPESAS_CACHE.clear()
        _AUDIT_RESP_CACHE.clear()

    @staticmethod
    def _to_expense_item(row: dict[str, Any], label: str) -> ExpenseItem:
        codigo = row.get("planoContaCodigo")
        try:
            codigo_int = int(codigo) if codigo is not None else None
        except (TypeError, ValueError):
            codigo_int = None
        oficial = format_plano_label(
            codigo_int,
            descricao=str(row.get("planoContaOficial") or row.get("planoConta") or ""),
            hierarquia=str(row.get("planoContaHierarquia") or ""),
        )
        return ExpenseItem(
            id=str(row.get("id") or ""),
            numeroDocumento=str(row.get("numeroDocumento") or ""),
            numeroNF=str(row.get("numeroNF") or ""),
            descricao=str(row.get("descricao") or ""),
            historico=str(row.get("historico") or row.get("descricao") or ""),
            fornecedor=str(row.get("fornecedor") or ""),
            favorecido=str(row.get("favorecido") or row.get("fornecedor") or ""),
            categoria=str(row.get("categoria") or "OUTRAS"),
            categoriaLabel=label,
            valor=round(_f(row.get("valor")), 2),
            dataPagamento=str(row.get("dataPagamento") or ""),
            dataVencimento=str(row.get("dataVencimento") or ""),
            planoConta=oficial,
            planoContaCodigo=codigo_int,
            planoContaHierarquia=str(row.get("planoContaHierarquia") or ""),
            planoContaOficial=oficial,
            planoContaTipo=str(row.get("planoContaTipo") or ""),
            grupoConta=str(row.get("grupoConta") or ""),
            grupoContaCodigo=row.get("grupoContaCodigo"),
            centroCusto=str(row.get("centroCusto") or ""),
            centroCustoCodigo=row.get("centroCustoCodigo"),
            empresaCodigo=int(row.get("empresaCodigo") or 0),
        )

    async def _fetch_vales_caixa_apresentado(
        self, start: str, end: str
    ) -> list[dict[str, Any]]:
        """Vales apurados nos caixas (valeFunApurado) via CAIXA_APRESENTADO_REDE."""
        cache_key = f"{start}|{end}"
        now = time.monotonic()
        cached = _VALES_CACHE.get(cache_key)
        if cached and (now - cached[0]) < _VALES_TTL_S:
            return cached[1]

        items: list[dict[str, Any]] = []
        try:
            resp = await asyncio.wait_for(
                self._client.call_endpoint(
                    "caixa_apresentado_rede",
                    params={"dataInicial": start, "dataFinal": end},
                ),
                timeout=_HTTP_BUDGET_S,
            )
            if not resp.success:
                logger.info(
                    "caixa_apresentado_rede indisponível para vales: %s", resp.error
                )
                return cached[1] if cached else []
            from src.services.cash_reconciliation.prestacao_contas_parser import (
                has_caixa_traceability,
                is_operational_expense_text,
                is_valid_employee_identity,
            )

            for row in _extract_rows(resp.data):
                valor = _f(
                    row.get("valeFunApurado")
                    or row.get("valeFuncionarioApurado")
                    or row.get("valeFuncionario")
                    or row.get("valeApurado")
                )
                if valor <= 0:
                    continue
                funcionario = str(
                    row.get("funcionarioNome")
                    or row.get("nomeFuncionario")
                    or row.get("operador")
                    or ""
                ).strip()
                fid = row.get("funcionarioCodigo") or row.get("codigoFuncionario")
                data_caixa = str(
                    row.get("dataMovimento")
                    or row.get("dataAbertura")
                    or row.get("data")
                    or ""
                )[:10]
                turno = str(
                    row.get("turno")
                    or row.get("pdv")
                    or row.get("caixaCodigo")
                    or row.get("codigo")
                    or ""
                ).strip()
                desc = (
                    f"Vale caixa {row.get('caixaCodigo') or row.get('codigo') or ''}".strip()
                )
                if is_operational_expense_text(desc, row.get("observacao"), row.get("historico")):
                    continue
                if not is_valid_employee_identity(funcionario, fid):
                    continue
                if not has_caixa_traceability(data_caixa, turno):
                    continue
                items.append(
                    {
                        "empresaCodigo": int(
                            row.get("empresaCodigo") or row.get("empresa") or 0
                        ),
                        "valor": valor,
                        "funcionario": funcionario,
                        "descricao": desc,
                        "planoConta": "Caixa Apresentado",
                        "planoContaCodigo": None,
                        "fonte": "caixa_apresentado",
                        "dataCaixa": data_caixa,
                        "turno": turno,
                    }
                )
            _VALES_CACHE[cache_key] = (time.monotonic(), items)
        except asyncio.TimeoutError:
            logger.warning("vales caixa timeout %.1fs", _HTTP_BUDGET_S)
            return cached[1] if cached else []
        except Exception as exc:
            logger.warning("Erro ao buscar vales no caixa apresentado: %s", exc)
            return cached[1] if cached else []
        return items

    def _build_vales_block(
        self,
        despesas_filial: list[dict[str, Any]],
        vales_caixa: list[dict[str, Any]],
    ) -> ValesFuncionariosBlock:
        from src.services.cash_reconciliation.prestacao_contas_parser import (
            has_caixa_traceability,
            is_valid_employee_identity,
        )

        itens: list[ValeFuncionarioItem] = []

        for row in despesas_filial:
            desc = str(row.get("descricao") or "")
            plano = str(row.get("planoConta") or "")
            codigo = row.get("planoContaCodigo")
            try:
                plano_codigo = int(codigo) if codigo is not None else None
            except (TypeError, ValueError):
                plano_codigo = None
            funcionario = (
                str(row.get("funcionario") or row.get("funcionarioNome") or "").strip()
                or _extract_funcionario_name(desc)
            )
            if not is_vale_funcionario(plano, desc, plano_codigo, funcionario):
                continue
            if not is_valid_employee_identity(funcionario, row.get("funcionarioCodigo")):
                continue
            data_caixa = str(
                row.get("dataCaixa")
                or row.get("dataMovimento")
                or row.get("dataPagamento")
                or row.get("data")
                or ""
            )[:10]
            turno = str(
                row.get("turno") or row.get("pdv") or row.get("caixaCodigo") or ""
            ).strip()
            # Despesas nominais: data obrigatória; turno preferencial (usa plano como fallback fraco)
            if not data_caixa:
                continue
            if not turno:
                turno = str(plano_codigo or plano or "DESPESA")[:20]
            itens.append(
                ValeFuncionarioItem(
                    descricao=desc or plano,
                    funcionario=funcionario,
                    valor=round(_f(row.get("valor")), 2),
                    planoConta=plano,
                    planoContaCodigo=plano_codigo,
                    fonte="despesa",
                    dataCaixa=data_caixa,
                    turno=turno,
                )
            )

        # Complementa com apurado do caixa (já filtrado na origem)
        if vales_caixa:
            seen = {
                (
                    i.funcionario.casefold(),
                    round(i.valor, 2),
                    i.dataCaixa,
                    i.turno,
                )
                for i in itens
            }
            for row in vales_caixa:
                funcionario = str(row.get("funcionario") or "").strip()
                data_caixa = str(row.get("dataCaixa") or "")[:10]
                turno = str(row.get("turno") or "").strip()
                if not is_valid_employee_identity(funcionario, row.get("funcionarioCodigo")):
                    continue
                if not has_caixa_traceability(data_caixa, turno):
                    continue
                key = (funcionario.casefold(), round(_f(row.get("valor")), 2), data_caixa, turno)
                if key in seen:
                    continue
                seen.add(key)
                itens.append(
                    ValeFuncionarioItem(
                        descricao=str(row.get("descricao") or "Vale (caixa apresentado)"),
                        funcionario=funcionario,
                        valor=round(_f(row.get("valor")), 2),
                        planoConta=str(row.get("planoConta") or "Caixa Apresentado"),
                        fonte="caixa_apresentado",
                        dataCaixa=data_caixa,
                        turno=turno,
                    )
                )

        itens.sort(key=lambda i: i.valor, reverse=True)
        # Totalizador = soma apenas dos débitos cobráveis exibidos
        total = round(sum(i.valor for i in itens), 2)
        return ValesFuncionariosBlock(
            total=total,
            quantidade=len(itens),
            itens=itens[:50],
        )

    def _group_expenses(self, rows: list[dict[str, Any]]) -> list[ExpenseCategoryBreakdown]:
        buckets: dict[str, list[dict[str, Any]]] = {
            "CPV": [],
            "PESSOAL": [],
            "ADMINISTRATIVA": [],
            "OUTRAS": [],
        }
        for row in rows:
            cat = row.get("categoria") or classify_expense_category(
                str(row.get("planoConta") or ""), str(row.get("descricao") or "")
            )
            if cat not in buckets:
                cat = "OUTRAS"
            buckets[cat].append(row)

        labels = {
            "CPV": "Custo de Produtos Vendidos (CPV)",
            "PESSOAL": "Despesas com Pessoal / Funcionários",
            "ADMINISTRATIVA": "Despesas Administrativas & Operacionais",
            "OUTRAS": "Outras Despesas / Financeiras",
        }
        result: list[ExpenseCategoryBreakdown] = []
        for key in ("CPV", "PESSOAL", "ADMINISTRATIVA", "OUTRAS"):
            items = buckets[key]
            valor = round(sum(_f(i.get("valor")) for i in items), 2)
            # Lançamentos individuais só via drill-down lazy
            # (GET /expenses/details ou /finance/expense-entry/drill-down).
            result.append(
                ExpenseCategoryBreakdown(
                    categoria=labels[key],
                    categoriaKey=key,
                    valor=valor,
                    qtd_lancamentos=len(items),
                    itens=[],
                )
            )
        return result

    @staticmethod
    def _empty_categories() -> list[ExpenseCategoryBreakdown]:
        return [
            ExpenseCategoryBreakdown(
                categoria="Custo de Produtos Vendidos (CPV)", categoriaKey="CPV"
            ),
            ExpenseCategoryBreakdown(
                categoria="Despesas com Pessoal / Funcionários", categoriaKey="PESSOAL"
            ),
            ExpenseCategoryBreakdown(
                categoria="Despesas Administrativas & Operacionais",
                categoriaKey="ADMINISTRATIVA",
            ),
            ExpenseCategoryBreakdown(
                categoria="Outras Despesas / Financeiras", categoriaKey="OUTRAS"
            ),
        ]
