"""Sincronização híbrida: autodiscovery de produtos + consolidação diária."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, update
from sqlmodel import col

from src.core.config import OFFICIAL_COMPANY_CODES
from src.gateway.shared_client import get_webposto_client
from src.infrastructure.config.database import AsyncSessionLocal
from src.models.company_product_model import CompanyProductModel
from src.models.sales_daily_summary_model import SalesDailySummaryModel
from src.services.abastecimento_service import AbastecimentoService
from src.services.webposto_integration_service import get_webposto_integration_service

logger = logging.getLogger(__name__)

FILIAL_NAMES = {
    5555: "AP Casa Caiada",
    11495: "Posto VIP",
    74014: "Posto Real / Doze",
}

_ADITIVADO_KEYS = (
    "ADITIV",
    "PREMIUM",
    "PODIUM",
    "GRID",
    "V-POWER",
    "VPOWER",
    "RACING",
)


def _f(val: Any, default: float = 0.0) -> float:
    try:
        if val is None or val == "":
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def classify_product(nome: str) -> tuple[str, bool]:
    """Retorna (categoria, is_aditivado) a partir do nome WebPosto."""
    upper = (nome or "").upper()
    is_aditivado = any(k in upper for k in _ADITIVADO_KEYS)
    categoria = AbastecimentoService.classify_fuel_type(nome) or "OUTROS"
    if categoria == "GASOLINA" and is_aditivado:
        categoria = "GASOLINA_ADITIVADA"
    elif categoria == "ETANOL" and is_aditivado:
        categoria = "ETANOL_ADITIVADO"
    elif categoria == "DIESEL" and is_aditivado:
        categoria = "DIESEL_ADITIVADO"
    return categoria, is_aditivado


def _product_code(row: dict[str, Any]) -> str:
    """Codigo do combustivel — NUNCA usar 'codigo' (é abastecimentoCodigo)."""
    for key in ("codigoProduto", "produtoCodigo", "produtoLmcCodigo", "produto_codigo"):
        val = row.get(key)
        if val is None:
            continue
        code = str(val).strip()
        # SKUs reais ~6-8 dígitos; IDs de abastecimento têm 9+
        if code and code not in ("0",) and code.isdigit() and len(code) <= 8:
            return code
        if code and not code.isdigit() and 1 <= len(code) <= 16:
            return code
    return ""


def _product_name(row: dict[str, Any], codigo: str = "") -> str:
    """Nome real do WebPosto — vazio se ausente (não sobrescrever com placeholder)."""
    for key in (
        "produtoDescricao",
        "produtoNome",
        "nomeProduto",
        "produto",
        "descricao",
        "produto_nome",
    ):
        val = row.get(key)
        if val is not None and str(val).strip():
            name = str(val).strip()
            # ignora placeholder gerado anteriormente
            if codigo and name == f"Produto {codigo}":
                continue
            return name
    return ""


def _abastecimento_id(row: dict[str, Any]) -> str:
    for key in ("abastecimentoCodigo", "codigo", "vendaItemCodigo", "stringFull"):
        val = row.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return (
        f"{row.get('empresaCodigo')}-"
        f"{row.get('dataHoraAbastecimento') or row.get('dataFiscal')}-"
        f"{row.get('codigoBico')}-"
        f"{row.get('quantidade')}-"
        f"{row.get('valorTotal')}"
    )


class DataSyncService:
    """Consolida D-1 (ou período) no SQLite/Postgres local + autodiscovery."""

    def __init__(self) -> None:
        self._abastecimento = AbastecimentoService(get_webposto_client())
        self._integration = get_webposto_integration_service()
        # Cache por empresa durante backfill (TANQUE/CPM não mudam a cada dia)
        self._catalog_cache: dict[int, dict[str, str]] = {}
        self._cpm_cache: dict[int, dict[str, float]] = {}

    async def sync_day(
        self,
        empresa_codigo: int,
        data_referencia: date,
    ) -> dict[str, Any]:
        day = data_referencia.isoformat()
        rows = await self._fetch_abastecimentos(empresa_codigo, day, day)
        if empresa_codigo in self._catalog_cache:
            products_seen = dict(self._catalog_cache[empresa_codigo])
        else:
            products_seen = await self._enrich_from_catalog_and_tanks(empresa_codigo)

        by_product: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "nome": "",
                "litros": 0.0,
                "faturamento": 0.0,
                "ids": set(),
                "ultima": None,
            }
        )

        for row in rows:
            codigo = _product_code(row)
            if not codigo:
                continue
            nome = _product_name(row, codigo)
            litros = _f(
                row.get("quantidade")
                or row.get("quantidadeLitros")
                or row.get("litros")
            )
            valor = _f(
                row.get("valorTotal")
                or row.get("valorVenda")
                or row.get("valor")
            )
            bucket = by_product[codigo]
            resolved_nome = (
                nome
                or products_seen.get(codigo)
                or bucket["nome"]
                or f"Produto {codigo}"
            )
            if not bucket["nome"] or (
                nome and (not bucket["nome"].startswith("Produto ") or len(nome) > len(bucket["nome"]))
            ):
                bucket["nome"] = resolved_nome
            bucket["litros"] += litros
            bucket["faturamento"] += valor
            bucket["ids"].add(_abastecimento_id(row))
            ts = row.get("dataHoraAbastecimento") or row.get("dataFiscal") or day
            bucket["ultima"] = str(ts)
            # Nunca sobrescrever nome bom do tanque com placeholder
            if nome:
                products_seen[codigo] = nome
            elif codigo not in products_seen:
                products_seen[codigo] = f"Produto {codigo}"

        # Atualiza cache com nomes resolvidos (tanque + vendas)
        self._catalog_cache[empresa_codigo] = dict(products_seen)

        if empresa_codigo in self._cpm_cache:
            cpm_map = self._cpm_cache[empresa_codigo]
        else:
            cpm_map = await self._cpm_map(empresa_codigo)
            self._cpm_cache[empresa_codigo] = cpm_map
        now = datetime.now(timezone.utc)

        # Preferir nome do tanque/venda real sobre placeholder
        for codigo, agg in by_product.items():
            if agg["nome"] and not str(agg["nome"]).startswith("Produto "):
                products_seen[codigo] = agg["nome"]
            elif codigo not in products_seen:
                products_seen[codigo] = agg["nome"] or f"Produto {codigo}"
        # Reaplica catálogo de tanques (fonte de verdade para nomes/aditivados)
        for codigo, nome_cat in (self._catalog_cache.get(empresa_codigo) or {}).items():
            if nome_cat and not str(nome_cat).startswith("Produto "):
                products_seen[codigo] = nome_cat
        self._catalog_cache[empresa_codigo] = {
            **(self._catalog_cache.get(empresa_codigo) or {}),
            **{
                k: v
                for k, v in products_seen.items()
                if v and not str(v).startswith("Produto ")
            },
        }

        async with AsyncSessionLocal() as session:
            products_upserted = 0
            for codigo, nome in products_seen.items():
                categoria, is_aditivado = classify_product(nome)
                ultima = None
                if codigo in by_product and by_product[codigo]["ultima"]:
                    try:
                        raw_ts = by_product[codigo]["ultima"]
                        ultima = datetime.fromisoformat(
                            str(raw_ts).replace("Z", "+00:00")
                        )
                    except ValueError:
                        ultima = datetime.combine(
                            data_referencia, datetime.min.time(), tzinfo=timezone.utc
                        )
                await self._upsert_product(
                    session,
                    empresa_codigo=empresa_codigo,
                    codigo=codigo,
                    nome=nome,
                    categoria=categoria,
                    is_aditivado=is_aditivado,
                    ultima_venda_em=ultima,
                    now=now,
                )
                products_upserted += 1

            summaries = 0
            for codigo, agg in by_product.items():
                nome = agg["nome"] or products_seen.get(codigo) or f"Produto {codigo}"
                categoria, _ = classify_product(nome)
                litros = round(float(agg["litros"]), 2)
                fat = round(float(agg["faturamento"]), 2)
                qtd = len(agg["ids"])
                cpm = float(cpm_map.get(codigo) or cpm_map.get(categoria) or 0.0)
                if cpm <= 0:
                    # fallback por família
                    for key, val in cpm_map.items():
                        if key.startswith(categoria[:4]) or categoria in key:
                            cpm = float(val)
                            break
                margem = round(fat - (litros * cpm), 2) if cpm > 0 else 0.0
                await self._upsert_summary(
                    session,
                    empresa_codigo=empresa_codigo,
                    data_referencia=data_referencia,
                    codigo=codigo,
                    nome=nome,
                    categoria=categoria,
                    litros=litros,
                    faturamento=fat,
                    qtd=qtd,
                    cpm=cpm,
                    margem=margem,
                    now=now,
                )
                summaries += 1

            await session.commit()

        result = {
            "empresa_codigo": empresa_codigo,
            "empresa_nome": FILIAL_NAMES.get(empresa_codigo, str(empresa_codigo)),
            "data_referencia": day,
            "abastecimentos_lidos": len(rows),
            "produtos_descobertos": products_upserted,
            "linhas_summary": summaries,
            "litros": round(sum(a["litros"] for a in by_product.values()), 2),
            "faturamento": round(sum(a["faturamento"] for a in by_product.values()), 2),
            "quantidade_abastecimentos": sum(len(a["ids"]) for a in by_product.values()),
        }
        logger.info("DataSync dia ok: %s", result)
        return result

    async def sync_yesterday(
        self,
        empresas: list[int] | None = None,
    ) -> dict[str, Any]:
        """Job noturno 03:00 — consolida D-1."""
        target = date.today() - timedelta(days=1)
        codes = empresas or list(OFFICIAL_COMPANY_CODES)
        results = []
        for code in codes:
            try:
                results.append(await self.sync_day(int(code), target))
            except Exception as exc:
                logger.exception("DataSync D-1 falhou empresa=%s: %s", code, exc)
                results.append(
                    {
                        "empresa_codigo": code,
                        "data_referencia": target.isoformat(),
                        "erro": str(exc),
                    }
                )
        return {
            "data_referencia": target.isoformat(),
            "filiais": results,
            "success": all("erro" not in r for r in results),
        }

    async def backfill(
        self,
        days: int = 90,
        empresas: list[int] | None = None,
        progress_cb: Any | None = None,
    ) -> dict[str, Any]:
        codes = empresas or list(OFFICIAL_COMPANY_CODES)
        end = date.today() - timedelta(days=1)
        start = end - timedelta(days=days - 1)
        total_days = (end - start).days + 1
        day_results: list[dict[str, Any]] = []
        errors = 0

        # Pré-aquece catálogo de tanques (rede) — nomes reais / aditivados
        network_catalog: dict[str, str] = {}
        for code in codes:
            local = await self._enrich_from_catalog_and_tanks(int(code))
            network_catalog.update({k: v for k, v in local.items() if v and not v.startswith("Produto ")})
            self._catalog_cache[int(code)] = {**network_catalog, **local}
            self._cpm_cache[int(code)] = await self._cpm_map(int(code))

        current = start
        idx = 0
        while current <= end:
            idx += 1
            for code in codes:
                try:
                    res = await self.sync_day(int(code), current)
                    day_results.append(res)
                    if progress_cb:
                        progress_cb(idx, total_days, code, res)
                except Exception as exc:
                    errors += 1
                    err = {
                        "empresa_codigo": code,
                        "data_referencia": current.isoformat(),
                        "erro": str(exc),
                    }
                    day_results.append(err)
                    if progress_cb:
                        progress_cb(idx, total_days, code, err)
                    logger.exception(
                        "Backfill falhou empresa=%s dia=%s: %s", code, current, exc
                    )
            current += timedelta(days=1)

        products = await self.list_discovered_products(codes)
        return {
            "periodo": {"inicio": start.isoformat(), "fim": end.isoformat()},
            "dias": total_days,
            "empresas": codes,
            "erros": errors,
            "produtos": products,
            "totais": {
                "litros": round(
                    sum(float(r.get("litros") or 0) for r in day_results), 2
                ),
                "faturamento": round(
                    sum(float(r.get("faturamento") or 0) for r in day_results), 2
                ),
                "abastecimentos": sum(
                    int(r.get("quantidade_abastecimentos") or 0) for r in day_results
                ),
            },
        }

    async def list_discovered_products(
        self, empresas: list[int] | None = None
    ) -> list[dict[str, Any]]:
        codes = empresas or list(OFFICIAL_COMPANY_CODES)
        async with AsyncSessionLocal() as session:
            stmt = select(CompanyProductModel).where(
                col(CompanyProductModel.empresa_codigo).in_(codes)
            )
            rows = (await session.execute(stmt)).scalars().all()
            return [
                {
                    "empresa_codigo": r.empresa_codigo,
                    "empresa_nome": FILIAL_NAMES.get(r.empresa_codigo, ""),
                    "codigo_produto_webposto": r.codigo_produto_webposto,
                    "nome_produto": r.nome_produto,
                    "categoria": r.categoria,
                    "is_aditivado": r.is_aditivado,
                    "ativo": r.ativo,
                    "ultima_venda_em": (
                        r.ultima_venda_em.isoformat() if r.ultima_venda_em else None
                    ),
                }
                for r in rows
            ]

    async def _fetch_abastecimentos(
        self, empresa_codigo: int, start: str, end: str
    ) -> list[dict[str, Any]]:
        resp = await self._abastecimento.get_periodo(
            start, end, empresa_codigo=empresa_codigo
        )
        if not resp.success:
            logger.warning(
                "ABASTECIMENTO sync falhou empresa=%s: %s",
                empresa_codigo,
                resp.error,
            )
            return []
        raw = resp.data
        if isinstance(raw, dict):
            rows = raw.get("dados") or raw.get("resultados") or raw.get("data") or []
        elif isinstance(raw, list):
            rows = raw
        else:
            rows = []
        return [
            r
            for r in rows
            if isinstance(r, dict)
            and int(r.get("empresaCodigo") or r.get("empresa") or 0)
            == int(empresa_codigo)
        ]

    async def _enrich_from_catalog_and_tanks(
        self, empresa_codigo: int
    ) -> dict[str, str]:
        """PRODUTO_COMBUSTIVEL + TANQUE — novos SKUs mesmo sem venda no dia."""
        discovered: dict[str, str] = {}
        client = self._integration._client_for_company(empresa_codigo)

        try:
            resp = await client.call_endpoint(
                "produto_combustivel",
                params={"empresaCodigo": empresa_codigo},
            )
            if resp.success:
                raw = resp.data
                rows = []
                if isinstance(raw, dict):
                    rows = (
                        raw.get("resultados")
                        or raw.get("dados")
                        or raw.get("data")
                        or []
                    )
                elif isinstance(raw, list):
                    rows = raw
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    codigo = _product_code(row)
                    if codigo:
                        discovered[codigo] = _product_name(row, codigo)
        except Exception as exc:
            logger.info(
                "produto_combustivel indisponível empresa=%s: %s",
                empresa_codigo,
                exc,
            )

        try:
            tanks = await self._integration.get_tank_levels(empresa_codigo)
            for t in tanks.tanques or []:
                codigo = str(
                    t.get("produto_codigo") or t.get("produtoCodigo") or ""
                ).strip()
                nome = _product_name(t, codigo) or str(
                    t.get("produto_nome") or t.get("produtoDescricao") or ""
                ).strip()
                if codigo and nome:
                    discovered[codigo] = nome
                elif codigo and codigo not in discovered:
                    discovered[codigo] = f"Produto {codigo}"
        except Exception as exc:
            logger.info("tanque sync skip empresa=%s: %s", empresa_codigo, exc)

        return discovered

    async def _cpm_map(self, empresa_codigo: int) -> dict[str, float]:
        mapping: dict[str, float] = {}
        try:
            costs = await self._integration.get_weighted_avg_cost(empresa_codigo)
            for item in costs.custos or []:
                codigo = str(item.get("produto_codigo") or "")
                cpm = _f(item.get("cpm_rs"))
                if codigo and cpm > 0:
                    mapping[codigo] = cpm
                    # alias por categoria do nome
                    cat, _ = classify_product(str(item.get("produto_nome") or codigo))
                    mapping.setdefault(cat, cpm)
        except Exception as exc:
            logger.warning("CPM sync empresa=%s: %s", empresa_codigo, exc)
        return mapping

    async def _upsert_product(
        self,
        session: Any,
        *,
        empresa_codigo: int,
        codigo: str,
        nome: str,
        categoria: str,
        is_aditivado: bool,
        ultima_venda_em: datetime | None,
        now: datetime,
    ) -> None:
        stmt = select(CompanyProductModel).where(
            CompanyProductModel.empresa_codigo == empresa_codigo,
            CompanyProductModel.codigo_produto_webposto == codigo,
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            # Nunca sobrescrever nome real com placeholder "Produto {codigo}"
            final_nome = existing.nome_produto or nome
            if nome and not str(nome).startswith("Produto "):
                final_nome = nome
            elif (not final_nome or str(final_nome).startswith("Produto ")) and nome:
                final_nome = nome

            final_cat = existing.categoria or categoria
            if categoria and categoria != "OUTROS":
                final_cat = categoria
            elif not final_cat or final_cat == "OUTROS":
                final_cat = categoria or "OUTROS"

            final_ultima = existing.ultima_venda_em
            if ultima_venda_em and (
                final_ultima is None or _aware(ultima_venda_em) > _aware(final_ultima)
            ):
                final_ultima = ultima_venda_em
            await session.execute(
                update(CompanyProductModel)
                .where(CompanyProductModel.id == existing.id)
                .values(
                    nome_produto=final_nome,
                    categoria=final_cat,
                    is_aditivado=bool(is_aditivado or existing.is_aditivado),
                    ativo=True,
                    ultima_venda_em=final_ultima,
                    updated_at=now,
                )
            )
        else:
            session.add(
                CompanyProductModel(
                    empresa_codigo=empresa_codigo,
                    codigo_produto_webposto=codigo,
                    nome_produto=nome,
                    categoria=categoria,
                    is_aditivado=is_aditivado,
                    ativo=True,
                    ultima_venda_em=ultima_venda_em,
                    created_at=now,
                    updated_at=now,
                )
            )

    async def _upsert_summary(
        self,
        session: Any,
        *,
        empresa_codigo: int,
        data_referencia: date,
        codigo: str,
        nome: str,
        categoria: str,
        litros: float,
        faturamento: float,
        qtd: int,
        cpm: float,
        margem: float,
        now: datetime,
    ) -> None:
        stmt = select(SalesDailySummaryModel).where(
            SalesDailySummaryModel.empresa_codigo == empresa_codigo,
            SalesDailySummaryModel.data_referencia == data_referencia,
            SalesDailySummaryModel.codigo_produto_webposto == codigo,
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.nome_produto = nome
            existing.categoria = categoria
            existing.litros_vendidos = litros
            existing.faturamento_bruto = faturamento
            existing.quantidade_abastecimentos = qtd
            existing.custo_medio_ponderado = round(cpm, 4)
            existing.margem_bruta_real = margem
            existing.synced_at = now
        else:
            session.add(
                SalesDailySummaryModel(
                    empresa_codigo=empresa_codigo,
                    data_referencia=data_referencia,
                    codigo_produto_webposto=codigo,
                    nome_produto=nome,
                    categoria=categoria,
                    litros_vendidos=litros,
                    faturamento_bruto=faturamento,
                    quantidade_abastecimentos=qtd,
                    custo_medio_ponderado=round(cpm, 4),
                    margem_bruta_real=margem,
                    synced_at=now,
                )
            )


_data_sync: DataSyncService | None = None


def get_data_sync_service() -> DataSyncService:
    global _data_sync
    if _data_sync is None:
        _data_sync = DataSyncService()
    return _data_sync
