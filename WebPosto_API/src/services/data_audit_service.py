"""Sprint 60 — Homologação de Dados Reais e DRE Diário por Plano de Contas."""

from __future__ import annotations

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
from src.services.sales_composition_service import SalesCompositionService
from src.services.webposto_integration_service import get_webposto_integration_service

logger = logging.getLogger(__name__)

# Cache em memória do catálogo oficial (TTL 1h)
_PLANO_CACHE: dict[int, dict[str, Any]] = {}
_PLANO_CACHE_TS: float = 0.0
_PLANO_CACHE_TTL_S = 3600.0
_CENTRO_CACHE: dict[int, dict[str, Any]] = {}
_CENTRO_CACHE_TS: float = 0.0

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
    29019: "CPV",       # compras mercadoria / conveniência
    29050: "CPV",       # compras diversas (atacado/loja)
    47952: "CPV",       # compras de alimentos / cozinha
    29073: "PESSOAL",   # VEM trabalhador / encargos
    48547: "PESSOAL",   # vales / benefícios (keywords refinariam o restante)
    29020: "ADMINISTRATIVA",
    29051: "ADMINISTRATIVA",
    141276: "ADMINISTRATIVA",
    137578: "ADMINISTRATIVA",
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
    valorEstoqueImobilizado: float = 0.0
    fallback: bool = False
    mensagem: str | None = None


class DataAuditResponse(BaseModel):
    periodo: dict[str, str]
    filiais: list[FilialDailyAudit] = Field(default_factory=list)
    consolidado: dict[str, Any] = Field(default_factory=dict)
    success: bool = True


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
) -> bool:
    blob = f"{plano} {descricao}".casefold()
    if any(k in blob for k in _VALE_KEYS):
        return True
    # Plano 48547 no Grupo Lisboa concentra vales; exclui material óbvio
    if plano_codigo == 48547 and not any(
        k in blob for k in ("cadeado", "carregador", "aluguel", "mouse", "boia")
    ):
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
        self._composition = SalesCompositionService()
        self._client = get_webposto_client()
        self._settings = get_company_settings_service()

    async def _ensure_plano_catalog(self) -> dict[int, dict[str, Any]]:
        """Carrega PLANO_CONTA_GERENCIAL (paginado) com cache em memória."""
        global _PLANO_CACHE, _PLANO_CACHE_TS
        now = time.monotonic()
        if _PLANO_CACHE and (now - _PLANO_CACHE_TS) < _PLANO_CACHE_TTL_S:
            return _PLANO_CACHE
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
                    oficial = (
                        f"{hierarquia} - {descricao}"
                        if hierarquia and descricao
                        else (descricao or hierarquia or f"Plano {code}")
                    )
                    catalog[code] = {
                        "codigo": code,
                        "descricao": descricao,
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
            if catalog:
                _PLANO_CACHE = catalog
                _PLANO_CACHE_TS = now
                logger.info(
                    "Catálogo plano_conta_gerencial carregado: %s contas",
                    len(catalog),
                )
        except Exception as exc:
            logger.warning("Erro ao carregar plano_conta_gerencial: %s", exc)
        return _PLANO_CACHE or catalog

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

    async def _fetch_despesas(self, start: str, end: str) -> list[dict[str, Any]]:
        try:
            resp = await self._client.call_endpoint(
                "despesas_financeiro_rede",
                params={"dataInicial": start, "dataFinal": end},
            )
            if not resp.success:
                logger.warning("Despesas rede falhou: %s", resp.error)
                return []
            plano_cat = await self._ensure_plano_catalog()
            centro_cat = await self._ensure_centro_catalog()
            rows = _extract_rows(resp.data)
            normalized: list[dict[str, Any]] = []
            for row in rows:
                item = self._normalize_expense_row(row, plano_cat, centro_cat)
                if item is None:
                    continue
                normalized.append(item)
            return normalized
        except Exception as exc:
            logger.warning("Erro ao buscar despesas: %s", exc)
            return []

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
        plano_desc = str(
            row.get("planoContaGerencialDescricao")
            or row.get("planoConta")
            or row.get("descricaoPlano")
            or meta.get("descricao")
            or ""
        )
        plano_oficial = str(
            meta.get("oficial")
            or (
                f"{hierarquia} - {plano_desc}"
                if hierarquia and plano_desc
                else (
                    plano_desc
                    or hierarquia
                    or (f"Plano {plano_codigo}" if plano_codigo else "")
                )
            )
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
            or row.get("data")
            or row.get("dataLancamento")
            or row.get("dataMovimento")
            or ""
        )[:10]
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
        return {
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
            "dataVencimento": data_venc,
            "categoria": cat_key,
        }

    async def build(
        self,
        data_inicial: str | None = None,
        data_final: str | None = None,
        empresa_codigo: int | None = None,
    ) -> DataAuditResponse:
        hoje = date.today().isoformat()
        start = data_inicial or hoje
        end = data_final or hoje
        targets = (
            [int(empresa_codigo)]
            if empresa_codigo and int(empresa_codigo) in OFFICIAL_COMPANY_CODES
            else list(OFFICIAL_COMPANY_CODES)
        )

        despesas_rede = await self._fetch_despesas(start, end)
        vales_caixa_rede = await self._fetch_vales_caixa_apresentado(start, end)
        filiais: list[FilialDailyAudit] = []

        for codigo in targets:
            try:
                filiais.append(
                    await self._audit_filial(
                        codigo, start, end, despesas_rede, vales_caixa_rede
                    )
                )
            except Exception as exc:
                logger.exception("Data audit filial %s falhou: %s", codigo, exc)
                filiais.append(
                    FilialDailyAudit(
                        empresaCodigo=codigo,
                        empresaNome=FILIAL_NAMES.get(codigo, f"Empresa {codigo}"),
                        fallback=True,
                        mensagem=str(exc),
                        despesasPorCategoria=self._empty_categories(),
                    )
                )

        consolidado = {
            "faturamentoTotal": round(sum(f.faturamentoTotal for f in filiais), 2),
            "volumeLitros": round(sum(f.volumeLitros for f in filiais), 2),
            "quantidadeAbastecimentos": sum(f.quantidadeAbastecimentos for f in filiais),
            "despesasTotal": round(sum(f.despesasTotal for f in filiais), 2),
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
        }

        return DataAuditResponse(
            periodo={"inicio": start, "fim": end},
            filiais=filiais,
            consolidado=consolidado,
            success=True,
        )

    async def _audit_filial(
        self,
        empresa_codigo: int,
        start: str,
        end: str,
        despesas_rede: list[dict[str, Any]],
        vales_caixa_rede: list[dict[str, Any]] | None = None,
    ) -> FilialDailyAudit:
        nome = FILIAL_NAMES.get(
            empresa_codigo,
            self._settings.get_settings(empresa_codigo).empresa_nome,
        )

        # Vendas / abastecimentos (COUNT DISTINCT operacional)
        composition = await self._composition.build(start, end, empresa_codigo)
        fat = composition.summary.faturamentoCombustivel or composition.summary.faturamentoTotal
        # Preferir faturamento total setorial quando disponível
        fat_total = composition.summary.faturamentoTotal or fat
        litros = composition.summary.litrosVendidos
        qtd_abast = composition.summary.quantidadeAbastecimentos

        # Tanques + CPM
        tanks = await self._integration.get_tank_levels(empresa_codigo)
        costs = await self._integration.get_weighted_avg_cost(empresa_codigo)
        cpm_map = {
            str(c.get("produto_codigo")): _f(c.get("cpm_rs"))
            for c in (costs.custos or [])
            if _f(c.get("cpm_rs")) > 0
        }

        ocup_sum = 0.0
        ocup_n = 0
        valor_estoque = 0.0
        margem_sum = 0.0
        margem_n = 0

        for t in tanks.tanques or []:
            vol = _f(t.get("volume_atual_litros"))
            cap = _f(t.get("capacidade_litros"))
            if cap > 0:
                ocup_sum += (vol / cap) * 100
                ocup_n += 1
            codigo = str(t.get("produto_codigo") or "")
            cpm = cpm_map.get(codigo) or self._fallback_custo(empresa_codigo, codigo, str(t.get("produto_nome") or ""))
            if cpm > 0 and vol > 0:
                valor_estoque += vol * cpm
            # margem bruta aproximada: preço médio do dia - CPM
            preco_medio = (fat_total / litros) if litros > 0 else 0.0
            if cpm > 0 and preco_medio > 0:
                margem_sum += preco_medio - cpm
                margem_n += 1

        ocupacao = round(ocup_sum / ocup_n, 1) if ocup_n else 0.0
        margem_media = round(margem_sum / margem_n, 4) if margem_n else 0.0

        # Despesas da filial
        despesas_filial = [
            r
            for r in despesas_rede
            if int(r.get("empresaCodigo") or 0) == int(empresa_codigo)
        ]
        cats = self._group_expenses(despesas_filial)
        desp_total = round(sum(c.valor for c in cats), 2)
        resultado = round(fat_total - desp_total, 2)

        vales_caixa = [
            r
            for r in (vales_caixa_rede or [])
            if int(r.get("empresaCodigo") or 0) == int(empresa_codigo)
        ]
        vales = self._build_vales_block(despesas_filial, vales_caixa)

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
            valorEstoqueImobilizado=round(valor_estoque, 2),
            fallback=bool(composition.fallback) or not tanks.sucesso,
            mensagem=composition.mensagem,
        )

    def _fallback_custo(self, empresa_codigo: int, produto_codigo: str, nome: str) -> float:
        pricing = self._settings.get_product_pricing(empresa_codigo, produto_codigo)
        if pricing and pricing.custo_aquisicao_rs > 0:
            return float(pricing.custo_aquisicao_rs)
        # metadata global fallback
        settings = self._settings.get_settings(empresa_codigo)
        meta = settings.metadata or {}
        fallback_map = meta.get("custo_fallback_por_produto") or {}
        if isinstance(fallback_map, dict) and produto_codigo in fallback_map:
            return _f(fallback_map.get(produto_codigo))
        # custo_base por categoria no cadastro de produtos
        prod = self._settings.get_product_config(empresa_codigo, produto_codigo)
        if prod and prod.custo_base > 0:
            return float(prod.custo_base)
        # heurística por nome
        low = nome.casefold()
        defaults = meta.get("custo_fallback_defaults") or {}
        if isinstance(defaults, dict):
            if "etanol" in low or "alcool" in low:
                return _f(defaults.get("ETANOL"), 3.50)
            if "diesel" in low:
                return _f(defaults.get("DIESEL"), 5.50)
            if "gasolina" in low:
                return _f(defaults.get("GASOLINA"), 5.10)
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

    @staticmethod
    def _to_expense_item(row: dict[str, Any], label: str) -> ExpenseItem:
        oficial = str(
            row.get("planoContaOficial")
            or row.get("planoConta")
            or ""
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
            planoContaCodigo=row.get("planoContaCodigo"),
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
        items: list[dict[str, Any]] = []
        try:
            resp = await self._client.call_endpoint(
                "caixa_apresentado_rede",
                params={"dataInicial": start, "dataFinal": end},
            )
            if not resp.success:
                logger.info(
                    "caixa_apresentado_rede indisponível para vales: %s", resp.error
                )
                return []
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
                    or row.get("funcionarioCodigo")
                    or "Funcionário"
                )
                items.append(
                    {
                        "empresaCodigo": int(
                            row.get("empresaCodigo") or row.get("empresa") or 0
                        ),
                        "valor": valor,
                        "funcionario": funcionario,
                        "descricao": f"Vale caixa {row.get('caixaCodigo') or row.get('codigo') or ''}".strip(),
                        "planoConta": "Caixa Apresentado",
                        "planoContaCodigo": None,
                        "fonte": "caixa_apresentado",
                    }
                )
        except Exception as exc:
            logger.warning("Erro ao buscar vales no caixa apresentado: %s", exc)
        return items

    def _build_vales_block(
        self,
        despesas_filial: list[dict[str, Any]],
        vales_caixa: list[dict[str, Any]],
    ) -> ValesFuncionariosBlock:
        itens: list[ValeFuncionarioItem] = []

        for row in despesas_filial:
            desc = str(row.get("descricao") or "")
            plano = str(row.get("planoConta") or "")
            codigo = row.get("planoContaCodigo")
            try:
                plano_codigo = int(codigo) if codigo is not None else None
            except (TypeError, ValueError):
                plano_codigo = None
            if not is_vale_funcionario(plano, desc, plano_codigo):
                continue
            itens.append(
                ValeFuncionarioItem(
                    descricao=desc or plano,
                    funcionario=_extract_funcionario_name(desc),
                    valor=round(_f(row.get("valor")), 2),
                    planoConta=plano,
                    planoContaCodigo=plano_codigo,
                    fonte="despesa",
                )
            )

        # Se despesas não trouxeram linhas nominais, usa apurado do caixa
        if not itens and vales_caixa:
            for row in vales_caixa:
                itens.append(
                    ValeFuncionarioItem(
                        descricao=str(row.get("descricao") or "Vale (caixa apresentado)"),
                        funcionario=str(row.get("funcionario") or ""),
                        valor=round(_f(row.get("valor")), 2),
                        planoConta=str(row.get("planoConta") or "Caixa Apresentado"),
                        fonte="caixa_apresentado",
                    )
                )

        itens.sort(key=lambda i: i.valor, reverse=True)
        despesa_total = round(sum(i.valor for i in itens if i.fonte == "despesa"), 2)
        caixa_total = round(sum(_f(r.get("valor")) for r in vales_caixa), 2)
        # Total = maior fonte (evita somar despesa + caixa do mesmo vale)
        total = max(despesa_total, caixa_total, round(sum(i.valor for i in itens), 2))
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
            result.append(
                ExpenseCategoryBreakdown(
                    categoria=labels[key],
                    categoriaKey=key,
                    valor=valor,
                    qtd_lancamentos=len(items),
                    itens=[
                        self._to_expense_item(i, labels[key]).model_dump()
                        for i in items
                    ],
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
