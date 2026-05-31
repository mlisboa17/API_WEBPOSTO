from __future__ import annotations

from decimal import Decimal
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.adelaide_engine import TaxMatrix
from src.infrastructure.persistence.postgresql.models import AdelaideTaxMatrixORM


class SqlAlchemyTaxMatrixRepository:
    """Concrete Adelaide matrix repository backed by PostgreSQL."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_matrix(self, uf: str, cnae: str, ncm: str | None) -> TaxMatrix | None:
        if not ncm:
            return None
        stmt = select(AdelaideTaxMatrixORM).where(
            AdelaideTaxMatrixORM.uf == uf,
            AdelaideTaxMatrixORM.cnae == cnae,
            AdelaideTaxMatrixORM.ncm == ncm,
        )
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return TaxMatrix(
            ncm=row.ncm,
            cst=row.cst,
            monofasico=bool(row.monofasico),
            aliquota_pis=Decimal(str(row.aliquota_pis or 0)),
            aliquota_cofins=Decimal(str(row.aliquota_cofins or 0)),
        )

    async def upsert_matrix(
        self,
        uf: str,
        cnae: str,
        ncm: str,
        cst: str,
        monofasico: bool,
        aliquota_pis: Decimal,
        aliquota_cofins: Decimal,
        descricao_referencia: str | None = None,
    ) -> TaxMatrix:
        matrix_id = sha256(f"{uf}:{cnae}:{ncm}".encode("utf-8")).hexdigest()[:32]
        instance = await self.session.get(AdelaideTaxMatrixORM, matrix_id)
        if instance is None:
            instance = AdelaideTaxMatrixORM(matrix_id=matrix_id, uf=uf, cnae=cnae, ncm=ncm)
            self.session.add(instance)

        instance.cst = cst
        instance.monofasico = monofasico
        instance.aliquota_pis = aliquota_pis
        instance.aliquota_cofins = aliquota_cofins
        instance.descricao_referencia = descricao_referencia
        await self.session.commit()
        return TaxMatrix(
            ncm=ncm,
            cst=cst,
            monofasico=monofasico,
            aliquota_pis=aliquota_pis,
            aliquota_cofins=aliquota_cofins,
        )
