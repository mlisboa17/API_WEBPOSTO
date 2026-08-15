"""Orquestração DF-e — import em lote, sync bloqueado, NSU, pré-cadastro."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from src.infrastructure.config.settings import settings
from src.operational.dfe import batch as batch_store
from src.operational.dfe import store
from src.operational.dfe.packaging import resolve_packaging
from src.operational.dfe.parser import parse_items_from_xml
from src.operational.dfe.pre_register import analyze_document, analyze_item
from src.operational.dfe.pynfe_provider import PyNFeDistributionProvider
from src.operational.dfe.vault import get_vault, vault_public_status
from src.operational.dfe.xml_import import (
    MAX_FILES_IN_UPLOAD,
    ExpandResult,
    ImportErrorDFe,
    expand_upload_detailed,
    mask_access_key,
    parse_xml_bytes,
    sha256_bytes,
)


class DFeError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


STATUS_PT = {
    "NO_FISCAL_MODEL": "Sem modelo fiscal",
    "ALREADY_REGISTERED": "Já cadastrado",
    "PRE_REGISTER_READY": "Pré-cadastro pronto",
    "READY_FOR_REVIEW": "Pronto para revisão",
    "TAX_CONFLICT": "Conflito tributário",
    "PACKAGING_AMBIGUITY": "Conferir embalagem",
    "DUPLICATE": "Possível duplicidade",
    "BLOCKED": "Bloqueado",
    "CANCELLED_DOCUMENT": "Documento cancelado",
    "IMPORTED": "Importado",
    "PARSED": "Analisado",
    "INVALID_XML": "XML inválido",
    "UNSUPPORTED_SCHEMA": "Schema não suportado",
    "RECIPIENT_MISMATCH": "Destinatário divergente",
    "CANCELLED": "Cancelado",
    "IGNORED_NON_XML": "Ignorado (não XML)",
    "QUARANTINED": "Quarentena",
    "FAILED": "Falhou",
    "VALIDATED": "Validado",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _digits(v: str | None) -> str:
    return "".join(ch for ch in str(v or "") if ch.isdigit())


def _dec(v: Any) -> Decimal | None:
    if v is None or v == "":
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None


def flags() -> dict[str, Any]:
    return {
        "DFE_AUTO_SYNC_ENABLED": bool(getattr(settings, "dfe_auto_sync_enabled", False)),
        "DFE_MANIFESTATION_ENABLED": bool(getattr(settings, "dfe_manifestation_enabled", False)),
        "SEFAZ_QUERIES": 1 if bool(getattr(settings, "dfe_auto_sync_enabled", False)) else 0,
        "WEBPOSTO_WRITES": 0,
        "vault": vault_public_status(),
    }


def _packaging_explain(item: dict[str, Any]) -> dict[str, Any]:
    pack = item.get("packaging") or {}
    factor = pack.get("conversion_factor")
    v_un = _dec(item.get("v_un_com"))
    unit_cost = _dec(pack.get("purchase_unit_cost"))
    u_com = item.get("u_com") or "UN"
    explain = {
        "status": pack.get("packaging_status"),
        "statusLabel": STATUS_PT.get(pack.get("packaging_status") or "", pack.get("packaging_status")),
        "comprado": None,
        "conteudo": None,
        "custoUnitario": None,
        "formula": None,
        "ambiguous": bool(pack.get("ambiguous")),
    }
    if v_un is not None:
        explain["comprado"] = f"1 {u_com} por R$ {v_un:.2f}"
    if factor and factor > 1:
        explain["conteudo"] = f"{int(factor) if float(factor).is_integer() else factor} UNIDADES"
        if v_un is not None and unit_cost is not None:
            explain["custoUnitario"] = f"R$ {unit_cost:.2f}"
            explain["formula"] = f"R$ {v_un:.2f} ÷ {factor:g}"
    elif factor == 1 and unit_cost is not None:
        explain["conteudo"] = "1 UNIDADE"
        explain["custoUnitario"] = f"R$ {unit_cost:.2f}"
        explain["formula"] = "sem conversão"
    return explain


def _process_one_xml(
    *,
    company_code: int,
    expected_cnpj: str,
    source_file: str,
    relative_path: str,
    data: bytes,
    actor: str,
    vault: Any,
    fiscal_models: list[dict[str, Any]],
) -> dict[str, Any]:
    base = {
        "file": relative_path,
        "sourceFile": source_file,
        "relativePath": relative_path,
        "size": len(data),
        "sha256": sha256_bytes(data),
        "webpostoWrites": 0,
        "sefazQueries": 0,
    }
    try:
        meta = parse_xml_bytes(data)
    except ImportErrorDFe as exc:
        return {
            **base,
            "ok": False,
            "status": "INVALID_XML" if exc.code in {"INVALID_XML", "XML_MALFORMED"} else exc.code,
            "code": exc.code,
            "message": exc.message,
            "documentType": None,
            "accessKeyMasked": None,
            "itemCount": 0,
        }

    if meta.get("status") == "CANCELLED":
        linked_id = None
        access_key = meta.get("access_key")
        if access_key:
            for existing in store.list_documents(company_code):
                if existing.get("access_key") != access_key:
                    continue
                if existing.get("document_type") not in {"PROC_NFE", "OTHER"}:
                    continue
                proto = dict(existing.get("protocol") or {})
                proto["cancelled"] = True
                existing["protocol"] = proto
                existing["status"] = "CANCELLED"
                store.save_document(existing)
                linked_id = existing.get("id")
                break
        return {
            **base,
            "ok": False,
            "status": "CANCELLED",
            "code": "CANCELLED",
            "message": "documento cancelado",
            "documentType": meta.get("document_type"),
            "accessKeyMasked": meta.get("access_key_masked"),
            "recipientCnpj": meta.get("recipient_cnpj"),
            "documentId": linked_id,
            "itemCount": 0,
        }

    if meta.get("status") == "UNSUPPORTED_SCHEMA":
        return {
            **base,
            "ok": False,
            "status": "UNSUPPORTED_SCHEMA",
            "code": "UNSUPPORTED_SCHEMA",
            "message": "schema não suportado para pré-cadastro",
            "documentType": meta.get("document_type"),
            "accessKeyMasked": meta.get("access_key_masked"),
            "itemCount": 0,
        }

    if meta.get("recipient_cnpj") and expected_cnpj and meta["recipient_cnpj"] != expected_cnpj:
        return {
            **base,
            "ok": False,
            "status": "RECIPIENT_MISMATCH",
            "code": "RECIPIENT_MISMATCH",
            "message": "destinatário do XML diverge da empresa selecionada",
            "documentType": meta.get("document_type"),
            "accessKeyMasked": meta.get("access_key_masked"),
            "recipientCnpj": meta.get("recipient_cnpj"),
            "expectedCnpj": expected_cnpj,
            "itemCount": 0,
        }

    dup = store.find_duplicate(
        company_code=company_code,
        access_key=meta.get("access_key"),
        document_type=meta["document_type"],
        xml_sha256=meta["xml_sha256"],
    )
    if dup:
        return {
            **base,
            "ok": False,
            "status": "DUPLICATE",
            "code": "DUPLICATE",
            "message": "documento já importado",
            "documentId": dup["id"],
            "documentType": meta.get("document_type"),
            "accessKeyMasked": meta.get("access_key_masked"),
            "itemCount": 0,
        }

    doc_id = store.new_id("dfe_doc")
    if vault.is_configured():
        sec = vault.put_secret(company_code=company_code, purpose="XML", plaintext=data)
        xml_ref = sec.secret_id
    else:
        path = store._root() / "documents" / f"{doc_id}.xml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        xml_ref = str(path.name)

    doc = {
        "id": doc_id,
        "company_code": company_code,
        "nsu": None,
        "access_key": meta.get("access_key"),
        "access_key_masked": meta.get("access_key_masked"),
        "schema_name": meta.get("schema_name"),
        "document_type": meta["document_type"],
        "issuer_cnpj": meta.get("issuer_cnpj"),
        "issuer_name": meta.get("issuer_name"),
        "recipient_cnpj": meta.get("recipient_cnpj"),
        "nNF": meta.get("nNF"),
        "serie": meta.get("serie"),
        "vNF": meta.get("vNF"),
        "issued_at": meta.get("issued_at"),
        "received_at": _now(),
        "status": meta.get("status") or "VALIDATED",
        "xml_storage_reference": xml_ref,
        "xml_sha256": meta["xml_sha256"],
        "source": "MANUAL",
        "created_at": _now(),
        "updated_at": _now(),
        "protocol": meta.get("protocol"),
        "filename": relative_path,
        "source_file": source_file,
    }
    store.save_document(doc)

    items: list[dict[str, Any]] = []
    item_analyses: list[dict[str, Any]] = []
    if doc["document_type"] in {"PROC_NFE", "OTHER"}:
        try:
            items = parse_items_from_xml(data)
            for it in items:
                pack = resolve_packaging(it)
                it["packaging"] = pack
                it["packaging_status"] = pack["packaging_status"]
                it["conversion_factor"] = pack["conversion_factor"]
                it["purchase_unit_cost"] = pack["purchase_unit_cost"]
                it["sale_unit_cost_candidate"] = pack["sale_unit_cost_candidate"]
                it["packaging_explain"] = _packaging_explain(it)
                it["id"] = store.new_id("dfe_item")
                it["document_id"] = doc_id
                it["company_code"] = company_code
                analysis = analyze_item(
                    it,
                    company_code=company_code,
                    existing_products=[],
                    fiscal_models=fiscal_models,
                    document_status=doc["status"],
                )
                analysis["statusLabel"] = STATUS_PT.get(analysis["status"], analysis["status"])
                it["pre_register"] = analysis
                item_analyses.append(analysis)
            store.save_items(doc_id, items)
            if items:
                doc["status"] = "PARSED"
                store.save_document(doc)
        except Exception:
            doc["status"] = "QUARANTINED"
            store.save_document(doc)
            return {
                **base,
                "ok": False,
                "status": "QUARANTINED",
                "code": "QUARANTINED",
                "message": "falha ao extrair itens",
                "documentId": doc_id,
                "documentType": doc["document_type"],
                "accessKeyMasked": doc.get("access_key_masked"),
                "itemCount": 0,
            }

    store.append_audit(
        company_code=company_code,
        action="XML_IMPORT",
        actor=actor,
        target_type="document",
        target_id=doc_id,
        detail={"sha256": meta["xml_sha256"], "type": doc["document_type"], "items": len(items)},
    )

    pr_summary: dict[str, int] = {}
    for a in item_analyses:
        pr_summary[a["status"]] = pr_summary.get(a["status"], 0) + 1

    return {
        **base,
        "ok": True,
        "status": "PARSED" if items else "IMPORTED",
        "code": "IMPORTED",
        "message": "importado",
        "documentId": doc_id,
        "documentType": doc["document_type"],
        "accessKeyMasked": doc.get("access_key_masked"),
        "issuerName": doc.get("issuer_name"),
        "issuerCnpj": doc.get("issuer_cnpj"),
        "recipientCnpj": doc.get("recipient_cnpj"),
        "nNF": doc.get("nNF"),
        "serie": doc.get("serie"),
        "issuedAt": doc.get("issued_at"),
        "vNF": doc.get("vNF"),
        "itemCount": len(items),
        "preRegisterSummary": pr_summary,
        "items": [
            {
                "id": it["id"],
                "line": it.get("line_number"),
                "xProd": it.get("x_prod"),
                "cProd": it.get("c_prod"),
                "cEAN": it.get("c_ean"),
                "cEANTrib": it.get("c_ean_trib"),
                "ncm": it.get("ncm"),
                "cest": it.get("cest"),
                "uCom": it.get("u_com"),
                "qCom": it.get("q_com"),
                "uTrib": it.get("u_trib"),
                "qTrib": it.get("q_trib"),
                "vUnCom": it.get("v_un_com"),
                "conversionFactor": it.get("conversion_factor"),
                "purchaseUnitCost": it.get("purchase_unit_cost"),
                "packagingExplain": it.get("packaging_explain"),
                "preRegisterStatus": (it.get("pre_register") or {}).get("status"),
                "preRegisterStatusLabel": (it.get("pre_register") or {}).get("statusLabel"),
            }
            for it in items
        ],
    }


def import_files(
    *,
    company_code: int,
    company_cnpj: str,
    files: list[tuple[str, bytes]],
    actor: str = "system",
    role: str = "operator",
) -> dict[str, Any]:
    if role not in {"admin", "approver", "operator", "director"}:
        raise DFeError("FORBIDDEN", "sem permissão", 403)
    if len(files) > MAX_FILES_IN_UPLOAD:
        raise DFeError("TOO_MANY_FILES", f"máximo {MAX_FILES_IN_UPLOAD} arquivos por envio", 400)

    expected = _digits(company_cnpj)
    vault = get_vault()
    batch = batch_store.create_batch(company_code, source_files=len(files))
    batch_id = batch["batchId"]
    batch_store.update_batch(batch_id, status="PROCESSING")

    fiscal_models: list[dict[str, Any]] = []
    try:
        from src.operational.fiscal_models.service import list_models

        fiscal_models = list_models(company_code=company_code)
    except Exception:
        fiscal_models = []

    expands: list[ExpandResult] = []
    for name, data in files:
        expands.append(expand_upload_detailed(name, data))

    results: list[dict[str, Any]] = []
    ignored = 0
    xml_found = 0

    # fatals sem XML
    for exp in expands:
        for e in exp.entries:
            if e.status == "IGNORED_NON_XML":
                ignored += 1
                results.append(
                    {
                        "file": e.relative_path,
                        "sourceFile": e.source_file,
                        "relativePath": e.relative_path,
                        "size": e.size,
                        "ok": False,
                        "status": "IGNORED_NON_XML",
                        "code": e.code or "IGNORED_NON_XML",
                        "message": e.message,
                        "itemCount": 0,
                        "webpostoWrites": 0,
                    }
                )
            elif e.status == "FAILED" and e.data is None:
                results.append(
                    {
                        "file": e.relative_path,
                        "sourceFile": e.source_file,
                        "relativePath": e.relative_path,
                        "size": e.size,
                        "ok": False,
                        "status": "FAILED",
                        "code": e.code or "FAILED",
                        "message": e.message,
                        "itemCount": 0,
                        "webpostoWrites": 0,
                    }
                )
        if exp.fatal_code and not exp.xml_ready:
            results.append(
                {
                    "file": exp.source_file,
                    "sourceFile": exp.source_file,
                    "relativePath": exp.source_file,
                    "ok": False,
                    "status": "FAILED",
                    "code": exp.fatal_code,
                    "message": exp.fatal_message,
                    "itemCount": 0,
                    "webpostoWrites": 0,
                }
            )
        xml_found += len(exp.xml_ready)

    ready = [(e.source_file, e.relative_path, e.data) for exp in expands for e in exp.xml_ready]
    batch_store.update_batch(batch_id, total=xml_found + ignored + sum(1 for r in results if r.get("status") == "FAILED" and r.get("sourceFile") and not any(x[1]==r.get("file") for x in ready)))

    imported = duplicates = invalid = blocked = recipient_mismatch = cancelled = 0
    processed = 0
    for source_file, rel, data in ready:
        if data is None:
            continue
        batch_store.update_batch(batch_id, currentItem=rel, processed=processed)
        one = _process_one_xml(
            company_code=company_code,
            expected_cnpj=expected,
            source_file=source_file,
            relative_path=rel,
            data=data,
            actor=actor,
            vault=vault,
            fiscal_models=fiscal_models,
        )
        results.append(one)
        processed += 1
        st = one.get("status")
        if one.get("ok"):
            imported += 1
        elif st == "DUPLICATE":
            duplicates += 1
        elif st in {"INVALID_XML", "UNSUPPORTED_SCHEMA", "QUARANTINED", "FAILED"}:
            invalid += 1
        elif st == "RECIPIENT_MISMATCH":
            recipient_mismatch += 1
            blocked += 1
        elif st == "CANCELLED":
            cancelled += 1
        else:
            blocked += 1

    # item stats
    items_found = sum(int(r.get("itemCount") or 0) for r in results if r.get("ok"))
    no_model = 0
    ready_review = 0
    for r in results:
        for it in r.get("items") or []:
            if it.get("preRegisterStatus") == "NO_FISCAL_MODEL":
                no_model += 1
            if it.get("preRegisterStatus") in {"READY_FOR_REVIEW", "PRE_REGISTER_READY"}:
                ready_review += 1

    failures = sum(1 for r in results if not r.get("ok") and r.get("status") != "IGNORED_NON_XML")
    status = "COMPLETED"
    if failures and imported:
        status = "COMPLETED_WITH_ERRORS"
    elif failures and not imported:
        status = "COMPLETED_WITH_ERRORS" if xml_found or ignored else "FAILED"

    batch_store.update_batch(
        batch_id,
        status=status,
        processed=processed,
        successes=imported,
        duplicates=duplicates,
        failures=failures,
        ignored=ignored,
        currentItem=None,
        completedAt=_now(),
        total=xml_found,
    )

    store.append_audit(
        company_code=company_code,
        action="BATCH_IMPORT",
        actor=actor,
        target_type="batch",
        target_id=batch_id,
        detail={
            "sourceFiles": len(files),
            "xmlFound": xml_found,
            "imported": imported,
            "duplicates": duplicates,
            "invalid": invalid,
        },
    )

    return {
        "success": True,
        "batchId": batch_id,
        "companyCode": company_code,
        "sourceFiles": len(files),
        "xmlEntriesFound": xml_found,
        "imported": imported,
        "duplicates": duplicates,
        "invalid": invalid,
        "ignored": ignored,
        "blocked": blocked,
        "recipientMismatch": recipient_mismatch,
        "cancelled": cancelled,
        "itemsFound": items_found,
        "noFiscalModel": no_model,
        "readyForReview": ready_review,
        "batchStatus": status,
        "results": results,
        "message": (
            "Os XMLs foram processados. Revise duplicidades, embalagens e itens sem modelo fiscal. "
            "Nenhum produto foi cadastrado no webPosto."
        ),
        "webpostoWrites": 0,
        "sefazQueries": 0,
        "manifestation": 0,
        "vault": vault_public_status(),
        "statusLabels": STATUS_PT,
    }


def get_document(doc_id: str, company_code: int | None = None) -> dict[str, Any]:
    doc = store.load_document(doc_id)
    if not doc:
        raise DFeError("NOT_FOUND", "documento não encontrado", 404)
    if company_code is not None and int(doc.get("company_code") or 0) != company_code:
        raise DFeError("FORBIDDEN", "isolamento por empresa", 403)
    if doc.get("access_key") and not doc.get("access_key_masked"):
        doc["access_key_masked"] = mask_access_key(doc.get("access_key"))
    return doc


def sync_preview(company_code: int) -> dict[str, Any]:
    state = store.get_sync_state(company_code)
    return {
        "company_code": company_code,
        "sync_state": state,
        "flags": flags(),
        "wouldQuerySefaz": False,
        "blockedReasons": _sync_block_reasons(company_code, role="admin"),
        "sefazQueries": 0,
        "webpostoWrites": 0,
    }


def _sync_block_reasons(company_code: int, *, role: str) -> list[str]:
    reasons: list[str] = []
    if not bool(getattr(settings, "dfe_auto_sync_enabled", False)):
        reasons.append("DFE_AUTO_SYNC_ENABLED=false")
    if not get_vault().is_configured():
        reasons.append("VAULT_NOT_CONFIGURED")
    if role not in {"admin", "approver"}:
        reasons.append("ADMIN_REQUIRED")
    certs = store.list_certificates(company_code)
    active = [c for c in certs if not c.get("disabled")]
    if not active:
        reasons.append("NO_CERTIFICATE")
    else:
        c = active[0]
        if c.get("status") == "EXPIRED":
            reasons.append("CERTIFICATE_EXPIRED")
        if c.get("status") == "CNPJ_MISMATCH":
            reasons.append("CNPJ_MISMATCH")
        if c.get("disabled"):
            reasons.append("CERTIFICATE_DISABLED")
    return reasons


def sync_start(*, company_code: int, actor: str, role: str) -> dict[str, Any]:
    reasons = _sync_block_reasons(company_code, role=role)
    store.append_audit(
        company_code=company_code,
        action="SYNC_START_BLOCKED",
        actor=actor,
        detail={"reasons": reasons},
    )
    return {
        "success": False,
        "blocked": True,
        "reasons": reasons,
        "sefazQueries": 0,
        "webpostoWrites": 0,
        "manifestation": False,
        "message": "Sincronização SEFAZ bloqueada nesta entrega",
    }


def sync_start(*, company_code: int, actor: str, role: str) -> dict[str, Any]:
    """Executa uma página da Distribuição DF-e e só avança NSU após persistência."""
    reasons = _sync_block_reasons(company_code, role=role)
    if reasons:
        store.append_audit(company_code=company_code, action="SYNC_START_BLOCKED", actor=actor, detail={"reasons": reasons})
        return {"success": False, "blocked": True, "reasons": reasons, "sefazQueries": 0, "webpostoWrites": 0, "manifestation": False}
    cert = next(c for c in store.list_certificates(company_code) if not c.get("disabled"))
    vault = get_vault()
    provider = PyNFeDistributionProvider(
        allow_sefaz_queries=True,
        pfx_bytes=vault.get_secret(cert["pfx_secret_id"]),
        password=vault.get_secret(cert["password_secret_id"]).decode("utf-8"),
    )
    environment = "PRODUCTION"
    state = store.get_sync_state(company_code, environment)
    next_allowed = state.get("next_allowed_query_at")
    if next_allowed:
        allowed_at = datetime.fromisoformat(next_allowed)
        if datetime.now(timezone.utc) < allowed_at:
            return {
                "success": False,
                "blocked": True,
                "reasons": ["SEFAZ_COOLDOWN_ACTIVE"],
                "nextAllowedQueryAt": next_allowed,
                "sefazQueries": 0,
                "webpostoWrites": 0,
                "manifestation": False,
            }
    try:
        result = provider.query_distribution_by_last_nsu(
            company_cnpj=cert["cnpj"], uf=cert.get("uf") or "PE",
            last_nsu=state["last_nsu"], homologation=False,
        )
        if result.c_stat == "656":
            if result.ult_nsu != "000000000000000":
                state["last_nsu"] = result.ult_nsu
            state["last_query_at"] = _now()
            state["next_allowed_query_at"] = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            state["status"] = "RATE_LIMITED"
            state["last_status_code"] = result.c_stat
            state["last_error_sanitized"] = "SEFAZ_CONSUMO_INDEVIDO"
            state["consecutive_failures"] = int(state.get("consecutive_failures") or 0) + 1
            store.save_sync_state(state)
            store.append_audit(company_code=company_code, action="SEFAZ_RATE_LIMITED", actor=actor, detail={"cStat": result.c_stat, "ultNSU": result.ult_nsu, "nextAllowedQueryAt": state["next_allowed_query_at"]})
            return {"success": False, "blocked": True, "cStat": result.c_stat, "xMotivo": result.x_motivo, "documentsReceived": 0, "state": state, "nextAllowedQueryAt": state["next_allowed_query_at"], "sefazQueries": 1, "webpostoWrites": 0, "manifestation": False}
        if result.c_stat not in {"137", "138"}:
            raise DFeError("SEFAZ_REJECTED", f"SEFAZ cStat={result.c_stat}", 502)
        files = [(f"sefaz_{d['nsu']}_{d.get('schema') or 'dfe'}.xml", d["xml_bytes"]) for d in result.documents]
        imported = import_files(company_code=company_code, company_cnpj=cert["cnpj"], files=files, actor=actor, role=role) if files else None
        acceptable = {"PARSED", "IMPORTED", "DUPLICATE", "CANCELLED"}
        persisted = imported is None or all(r.get("status") in acceptable for r in imported.get("results", []))
        state["last_query_at"] = _now(); state["last_status_code"] = result.c_stat
        state["last_error_sanitized"] = None; state["consecutive_failures"] = 0
        state["next_allowed_query_at"] = None
        store.save_sync_state(state)
        advance_nsu_after_persist(company_code, environment=environment, new_ult_nsu=result.ult_nsu, max_nsu=result.max_nsu, documents_persisted=persisted)
        store.append_audit(company_code=company_code, action="SEFAZ_SYNC", actor=actor, detail={"cStat": result.c_stat, "documents": len(files), "ultNSU": result.ult_nsu, "maxNSU": result.max_nsu})
        return {"success": persisted, "blocked": False, "cStat": result.c_stat, "xMotivo": result.x_motivo, "documentsReceived": len(files), "import": imported, "state": store.get_sync_state(company_code, environment), "sefazQueries": 1, "webpostoWrites": 0, "manifestation": False}
    except Exception as exc:
        state["last_query_at"] = _now(); state["status"] = "ERROR"
        state["consecutive_failures"] = int(state.get("consecutive_failures") or 0) + 1
        state["last_error_sanitized"] = type(exc).__name__
        store.save_sync_state(state)
        store.append_audit(company_code=company_code, action="SEFAZ_SYNC_FAIL", actor=actor, detail={"error": type(exc).__name__})
        raise DFeError("SEFAZ_SYNC_FAILED", "falha sanitizada na consulta SEFAZ", 502) from exc


def sync_status(company_code: int) -> dict[str, Any]:
    return {
        "company_code": company_code,
        "state": store.get_sync_state(company_code),
        "flags": flags(),
        "sefazQueries": 0,
        "webpostoWrites": 0,
    }


def reset_nsu(*, company_code: int, actor: str, role: str, confirm: bool) -> dict[str, Any]:
    if role != "admin":
        raise DFeError("FORBIDDEN", "reset NSU requer admin", 403)
    if not confirm:
        raise DFeError("CONFIRMATION_REQUIRED", "envie confirm=true", 400)
    state = store.get_sync_state(company_code)
    prev = state.get("last_nsu")
    state["last_nsu"] = "000000000000000"
    state["max_nsu"] = "000000000000000"
    state["consecutive_failures"] = 0
    state["status"] = "IDLE"
    store.save_sync_state(state)
    store.append_audit(
        company_code=company_code,
        action="NSU_RESET",
        actor=actor,
        detail={"previous_last_nsu": prev},
    )
    return {"success": True, "state": state, "webpostoWrites": 0, "sefazQueries": 0}


def pre_register_analyze(document_id: str, company_code: int | None = None) -> dict[str, Any]:
    doc = get_document(document_id, company_code=company_code)
    items = store.load_items(document_id)
    fiscal_models: list[dict[str, Any]] = []
    try:
        from src.operational.fiscal_models.service import list_models

        fiscal_models = list_models(company_code=int(doc["company_code"]))
    except Exception:
        fiscal_models = []
    result = analyze_document(doc, items, existing_products=[], fiscal_models=fiscal_models)
    for it in result.get("items") or []:
        it["statusLabel"] = STATUS_PT.get(it.get("status") or "", it.get("status"))
    store.append_audit(
        company_code=doc.get("company_code"),
        action="PRE_REGISTER_ANALYZE",
        actor="system",
        target_type="document",
        target_id=document_id,
        detail={"summary": result.get("summary")},
    )
    return result


def advance_nsu_after_persist(
    company_code: int,
    *,
    environment: str,
    new_ult_nsu: str,
    max_nsu: str,
    documents_persisted: bool,
) -> dict[str, Any]:
    state = store.get_sync_state(company_code, environment)
    if not documents_persisted:
        state["last_error_sanitized"] = "persistência falhou — NSU não avançado"
        store.save_sync_state(state)
        return state
    state["last_nsu"] = str(new_ult_nsu).zfill(15)
    state["max_nsu"] = str(max_nsu).zfill(15)
    if state["last_nsu"] == state["max_nsu"]:
        state["status"] = "UP_TO_DATE"
    store.save_sync_state(state)
    return state
