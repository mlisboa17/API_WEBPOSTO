"""Fachada da ingestao incremental DF-e + recálculo de custo."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.operational.cost_update.current_cost_reader import CurrentProductCostReader
from src.operational.cost_update.service import CostUpdateService
from src.operational.dfe import store
from src.operational.dfe_sync.lease import acquire_lease, release_lease
from src.operational.dfe_sync.local_inbox import import_local
from src.operational.dfe_sync.packaging_conversion import PackagingConversionResolver
from src.operational.dfe_sync.sefaz_once import cooldown_active, sync_sefaz_once
from src.operational.product_registration.company_credentials import (
    HttpProductReader,
    resolve_credential,
)

COMPANY = 118508
CNPJ = "02080237000155"


class DfeCostSyncService:
    def __init__(self, root: Path, output_dir: Path | None = None) -> None:
        self.root = Path(root)
        self.output_dir = Path(output_dir or root / "data" / "cost_update" / "118508")
        self.packaging = PackagingConversionResolver.from_path(
            self.root / "config" / "cost_update" / "packaging_conversions.json"
        )

    def status(self) -> dict[str, Any]:
        state = store.get_sync_state(COMPANY, "PRODUCTION")
        return {
            "company_code": COMPANY,
            "environment": "PRODUCTION",
            "last_nsu": state.get("last_nsu"),
            "max_nsu": state.get("max_nsu"),
            "last_query_at": state.get("last_query_at"),
            "next_allowed_query_at": state.get("next_allowed_query_at"),
            "cooldown_active": cooldown_active(state),
            "lease_owner": state.get("lease_owner"),
            "documents_received": state.get("documents_received") or 0,
            "documents_imported": state.get("documents_imported") or 0,
            "duplicates": state.get("duplicates") or 0,
            "quarantined": state.get("quarantined") or 0,
            "webposto_writes": 0,
            "manifestation": 0,
        }

    def import_local(self) -> dict[str, Any]:
        return import_local(root=self.root)

    def sync_sefaz_once(self, provider: Any | None = None) -> dict[str, Any]:
        return sync_sefaz_once(provider=provider)

    def recalculate(self, eans: set[str], *, key: str | None = None, reader=None) -> dict[str, Any]:
        pending = json.loads(
            (self.root / "data" / "product_registration" / "pending_cost_update_118508.json").read_text(
                encoding="utf-8"
            )
        ) if (self.root / "data" / "product_registration" / "pending_cost_update_118508.json").is_file() else {}
        pending_eans = set(pending) | set(
            json.loads(
                (self.root / "data" / "product_registration" / "pending_price_review_118508.json").read_text(
                    encoding="utf-8"
                )
            )
            if (self.root / "data" / "product_registration" / "pending_price_review_118508.json").is_file()
            else {}
        )
        target = {ean for ean in eans if ean in pending_eans}
        if not target:
            return {
                "recalculated": 0,
                "affected_pending": [],
                "webposto_writes": 0,
                "event": "DFE_IMPORTED_COST_REEVALUATED",
            }
        pending_path = self.root / "data" / "product_registration" / "pending_cost_update_118508.json"
        price_review_path = self.root / "data" / "product_registration" / "pending_price_review_118508.json"
        checkpoint_path = self.root / "data" / "product_registration" / "execution" / "checkpoint_118508.json"
        accountant_path = self.root / "data" / "product_registration" / "accountant_review_118508.json"
        if reader is None:
            if not key:
                key = resolve_credential(COMPANY).key
            import httpx

            reader = CurrentProductCostReader(HttpProductReader(httpx.Client(timeout=60.0)))
        service = CostUpdateService(
            self.output_dir,
            reader=reader,
            pending_path=pending_path,
            price_review_path=price_review_path,
            checkpoint_path=checkpoint_path,
            accountant_path=accountant_path,
        )
        before = {ean: (service.store.latest_for_ean(ean) or {}).get("status") for ean in target}
        result = service.propose(
            key or "local",
            eans=target,
            persist_aggregates=False,
            event="DFE_IMPORTED_COST_REEVALUATED",
        )
        after = {ean: (service.store.latest_for_ean(ean) or {}).get("status") for ean in target}
        self._write_packaging_review(target)
        return {
            "recalculated": result.get("analyzed") or 0,
            "affected_pending": sorted(target),
            "before": before,
            "after": after,
            "counts": result.get("counts"),
            "api_reads": result.get("api_reads") or 0,
            "webposto_writes": 0,
            "event": "DFE_IMPORTED_COST_REEVALUATED",
        }

    def run_once(self, *, provider: Any | None = None, key: str | None = None, reader=None) -> dict[str, Any]:
        lease = acquire_lease(COMPANY)
        if not lease["ok"]:
            return {"ok": False, "reason": "LEASE_HELD", "webposto_writes": 0, "manifestation": 0}
        try:
            local = self.import_local()
            sefaz = self.sync_sefaz_once(provider=provider)
            eans = set(local.get("affected_eans") or []) | set(sefaz.get("affected_eans") or [])
            recalc = self.recalculate(eans, key=key, reader=reader) if eans else {"recalculated": 0}
            return {
                "ok": True,
                "local": local,
                "sefaz": sefaz,
                "recalculate": recalc,
                "webposto_writes": 0,
                "manifestation": 0,
            }
        finally:
            release_lease(COMPANY, lease["owner"])

    def _write_packaging_review(self, eans: set[str]) -> None:
        rows = []
        for document in store.list_documents(COMPANY):
            for item in store.load_items(document["id"]):
                norm = item.get("normalized_json") or item
                ean = str(norm.get("c_ean") or "")
                if ean not in eans:
                    continue
                resolved = self.packaging.resolve(norm, supplier_cnpj=document.get("issuer_cnpj"))
                if resolved.get("ok"):
                    continue
                rows.append(
                    {
                        "ean": ean,
                        "produto": norm.get("x_prod"),
                        "fornecedor": document.get("issuer_name"),
                        "uCom": resolved.get("u_com"),
                        "qCom": str(resolved.get("q_com")),
                        "uTrib": resolved.get("u_trib"),
                        "qTrib": str(resolved.get("q_trib")),
                        "descricao": norm.get("x_prod"),
                        "fator_sugerido": str(resolved.get("suggested_factor")) if resolved.get("suggested_factor") else None,
                        "calculo": resolved.get("calculo"),
                        "confidence": resolved.get("confidence"),
                        "evidencias": resolved.get("evidences"),
                        "status": resolved.get("status"),
                    }
                )
        path = self.output_dir / "packaging_conversion_review.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"items": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
