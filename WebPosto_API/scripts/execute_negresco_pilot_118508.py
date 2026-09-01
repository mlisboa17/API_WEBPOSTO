"""Executa UM unico POST do piloto NEGRESCO na empresa 118508.

Revalida os gates, envia exatamente um POST, confirma o vinculo em PRODUTO_EMPRESA e
para. A trava de POST unico e persistente: qualquer segunda execucao e recusada.

Nao imprime credencial. Nao envia empresaCodigo. Nao usa V1 como fallback.
Nao executa PUT, PATCH, DELETE nem rollback.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.operational.product_registration.company_credentials import (  # noqa: E402
    HttpProductReader,
    company_guard,
    resolve_credential,
)
from src.operational.product_registration.dfe_cost_resolver import find_cost_evidence  # noqa: E402
from src.operational.product_registration.registration_engine import (  # noqa: E402
    ProductRegistrationService,
)
from src.operational.product_registration.stores import interpret_lock  # noqa: E402

BASE_URL = "https://web.qualityautomacao.com.br"
LEGACY_ENDPOINT = "/INTEGRACAO/INCLUIR_PRODUTO"
COMPANY_CODE = 118508
COMPANY_CNPJ = "02.080.237/0001-55"
PROFILE = "WEBPOSTO_CONVENIENCIA_24_HORAS_KEY"
EAN = "7891000377130"
COST_CENTER = 24886

OUT_DIR = ROOT / "data" / "product_registration" / "pilot_negresco_118508"
PREFLIGHT = OUT_DIR / "preflight.json"
BODY_PREVIEW = OUT_DIR / "body_preview.json"
PILOT_LOCK = OUT_DIR / "pilot_post_lock.json"
RESULT = OUT_DIR / "post_result.json"

READY = "READY_FOR_EXPLICIT_WRITE_AUTHORIZATION"


class PilotBlocked(Exception):
    """Impede o POST quando um gate nao passa."""


def sanitize(url: str) -> str:
    return url.split("CHAVE=")[0] + "CHAVE=***REDACTED***" if "CHAVE=" in url else url


def rows(payload: Any) -> list[dict[str, Any]]:
    return payload.get("resultados") or [] if isinstance(payload, dict) else []


def assert_single_post_allowed() -> None:
    """Trava persistente: no modo piloto so um POST pode existir."""
    if PILOT_LOCK.is_file():
        lock = interpret_lock(json.loads(PILOT_LOCK.read_text(encoding="utf-8")))
        raise PilotBlocked(
            f"POST do piloto já executado em {lock.get('sentAt')} "
            f"(bodyHash={str(lock.get('bodyHash'))[:16]}...). Segunda tentativa recusada."
        )


def write_lock(body_hash: str, extra: dict[str, Any]) -> None:
    PILOT_LOCK.write_text(
        json.dumps(
            {
                "status": extra.get("status", "COMPLETED"),
                "ean": EAN,
                "empresaCodigo": COMPANY_CODE,
                "bodyHash": body_hash,
                "sentAt": datetime.now(timezone.utc).isoformat(),
                "postCount": 1,
                "reexecution": "LOCKED",
                **{k: v for k, v in extra.items() if k != "status"},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    assert_single_post_allowed()

    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    preview = json.loads(BODY_PREVIEW.read_text(encoding="utf-8"))

    if preflight.get("status") != READY:
        raise PilotBlocked(f"Pre-flight não está {READY}: {preflight.get('status')}")
    if preflight.get("blockers"):
        raise PilotBlocked(f"Pre-flight com blockers: {preflight['blockers']}")

    body = preview["body"]
    body_hash = preview["bodyHash"]
    if body.get("codigoBarras") != EAN or body.get("codigoExterno") != EAN:
        raise PilotBlocked("Body divergente do EAN do piloto")
    if "empresaCodigo" in body:
        raise PilotBlocked("Body contém empresaCodigo, proibido no endpoint legado")

    credential = resolve_credential(COMPANY_CODE)
    if credential.variable_name != PROFILE:
        raise PilotBlocked(f"Credencial resolvida fora do profile exigido: {credential.variable_name}")

    print("=" * 78)
    print("PILOTO NEGRESCO — EXECUCAO AUTORIZADA DE UM UNICO POST")
    print("=" * 78)
    print(f"credencial: {credential.variable_name} (nunca impressa)")
    print(f"bodyHash: {body_hash}")

    with httpx.Client(timeout=120.0) as client:
        # Revalidacao dos gates imediatamente antes da escrita.
        guard = company_guard(credential, HttpProductReader(client))
        if not guard.passed:
            raise PilotBlocked("COMPANY_CREDENTIAL_MISMATCH no guard imediatamente antes do POST")
        print(f"guard: sentinel={guard.sentinel_found} vinculo_118508={guard.company_link_confirmed}")

        evidence = find_cost_evidence(EAN, COMPANY_CODE)
        if not evidence.resolved:
            raise PilotBlocked(f"Custo DF-e indisponível: {evidence.status}")
        expected_cost = float(evidence.preco_custo)
        if abs(float(body["precoCusto"]) - expected_cost) > 1e-9:
            raise PilotBlocked(
                f"precoCusto do body ({body['precoCusto']}) divergente do DF-e ({expected_cost})"
            )
        print(f"custo DF-e revalidado: {expected_cost} (NF-e {evidence.numero}/{evidence.serie})")

        # Duplicidade imediata: cursor logo abaixo de um limite alto nao serve, varre tudo.
        reader = HttpProductReader(client)
        cursor = 0
        duplicate: dict[str, Any] | None = None
        scanned = 0
        seen: set[int] = set()
        for _ in range(400):
            batch = reader.get_catalog(credential.key, cursor=cursor, page_size=200)
            if not batch:
                break
            scanned += len(batch)
            for product in batch:
                codes = {
                    str((e.get("codigoBarra") if isinstance(e, dict) else e) or "").strip()
                    for e in product.get("produtoCodigoBarra") or []
                }
                if EAN in codes:
                    duplicate = product
                    break
            if duplicate:
                break
            nxt = max(int(p.get("produtoCodigo") or 0) for p in batch)
            if nxt == cursor or nxt in seen:
                break
            seen.add(nxt)
            cursor = nxt
        if duplicate:
            raise PilotBlocked(f"EAN já existe no catálogo: produtoCodigo {duplicate.get('produtoCodigo')}")
        print(f"duplicidade: nenhuma ({scanned} produtos varridos)")

        # --- POST unico via fachada -------------------------------------
        url = f"{BASE_URL}{LEGACY_ENDPOINT}"
        print()
        print(f"POST {sanitize(url + '?CHAVE=' + credential.key)}")
        service = ProductRegistrationService(OUT_DIR / "_facade_checkpoint.json")
        outcome, response, recovered, transport_error = service.post_product(
            client,
            reader,
            credential.key,
            body,
            ean=EAN,
            from_code=0,
        )
        if response is None and recovered is None:
            write_lock(
                body_hash,
                {"outcome": outcome, "error": transport_error, "status": "PARTIAL"},
            )
            raise PilotBlocked(f"POST falhou: {outcome}:{transport_error}")
        if response is None:
            http_status = 200
            payload = {
                "codProduto": recovered.get("produtoCodigo"),
                "recoveredAfterTimeout": True,
            }
        else:
            http_status = response.status_code
            try:
                payload = response.json()
            except Exception:
                payload = {"raw": (response.text or "")[:400]}

        cod_produto = None
        if isinstance(payload, dict):
            cod_produto = payload.get("codProduto") or payload.get("CODPRODUTO")
        ret = payload.get("RET") if isinstance(payload, dict) else None
        men = payload.get("MEN") if isinstance(payload, dict) else None

        write_lock(body_hash, {"httpStatus": http_status, "codProduto": cod_produto})

        print(f"HTTP {http_status} | RET={ret} | MEN={men} | codProduto={cod_produto}")

        # --- Verificacao obrigatoria do vinculo -------------------------
        verification: dict[str, Any] = {"performed": False}
        classification = "REJECTED"

        if cod_produto:
            code = int(cod_produto)
            links = reader.get_company_links(credential.key, cursor=code - 1, page_size=50)
            matching = [link for link in links if int(link.get("produtoCodigo") or 0) == code]
            company_link = next(
                (link for link in matching if int(link.get("empresaCodigo") or 0) == COMPANY_CODE),
                None,
            )
            catalog_rows = reader.get_catalog(credential.key, cursor=code - 1, page_size=50)
            created = next((p for p in catalog_rows if int(p.get("produtoCodigo") or 0) == code), None)

            verification = {
                "performed": True,
                "produtoCodigo": code,
                "linksFound": [
                    {
                        "empresaCodigo": link.get("empresaCodigo"),
                        "precoVenda": link.get("precoVenda"),
                        "precoCusto": link.get("precoCusto"),
                        "ativo": link.get("ativo"),
                    }
                    for link in matching
                ],
                "companyLinkConfirmed": bool(company_link),
                "catalog": (
                    {
                        "nome": created.get("nome"),
                        "referenciaCodigo": created.get("referenciaCodigo"),
                        "grupoCodigo": created.get("grupoCodigo"),
                        "ncm": created.get("ncm"),
                        "cest": created.get("cest"),
                        "ativo": created.get("ativo"),
                        "tipoProduto": created.get("tipoProduto"),
                        "combustivel": created.get("combustivel"),
                        "produtoCodigoExterno": created.get("produtoCodigoExterno"),
                        "unidadeVenda": created.get("unidadeVenda"),
                    }
                    if created
                    else None
                ),
                "centerSent": COST_CENTER,
                "centerVerifiedByGet": "UNAVAILABLE",
            }

            if company_link:
                classification = "CREATED_AND_VERIFIED"
                print(f"vinculo PRODUTO_EMPRESA: empresa {company_link.get('empresaCodigo')} CONFIRMADO")
                print(
                    f"  precoVenda={company_link.get('precoVenda')} "
                    f"precoCusto={company_link.get('precoCusto')} ativo={company_link.get('ativo')}"
                )
            elif matching:
                classification = "CREATED_IN_WRONG_COMPANY"
                print(
                    f"ALERTA: vinculo em outra empresa: "
                    f"{[link.get('empresaCodigo') for link in matching]}"
                )
            else:
                classification = "ORPHANED_SHARED_CATALOG_RECORD"
                print("ALERTA: produto no catalogo compartilhado sem vinculo PRODUTO_EMPRESA")

        result = {
            "title": "PILOT POST RESULT — NEGRESCO 118508",
            "executedAt": datetime.now(timezone.utc).isoformat(),
            "endpoint": f"POST {LEGACY_ENDPOINT}",
            "urlSanitized": f"{LEGACY_ENDPOINT}?CHAVE=***REDACTED***",
            "routing": "CHAVE_ONLY",
            "empresaCodigoInQuery": "OMITTED",
            "credentialVariable": credential.variable_name,
            "keyExposed": False,
            "ean": EAN,
            "bodyHash": body_hash,
            "postCount": 1,
            "httpStatus": http_status,
            "ret": ret,
            "men": men,
            "codProduto": cod_produto,
            "response": payload,
            "verification": verification,
            "classification": classification,
            "cost": {
                "precoCompra": body["precoCompra"],
                "precoCusto": body["precoCusto"],
                "source": "DFE",
                "invoice": f"{evidence.numero}/{evidence.serie}",
                "accessKeyMasked": evidence.access_key_masked,
            },
            "rollback": "NOT_PERFORMED",
            "correctivePut": "NOT_PERFORMED",
            "delete": "NOT_PERFORMED",
            "nextProduct": "PAUSED_AWAITING_AUTHORIZATION",
        }
        RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

        print()
        print("=" * 78)
        print(f"CLASSIFICACAO: {classification}")
        print("POSTS ENVIADOS: 1")
        print("EXECUCAO PAUSADA — nenhum outro produto sera cadastrado")
        print(f"RESULTADO: {RESULT}")


if __name__ == "__main__":
    try:
        main()
    except PilotBlocked as exc:
        print(f"BLOQUEADO: {exc}")
        print("POSTS ENVIADOS: 0")
        sys.exit(1)
