from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.crud_entities import GrupoRecord, ProdutoRecord, SubgrupoRecord
from src.infrastructure.cache import CacheManager


class ImmutableProductPayload(BaseModel):
    """Validated immutable payload used by the sync pipeline."""

    sku: Optional[str] = None
    nome: str
    grupo: str
    subgrupo: str
    preco_venda: Decimal = Decimal("0.00")
    preco_custo: Decimal = Decimal("0.00")
    ativo: bool = True

    model_config = ConfigDict(frozen=True)

    @field_validator("nome", "grupo", "subgrupo")
    @classmethod
    def _validate_required_name(cls, value: str) -> str:
        clean = (value or "").strip()
        if not clean:
            raise ValueError("string field must be non-empty")
        return clean

    @field_validator("sku")
    @classmethod
    def _normalize_sku(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        clean = value.strip()
        return clean or None

    @field_validator("preco_venda", "preco_custo", mode="before")
    @classmethod
    def _parse_decimal(cls, value: Any) -> Decimal:
        if value is None or value == "":
            parsed = Decimal("0.00")
        else:
            try:
                parsed = Decimal(str(value))
            except (InvalidOperation, ValueError) as exc:
                raise ValueError("invalid decimal") from exc
        if not parsed.is_finite():
            raise ValueError("decimal must be finite")
        return parsed.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class SyncProductsUseCase:
    def __init__(self, db_session: AsyncSession, cache: CacheManager):
        self.db = db_session
        self.cache = cache

    async def execute(self, posto_id: str, catalog: Dict[str, Any], force_refresh: bool = False) -> Dict[str, Any]:
        raw_items = catalog.get("items") if isinstance(catalog, dict) else None
        if not isinstance(raw_items, list):
            raise ValueError("catalog.items must be a list")

        items = [self._to_payload(item) for item in raw_items]

        counters = {
            "grupos_inseridos": 0,
            "grupos_atualizados": 0,
            "subgrupos_inseridos": 0,
            "subgrupos_atualizados": 0,
            "produtos_inseridos": 0,
            "produtos_atualizados": 0,
        }

        async with self.db.begin():
            for item in items:
                grupo, grupo_inserted = await self._upsert_grupo(item.grupo)
                subgrupo, subgrupo_inserted = await self._upsert_subgrupo(grupo.id, item.subgrupo)
                _, produto_inserted = await self._upsert_produto(subgrupo.id, item)

                counters["grupos_inseridos" if grupo_inserted else "grupos_atualizados"] += 1
                counters["subgrupos_inseridos" if subgrupo_inserted else "subgrupos_atualizados"] += 1
                counters["produtos_inseridos" if produto_inserted else "produtos_atualizados"] += 1

        if force_refresh:
            self.cache.invalidate(namespace="products_catalog")

        return {
            "posto_id": posto_id,
            "total_recebidos": len(items),
            **counters,
        }

    @staticmethod
    def _to_payload(item: Any) -> ImmutableProductPayload:
        if not isinstance(item, dict):
            raise ValueError("each product payload must be an object")
        return ImmutableProductPayload(
            sku=item.get("sku") or item.get("codigo"),
            nome=item.get("nome") or item.get("descricao"),
            grupo=item.get("grupo") or "Sem Grupo",
            subgrupo=item.get("subgrupo") or "Sem Subgrupo",
            preco_venda=item.get("preco_venda") or item.get("preco") or 0,
            preco_custo=item.get("preco_custo") or 0,
            ativo=bool(item.get("ativo", True)),
        )

    async def _upsert_grupo(self, nome: str) -> Tuple[GrupoRecord, bool]:
        stmt = select(GrupoRecord).where(GrupoRecord.nome == nome)
        result = await self.db.execute(stmt)
        record = result.scalar_one_or_none()
        if record is None:
            record = GrupoRecord(nome=nome, ativo=True)
            self.db.add(record)
            await self.db.flush()
            return record, True

        record.ativo = True
        await self.db.flush()
        return record, False

    async def _upsert_subgrupo(self, grupo_id: int, nome: str) -> Tuple[SubgrupoRecord, bool]:
        grupo_stmt = select(GrupoRecord).where(GrupoRecord.id == grupo_id)
        grupo_result = await self.db.execute(grupo_stmt)
        if grupo_result.scalar_one_or_none() is None:
            raise ValueError("referential integrity failed: grupo not found")

        stmt = select(SubgrupoRecord).where(
            SubgrupoRecord.grupo_id == grupo_id,
            SubgrupoRecord.nome == nome,
        )
        result = await self.db.execute(stmt)
        record = result.scalar_one_or_none()
        if record is None:
            record = SubgrupoRecord(grupo_id=grupo_id, nome=nome, ativo=True)
            self.db.add(record)
            await self.db.flush()
            return record, True

        record.ativo = True
        await self.db.flush()
        return record, False

    async def _upsert_produto(self, subgrupo_id: int, item: ImmutableProductPayload) -> Tuple[ProdutoRecord, bool]:
        subgrupo_stmt = select(SubgrupoRecord).where(SubgrupoRecord.id == subgrupo_id)
        subgrupo_result = await self.db.execute(subgrupo_stmt)
        if subgrupo_result.scalar_one_or_none() is None:
            raise ValueError("referential integrity failed: subgrupo not found")

        record: Optional[ProdutoRecord] = None
        if item.sku:
            stmt = select(ProdutoRecord).where(ProdutoRecord.sku == item.sku)
            result = await self.db.execute(stmt)
            record = result.scalar_one_or_none()

        if record is None:
            stmt = select(ProdutoRecord).where(
                ProdutoRecord.subgrupo_id == subgrupo_id,
                ProdutoRecord.nome == item.nome,
            )
            result = await self.db.execute(stmt)
            record = result.scalar_one_or_none()

        if record is None:
            record = ProdutoRecord(
                subgrupo_id=subgrupo_id,
                sku=item.sku,
                nome=item.nome,
                preco=item.preco_venda,
                preco_custo=item.preco_custo,
                ativo=item.ativo,
            )
            self.db.add(record)
            await self.db.flush()
            return record, True

        record.subgrupo_id = subgrupo_id
        record.sku = item.sku
        record.nome = item.nome
        record.preco = item.preco_venda
        record.preco_custo = item.preco_custo
        record.ativo = item.ativo
        await self.db.flush()
        return record, False
