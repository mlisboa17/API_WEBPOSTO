"""
AuditoriaRepository - Specialized repository for Audit operations
Integrates with WebPosto_API DDD architecture
Uses MongoDB async driver with proper async/await patterns
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from pydantic import ValidationError
import logging

from src.shared.repository import BaseRepository
from src.domain.models.auditoria_models import (
    DespesaCaixa,
    FechamentoCaixa,
    ResumoAuditoriaUnidade,
    StatusJustificativa,
    StatusCaixa,
)

logger = logging.getLogger(__name__)


class AuditoriaRepository(BaseRepository):
    """
    Repository for audit-specific operations
    Handles despesas (expenses), fechamentos (closures), and audit insights

    Inherits from BaseRepository for consistency with WebPosto_API patterns
    Uses motor (async MongoDB driver) for async operations
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize AuditoriaRepository with MongoDB database connection

        Args:
            db: AsyncIOMotorDatabase instance from WebPosto_API infrastructure
        """
        super().__init__(db)
        self.despesas_collection: AsyncIOMotorCollection = db["despesas_auditoria"]
        self.fechamentos_collection: AsyncIOMotorCollection = db[
            "fechamentos_auditoria"
        ]
        self.auditoria_insights_collection: AsyncIOMotorCollection = db[
            "auditoria_insights"
        ]

        self._ensure_indexes()

    def _ensure_indexes(self):
        """Create required indexes for optimal query performance"""
        try:
            # Despesas indexes
            self.despesas_collection.create_index(
                [("unidade_id", ASCENDING), ("horario", DESCENDING)],
                name="idx_despesas_unidade_horario",
            )
            self.despesas_collection.create_index(
                [("status_justificativa", ASCENDING)], name="idx_despesas_status"
            )

            # Fechamentos indexes
            self.fechamentos_collection.create_index(
                [("unidade_id", ASCENDING), ("horario_fechamento", DESCENDING)],
                name="idx_fechamentos_unidade_data",
            )
            self.fechamentos_collection.create_index(
                [("status", ASCENDING)], name="idx_fechamentos_status"
            )
            self.fechamentos_collection.create_index(
                [("flagged_auditoria", ASCENDING)], name="idx_fechamentos_flagged"
            )

            # Insights indexes
            self.auditoria_insights_collection.create_index(
                [("unidade_id", ASCENDING), ("data", DESCENDING)],
                name="idx_insights_unidade_data",
            )
        except Exception as e:
            logger.warning(f"Could not create indexes: {e}")

    # ============ DESPESAS OPERATIONS ============

    async def get_despesas_by_unidade(
        self,
        unidade_id: str,
        data_inicio: datetime,
        data_fim: datetime,
        status_justificativa: Optional[StatusJustificativa] = None,
    ) -> List[DespesaCaixa]:
        """
        Retrieve expenses for a unit within a date range

        Args:
            unidade_id: Unit identifier (Real, Casa Caiada, VIP)
            data_inicio: Start date for filtering
            data_fim: End date for filtering
            status_justificativa: Optional filter by justification status

        Returns:
            List of DespesaCaixa validated models

        Raises:
            ValidationError: If documents don't match Pydantic schema
        """
        try:
            query = {
                "unidade_id": unidade_id,
                "horario": {
                    "$gte": data_inicio,
                    "$lte": data_fim,
                },
            }

            if status_justificativa:
                query["status_justificativa"] = status_justificativa.value

            documents = (
                await self.despesas_collection.find(query)
                .sort("horario", DESCENDING)
                .to_list(None)
            )

            despesas = []
            for doc in documents:
                # Remove MongoDB _id field for Pydantic validation
                doc.pop("_id", None)
                try:
                    despesa = DespesaCaixa(**doc)
                    despesas.append(despesa)
                except ValidationError as ve:
                    logger.error(f"Validation error for despesa {doc.get('id')}: {ve}")
                    continue

            logger.info(
                f"Retrieved {len(despesas)} despesas for {unidade_id} "
                f"between {data_inicio} and {data_fim}"
            )
            return despesas

        except Exception as e:
            logger.error(f"Error retrieving despesas: {e}")
            raise

    async def create_despesa(self, despesa: DespesaCaixa) -> DespesaCaixa:
        """
        Create a new expense record

        Args:
            despesa: DespesaCaixa model instance

        Returns:
            The created DespesaCaixa with confirmed ID
        """
        try:
            doc = despesa.model_dump(mode="json")
            doc["_id"] = despesa.id
            doc["created_at"] = datetime.utcnow()

            result = await self.despesas_collection.insert_one(doc)
            logger.info(f"Created despesa: {result.inserted_id}")

            return despesa
        except Exception as e:
            logger.error(f"Error creating despesa: {e}")
            raise

    async def update_despesa_status(
        self,
        despesa_id: str,
        novo_status: StatusJustificativa,
        motivo: Optional[str] = None,
    ) -> bool:
        """
        Update expense justification status

        Args:
            despesa_id: Expense ID
            novo_status: New justification status
            motivo: Optional reason for status change

        Returns:
            True if update was successful
        """
        try:
            update_data = {
                "status_justificativa": novo_status.value,
                "updated_at": datetime.utcnow(),
            }
            if motivo:
                update_data["motivo_status"] = motivo

            result = await self.despesas_collection.update_one(
                {"_id": despesa_id}, {"$set": update_data}
            )

            success = result.modified_count > 0
            if success:
                logger.info(
                    f"Updated despesa {despesa_id} status to {novo_status.value}"
                )

            return success
        except Exception as e:
            logger.error(f"Error updating despesa status: {e}")
            raise

    # ============ FECHAMENTOS OPERATIONS ============

    async def get_fechamentos_consolidated(
        self,
        unidade_id: str,
        data: datetime,
    ) -> List[FechamentoCaixa]:
        """
        Retrieve consolidated cash closures for a specific date

        Args:
            unidade_id: Unit identifier
            data: Date to retrieve closures for

        Returns:
            List of FechamentoCaixa models with all details
        """
        try:
            # Create date range for the day
            data_inicio = datetime.combine(data.date(), datetime.min.time())
            data_fim = datetime.combine(data.date(), datetime.max.time())

            query = {
                "unidade_id": unidade_id,
                "horario_fechamento": {
                    "$gte": data_inicio,
                    "$lte": data_fim,
                },
            }

            documents = (
                await self.fechamentos_collection.find(query)
                .sort("horario_fechamento", DESCENDING)
                .to_list(None)
            )

            fechamentos = []
            for doc in documents:
                doc.pop("_id", None)
                try:
                    fechamento = FechamentoCaixa(**doc)
                    fechamentos.append(fechamento)
                except ValidationError as ve:
                    logger.error(
                        f"Validation error for fechamento {doc.get('id')}: {ve}"
                    )
                    continue

            logger.info(
                f"Retrieved {len(fechamentos)} fechamentos for {unidade_id} on {data.date()}"
            )
            return fechamentos

        except Exception as e:
            logger.error(f"Error retrieving fechamentos: {e}")
            raise

    async def create_fechamento(self, fechamento: FechamentoCaixa) -> FechamentoCaixa:
        """
        Create a new cash closure record

        Args:
            fechamento: FechamentoCaixa model instance

        Returns:
            The created FechamentoCaixa with confirmed ID
        """
        try:
            doc = fechamento.model_dump(mode="json")
            doc["_id"] = fechamento.id
            doc["created_at"] = datetime.utcnow()

            result = await self.fechamentos_collection.insert_one(doc)
            logger.info(f"Created fechamento: {result.inserted_id}")

            return fechamento
        except Exception as e:
            logger.error(f"Error creating fechamento: {e}")
            raise

    async def update_fechamento_status(
        self,
        fechamento_id: str,
        novo_status: StatusCaixa,
    ) -> bool:
        """
        Update cash closure status

        Args:
            fechamento_id: Closure ID
            novo_status: New status

        Returns:
            True if update was successful
        """
        try:
            result = await self.fechamentos_collection.update_one(
                {"_id": fechamento_id},
                {
                    "$set": {
                        "status": novo_status.value,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )

            success = result.modified_count > 0
            if success:
                logger.info(
                    f"Updated fechamento {fechamento_id} status to {novo_status.value}"
                )

            return success
        except Exception as e:
            logger.error(f"Error updating fechamento status: {e}")
            raise

    async def flag_fechamento_for_audit(
        self,
        fechamento_id: str,
        motivo: str,
    ) -> bool:
        """
        Mark a closure for manual audit review

        Args:
            fechamento_id: Closure ID
            motivo: Reason for audit flag

        Returns:
            True if flag was set successfully
        """
        try:
            result = await self.fechamentos_collection.update_one(
                {"_id": fechamento_id},
                {
                    "$set": {
                        "flagged_auditoria": True,
                        "motivo_auditoria": motivo,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )

            success = result.modified_count > 0
            if success:
                logger.info(f"Flagged fechamento {fechamento_id} for audit: {motivo}")

            return success
        except Exception as e:
            logger.error(f"Error flagging fechamento for audit: {e}")
            raise

    # ============ AUDIT INSIGHTS OPERATIONS ============

    async def calculate_auditoria_insights(
        self,
        data_inicio: datetime,
        data_fim: datetime,
        unidade_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Calculate comprehensive audit insights and anomaly detection

        Uses aggregation pipeline for efficient computation
        Identifies:
        - Cash breaks above threshold
        - Expenses without documentation
        - Outlier expenses by category
        - Unusual patterns vs historical average

        Args:
            data_inicio: Start date for analysis
            data_fim: End date for analysis
            unidade_id: Optional filter by specific unit

        Returns:
            List of insight dictionaries with metrics and severity
        """
        try:
            # Build match stage
            match_stage = {
                "horario_fechamento": {
                    "$gte": data_inicio,
                    "$lte": data_fim,
                }
            }
            if unidade_id:
                match_stage["unidade_id"] = unidade_id

            # Aggregation pipeline for complex analytics
            pipeline = [
                {"$match": match_stage},
                {
                    "$group": {
                        "_id": "$unidade_id",
                        "total_fechamentos": {"$sum": 1},
                        "faturamento_total": {"$sum": "$faturamento_bruto"},
                        "despesas_total": {"$sum": "$despesas_caixa_total"},
                        "quebra_total": {"$sum": "$quebra_caixa"},
                        "caixas_em_auditoria": {
                            "$sum": {"$cond": ["$flagged_auditoria", 1, 0]}
                        },
                        "avg_quebra": {"$avg": "$quebra_caixa"},
                        "max_quebra": {"$max": "$quebra_caixa"},
                        "despesas_sem_doc_total": {"$sum": "$despesas_sem_documento"},
                    }
                },
                {
                    "$project": {
                        "unidade_id": "$_id",
                        "total_fechamentos": 1,
                        "faturamento_total": 1,
                        "despesas_total": 1,
                        "taxa_despesas": {
                            "$cond": [
                                {"$gt": ["$faturamento_total", 0]},
                                {
                                    "$multiply": [
                                        {
                                            "$divide": [
                                                "$despesas_total",
                                                "$faturamento_total",
                                            ]
                                        },
                                        100,
                                    ]
                                },
                                0,
                            ]
                        },
                        "quebra_total": 1,
                        "quebra_percentual": {
                            "$cond": [
                                {"$gt": ["$faturamento_total", 0]},
                                {
                                    "$multiply": [
                                        {
                                            "$divide": [
                                                "$quebra_total",
                                                "$faturamento_total",
                                            ]
                                        },
                                        100,
                                    ]
                                },
                                0,
                            ]
                        },
                        "caixas_em_auditoria": 1,
                        "avg_quebra": 1,
                        "max_quebra": 1,
                        "despesas_sem_doc_total": 1,
                    }
                },
            ]

            results = await self.fechamentos_collection.aggregate(pipeline).to_list(
                None
            )

            # Transform aggregation results into audit insights
            insights = []
            for result in results:
                unidade_id = result.get("unidade_id")

                # Insight 1: Cash break anomalies
                if result.get("max_quebra", 0) > 10:
                    insights.append(
                        {
                            "unidade_id": unidade_id,
                            "tipo": "quebra_caixa",
                            "severidade": (
                                "crítico" if result["max_quebra"] > 50 else "warning"
                            ),
                            "mensagem": f"Maior quebra de R$ {result['max_quebra']:.2f}",
                            "valor": result["max_quebra"],
                            "data_calculo": datetime.utcnow(),
                        }
                    )

                # Insight 2: High expense ratio
                taxa_despesas = result.get("taxa_despesas", 0)
                if taxa_despesas > 10:
                    insights.append(
                        {
                            "unidade_id": unidade_id,
                            "tipo": "taxa_despesas_alta",
                            "severidade": "warning",
                            "mensagem": f"Taxa de despesas {taxa_despesas:.1f}% (esperado: ~5%)",
                            "valor": taxa_despesas,
                            "data_calculo": datetime.utcnow(),
                        }
                    )

                # Insight 3: Expenses without documentation
                if result.get("despesas_sem_doc_total", 0) > 0:
                    insights.append(
                        {
                            "unidade_id": unidade_id,
                            "tipo": "despesas_sem_documento",
                            "severidade": "info",
                            "mensagem": f"{result['despesas_sem_doc_total']} despesa(s) sem documentação",
                            "valor": result["despesas_sem_doc_total"],
                            "data_calculo": datetime.utcnow(),
                        }
                    )

            logger.info(
                f"Calculated {len(insights)} audit insights for period {data_inicio} to {data_fim}"
            )
            return insights

        except Exception as e:
            logger.error(f"Error calculating audit insights: {e}")
            raise

    async def get_auditoria_resumo_unidade(
        self,
        unidade_id: str,
        data: datetime,
    ) -> Optional[ResumoAuditoriaUnidade]:
        """
        Get consolidated audit summary for a unit on a specific date

        Combines all despesas and fechamentos data for executive view

        Args:
            unidade_id: Unit identifier
            data: Date to summarize

        Returns:
            ResumoAuditoriaUnidade model or None if no data found
        """
        try:
            # Get all closures for the date
            fechamentos = await self.get_fechamentos_consolidated(unidade_id, data)

            # Get all expenses for the date
            data_inicio = datetime.combine(data.date(), datetime.min.time())
            data_fim = datetime.combine(data.date(), datetime.max.time())
            despesas = await self.get_despesas_by_unidade(
                unidade_id, data_inicio, data_fim
            )

            if not fechamentos:
                logger.warning(
                    f"No fechamentos found for {unidade_id} on {data.date()}"
                )
                return None

            # Calculate aggregates
            faturamento_total = sum(f.faturamento_bruto for f in fechamentos)
            despesas_operacionais = sum(f.despesas_caixa_total for f in fechamentos)
            quebra_total = sum(f.quebra_caixa for f in fechamentos)
            saldo_especie_total = sum(f.saldo_informado_dinheiro for f in fechamentos)

            caixas_fechados = len(
                [f for f in fechamentos if f.status == StatusCaixa.FECHADO]
            )
            caixas_abertos = len(
                [f for f in fechamentos if f.status == StatusCaixa.ABERTO]
            )
            caixas_em_auditoria = len(
                [f for f in fechamentos if f.status == StatusCaixa.EM_AUDITORIA]
            )

            despesas_sem_categoria = sum(f.despesas_sem_categoria for f in fechamentos)
            despesas_sem_documento = sum(f.despesas_sem_documento for f in fechamentos)
            caixas_com_quebra_acima_10 = len(
                [f for f in fechamentos if f.quebra_caixa > 10]
            )

            # Calculate deviation from historical 5% expense ratio
            desvio_percentual = 0
            if faturamento_total > 0:
                taxa_despesas = (despesas_operacionais / faturamento_total) * 100
                desvio_percentual = taxa_despesas - 5.0

            resumo = ResumoAuditoriaUnidade(
                unidade_id=unidade_id,
                data=data,
                faturamento_total=round(faturamento_total, 2),
                despesas_operacionais=round(despesas_operacionais, 2),
                saldo_especie_total=round(saldo_especie_total, 2),
                quebra_total=round(quebra_total, 2),
                quebra_percentual=round(
                    (
                        (quebra_total / faturamento_total * 100)
                        if faturamento_total > 0
                        else 0
                    ),
                    2,
                ),
                caixas_fechados=caixas_fechados,
                caixas_abertos=caixas_abertos,
                caixas_em_auditoria=caixas_em_auditoria,
                despesas_sem_categoria_total=despesas_sem_categoria,
                despesas_sem_documento_total=despesas_sem_documento,
                caixas_com_quebra_acima_10=caixas_com_quebra_acima_10,
                desvio_percentual_media_despesas=round(desvio_percentual, 2),
                outlier_unidade=abs(desvio_percentual) > 10,
            )

            logger.info(f"Generated audit summary for {unidade_id} on {data.date()}")
            return resumo

        except Exception as e:
            logger.error(f"Error generating audit summary: {e}")
            raise

    # ============ UTILITY METHODS ============

    async def delete_despesa(self, despesa_id: str) -> bool:
        """
        Delete an expense record (soft delete recommended in production)

        Args:
            despesa_id: Expense ID

        Returns:
            True if deletion was successful
        """
        try:
            result = await self.despesas_collection.delete_one({"_id": despesa_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting despesa: {e}")
            raise

    async def delete_fechamento(self, fechamento_id: str) -> bool:
        """
        Delete a closure record (soft delete recommended in production)

        Args:
            fechamento_id: Closure ID

        Returns:
            True if deletion was successful
        """
        try:
            result = await self.fechamentos_collection.delete_one(
                {"_id": fechamento_id}
            )
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting fechamento: {e}")
            raise

    async def get_total_despesas_by_categoria(
        self,
        unidade_id: str,
        data_inicio: datetime,
        data_fim: datetime,
    ) -> Dict[str, float]:
        """
        Get total expenses by category for auditing purposes

        Args:
            unidade_id: Unit identifier
            data_inicio: Start date
            data_fim: End date

        Returns:
            Dictionary mapping categoria to total value
        """
        try:
            pipeline = [
                {
                    "$match": {
                        "unidade_id": unidade_id,
                        "horario": {
                            "$gte": data_inicio,
                            "$lte": data_fim,
                        },
                    }
                },
                {
                    "$group": {
                        "_id": "$categoria",
                        "total": {"$sum": "$valor"},
                        "qtd": {"$sum": 1},
                    }
                },
                {"$sort": {"total": -1}},
            ]

            results = await self.despesas_collection.aggregate(pipeline).to_list(None)

            return {result["_id"]: result["total"] for result in results}
        except Exception as e:
            logger.error(f"Error calculating despesas by categoria: {e}")
            raise
