"""Uma consulta SEFAZ por execucao. NSU so avanca apos importacao segura."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from src.operational.dfe import store
from src.operational.dfe.pynfe_provider import PyNFeDistributionProvider
from src.operational.dfe.service import advance_nsu_after_persist, import_files
from src.operational.dfe.vault import get_vault
from src.operational.dfe_sync.local_inbox import _eans_from_results

COMPANY = 118508
CNPJ = "02080237000155"
ENVIRONMENT = "PRODUCTION"
COOLDOWN_656 = timedelta(hours=1)


def cooldown_active(state: dict[str, Any]) -> bool:
    raw = state.get("next_allowed_query_at")
    if not raw:
        return False
    allowed = datetime.fromisoformat(raw)
    if allowed.tzinfo is None:
        allowed = allowed.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) < allowed


def sync_sefaz_once(
    *,
    company_code: int = COMPANY,
    company_cnpj: str = CNPJ,
    provider: Any | None = None,
) -> dict[str, Any]:
    state = store.get_sync_state(company_code, ENVIRONMENT)
    previous_nsu = state.get("last_nsu")
    if cooldown_active(state):
        return {
            "ok": False,
            "blocked": True,
            "reason": "SEFAZ_COOLDOWN_ACTIVE",
            "previous_nsu": previous_nsu,
            "current_nsu": previous_nsu,
            "next_allowed_query_at": state.get("next_allowed_query_at"),
            "documents_received": 0,
            "sefaz_queries": 0,
            "webposto_writes": 0,
            "manifestation": 0,
            "affected_eans": [],
        }

    if provider is None:
        vault = get_vault()
        certs = [row for row in store.list_certificates(company_code) if not row.get("disabled")]
        if not vault.is_configured() or not certs:
            return {
                "ok": False,
                "blocked": True,
                "reason": "VAULT_OR_CERTIFICATE_MISSING",
                "previous_nsu": previous_nsu,
                "current_nsu": previous_nsu,
                "sefaz_queries": 0,
                "webposto_writes": 0,
                "manifestation": 0,
                "affected_eans": [],
            }
        cert = certs[0]
        provider = PyNFeDistributionProvider(
            allow_sefaz_queries=True,
            pfx_bytes=vault.get_secret(cert["pfx_secret_id"]),
            password=vault.get_secret(cert["password_secret_id"]).decode("utf-8"),
        )

    result = provider.query_distribution_by_last_nsu(
        company_cnpj=company_cnpj,
        uf="PE",
        last_nsu=str(state.get("last_nsu") or "0"),
        homologation=False,
    )
    state["last_query_at"] = datetime.now(timezone.utc).isoformat()
    state["last_status_code"] = result.c_stat
    state["documents_received"] = int(state.get("documents_received") or 0) + len(result.documents)

    if result.c_stat == "656":
        state["next_allowed_query_at"] = (datetime.now(timezone.utc) + COOLDOWN_656).isoformat()
        state["consecutive_failures"] = int(state.get("consecutive_failures") or 0) + 1
        state["last_error_sanitized"] = "SEFAZ_CONSUMO_INDEVIDO"
        store.save_sync_state(state)
        return {
            "ok": False,
            "blocked": True,
            "reason": "SEFAZ_656",
            "cStat": "656",
            "previous_nsu": previous_nsu,
            "current_nsu": previous_nsu,
            "next_allowed_query_at": state["next_allowed_query_at"],
            "documents_received": 0,
            "sefaz_queries": 1,
            "webposto_writes": 0,
            "manifestation": 0,
            "affected_eans": [],
        }

    if result.c_stat not in {"137", "138"}:
        state["consecutive_failures"] = int(state.get("consecutive_failures") or 0) + 1
        state["last_error_sanitized"] = f"cStat_{result.c_stat}"
        store.save_sync_state(state)
        return {
            "ok": False,
            "blocked": False,
            "reason": f"SEFAZ_{result.c_stat}",
            "previous_nsu": previous_nsu,
            "current_nsu": previous_nsu,
            "documents_received": len(result.documents),
            "sefaz_queries": 1,
            "webposto_writes": 0,
            "manifestation": 0,
            "affected_eans": [],
        }

    files = [(f"sefaz_{doc['nsu']}.xml", doc["xml_bytes"]) for doc in result.documents]
    imported = None
    persisted = True
    if files:
        imported = import_files(
            company_code=company_code,
            company_cnpj=company_cnpj,
            files=files,
            actor="dfe-sync",
        )
        acceptable = {"PARSED", "IMPORTED", "DUPLICATE", "CANCELLED"}
        persisted = all(row.get("status") in acceptable for row in imported.get("results") or [])
        state["documents_imported"] = int(state.get("documents_imported") or 0) + int(imported.get("imported") or 0)
        state["duplicates"] = int(state.get("duplicates") or 0) + int(imported.get("duplicates") or 0)
        state["quarantined"] = int(state.get("quarantined") or 0) + int(imported.get("invalid") or 0)

    state["consecutive_failures"] = 0
    state["last_error_sanitized"] = None
    store.save_sync_state(state)
    advance_nsu_after_persist(
        company_code,
        environment=ENVIRONMENT,
        new_ult_nsu=result.ult_nsu,
        max_nsu=result.max_nsu,
        documents_persisted=persisted,
    )
    refreshed = store.get_sync_state(company_code, ENVIRONMENT)
    eans = _eans_from_results((imported or {}).get("results") or [])
    return {
        "ok": persisted,
        "blocked": False,
        "cStat": result.c_stat,
        "previous_nsu": previous_nsu,
        "current_nsu": refreshed.get("last_nsu"),
        "documents_received": len(result.documents),
        "imported": (imported or {}).get("imported") or 0,
        "duplicates": (imported or {}).get("duplicates") or 0,
        "affected_eans": sorted(eans),
        "sefaz_queries": 1,
        "webposto_writes": 0,
        "manifestation": 0,
    }
