"""Importacao local. Nao altera o arquivo original."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from src.operational.dfe import store
from src.operational.dfe.service import import_files

COMPANY = 118508
CNPJ = "02080237000155"


def default_inboxes(root: Path) -> list[Path]:
    return [
        root / "data" / "dfe" / "inbox" / "118508",
        root / "data" / "dfe" / "manual_import" / "118508",
    ]


def collect_files(directories: list[Path]) -> list[Path]:
    found: list[Path] = []
    for directory in directories:
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*")):
            if path.is_file() and path.suffix.lower() in {".xml", ".zip"}:
                found.append(path)
    return found


def import_local(
    *,
    root: Path,
    company_code: int = COMPANY,
    company_cnpj: str = CNPJ,
    inboxes: list[Path] | None = None,
) -> dict[str, Any]:
    directories = inboxes or default_inboxes(root)
    found = collect_files(directories)
    processed_dir = root / "data" / "dfe" / "processed" / str(company_code)
    quarantine_dir = root / "data" / "dfe" / "quarantine" / str(company_code)
    processed_dir.mkdir(parents=True, exist_ok=True)
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    files = [(path.name, path.read_bytes()) for path in found]
    imported = (
        import_files(company_code=company_code, company_cnpj=company_cnpj, files=files, actor="dfe-sync")
        if files
        else {
            "imported": 0,
            "duplicates": 0,
            "invalid": 0,
            "results": [],
            "webpostoWrites": 0,
            "sefazQueries": 0,
            "manifestation": 0,
            "itemsFound": 0,
        }
    )
    by_name = {row.get("sourceFile") or row.get("file"): row for row in imported.get("results") or []}
    quarantined = 0
    copied = 0
    for path in found:
        row = by_name.get(path.name) or {}
        ok = bool(row.get("ok"))
        dest_dir = processed_dir if ok or row.get("status") == "DUPLICATE" else quarantine_dir
        dest = dest_dir / path.name
        if dest.exists():
            dest = dest_dir / f"{path.stem}-{path.stat().st_size}{path.suffix}"
        shutil.copy2(path, dest)
        copied += 1
        if dest_dir == quarantine_dir:
            quarantined += 1
            (dest.with_suffix(dest.suffix + ".reason.json")).write_text(
                json.dumps(
                    {"file": path.name, "status": row.get("status"), "message": row.get("message")},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
    eans = _eans_from_results(imported.get("results") or [])
    state = store.get_sync_state(company_code, "PRODUCTION")
    state["documents_imported"] = int(state.get("documents_imported") or 0) + int(imported.get("imported") or 0)
    state["duplicates"] = int(state.get("duplicates") or 0) + int(imported.get("duplicates") or 0)
    state["quarantined"] = int(state.get("quarantined") or 0) + quarantined
    store.save_sync_state(state)
    return {
        "found": len(found),
        "imported": imported.get("imported") or 0,
        "duplicates": imported.get("duplicates") or 0,
        "invalid": imported.get("invalid") or 0,
        "recipient_mismatch": imported.get("recipientMismatch") or 0,
        "cancelled": imported.get("cancelled") or 0,
        "quarantined": quarantined,
        "copied": copied,
        "items_indexed": imported.get("itemsFound") or 0,
        "affected_eans": sorted(eans),
        "webposto_writes": 0,
        "sefaz_queries": 0,
        "manifestation": 0,
        "results": imported.get("results") or [],
    }


def _eans_from_results(results: list[dict[str, Any]]) -> set[str]:
    eans: set[str] = set()
    for row in results:
        if not row.get("ok") and row.get("status") != "CANCELLED":
            continue
        doc_id = row.get("documentId")
        if not doc_id:
            continue
        for item in store.load_items(doc_id):
            norm = item.get("normalized_json") or item
            for key in ("c_ean", "c_ean_trib", "cEAN", "cEANTrib"):
                value = str(norm.get(key) or "").strip()
                if value and value != "None":
                    eans.add(value)
    return eans
