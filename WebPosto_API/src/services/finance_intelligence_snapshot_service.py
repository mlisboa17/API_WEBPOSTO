from __future__ import annotations



import asyncio

from datetime import datetime

from typing import Any



from src.services.analytics_multiselect import build_finance_center_filters

from src.services.financial_health_score_service import FinancialHealthScoreService

from src.services.financial_health_score_v3_service import FinancialHealthScoreV3Service

from src.services.financial_intelligence_advanced_service import FinancialIntelligenceAdvancedService

from src.services.financial_intelligence_service import FinancialIntelligenceService

from src.services.supplier_intelligence_service import SupplierIntelligenceService

from src.services.supplier_segmentation_service import SupplierSegmentationService

from src.services.snapshot_store import SnapshotStore



FINANCE_INTELLIGENCE_SNAPSHOT_TTL_SECONDS = 5 * 60





class FinanceIntelligenceSnapshotService:

    def __init__(

        self,

        intelligence: FinancialIntelligenceService,

        health_score: FinancialHealthScoreService,

        advanced: FinancialIntelligenceAdvancedService | None = None,

        health_score_v3: FinancialHealthScoreV3Service | None = None,

        suppliers: SupplierIntelligenceService | None = None,

        segmentation: SupplierSegmentationService | None = None,

        output_dir: str = "snapshots/finance_intelligence",

        ttl_seconds: float = FINANCE_INTELLIGENCE_SNAPSHOT_TTL_SECONDS,

    ) -> None:

        self._intel = intelligence

        self._health = health_score

        self._advanced = advanced

        self._health_v3 = health_score_v3

        self._suppliers = suppliers

        self._segmentation = segmentation

        self._store = SnapshotStore(output_dir, ttl_seconds)

        self._running: set[str] = set()

        self._lock = asyncio.Lock()



    @staticmethod

    def _key(data_inicial: str, data_final: str, empresa_codigo: str | int | None) -> str:

        from src.services.multiselect_utils import empresa_snapshot_suffix



        suffix = empresa_snapshot_suffix(empresa_codigo)

        return f"finance:intelligence:all:{data_inicial}:{data_final}:{suffix}"



    def get_snapshot(

        self,

        data_inicial: str,

        data_final: str,

        empresa_codigo: str | int | None = None,

    ) -> dict[str, Any]:

        stored = self._store.load(self._key(data_inicial, data_final, empresa_codigo))

        if stored:

            return {

                "fromSnapshot": True,

                "lastUpdated": stored.get("lastUpdated"),

                "intelligence": stored.get("intelligence"),

                "healthScore": stored.get("healthScore"),

                "advanced": stored.get("advanced"),

                "healthScoreV3": stored.get("healthScoreV3"),

                "supplierIntelligence": stored.get("supplierIntelligence"),

                "supplierSegmentation": stored.get("supplierSegmentation"),

            }

        return {

            "fromSnapshot": False,

            "lastUpdated": None,

            "intelligence": None,

            "healthScore": None,

            "advanced": None,

            "healthScoreV3": None,

            "supplierIntelligence": None,

            "supplierSegmentation": None,

        }



    async def collect(

        self,

        data_inicial: str,

        data_final: str,

        empresa_codigo: str | int | None = None,

    ) -> dict[str, Any]:

        filters = build_finance_center_filters(data_inicial, data_final, empresa_codigo)

        tasks: list[Any] = [

            self._intel.build(filters, empresa_codigo),

            self._health.build(filters, empresa_codigo),

        ]

        if self._advanced:

            tasks.append(self._advanced.build(filters, empresa_codigo))

        if self._health_v3:

            tasks.append(self._health_v3.build(filters, empresa_codigo))

        if self._suppliers:

            tasks.append(self._suppliers.build(filters, empresa_codigo))

        if self._segmentation:

            tasks.append(self._segmentation.build(filters, empresa_codigo))



        results = await asyncio.gather(*tasks)

        idx = 0

        intel_resp = results[idx]

        idx += 1

        health_resp = results[idx]

        idx += 1

        adv_resp = results[idx] if self._advanced else None

        if self._advanced:

            idx += 1

        hv3_resp = results[idx] if self._health_v3 else None

        if self._health_v3:

            idx += 1

        sup_resp = results[idx] if self._suppliers else None

        if self._suppliers:

            idx += 1

        seg_resp = results[idx] if self._segmentation else None



        payload = {

            "lastUpdated": datetime.now().isoformat(timespec="seconds"),

            "intelligence": intel_resp.data if intel_resp.success else None,

            "healthScore": health_resp.data if health_resp.success else None,

            "advanced": adv_resp.data if adv_resp and adv_resp.success else None,

            "healthScoreV3": hv3_resp.data if hv3_resp and hv3_resp.success else None,

            "supplierIntelligence": sup_resp.data if sup_resp and sup_resp.success else None,

            "supplierSegmentation": seg_resp.data if seg_resp and seg_resp.success else None,

            "snapshotKey": self._key(data_inicial, data_final, empresa_codigo),

        }

        if payload["intelligence"] and payload["healthScore"]:

            self._store.save(self._key(data_inicial, data_final, empresa_codigo), payload)

        return payload



    async def refresh_background(

        self,

        data_inicial: str,

        data_final: str,

        empresa_codigo: str | int | None = None,

    ) -> None:

        key = self._key(data_inicial, data_final, empresa_codigo)

        async with self._lock:

            if key in self._running:

                return

            self._running.add(key)

        try:

            await self.collect(data_inicial, data_final, empresa_codigo)

        finally:

            async with self._lock:

                self._running.discard(key)


