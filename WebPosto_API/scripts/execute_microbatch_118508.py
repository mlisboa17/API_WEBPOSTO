"""Executa o microbatch autorizado da empresa 118508, um POST por vez.

Cada produto passa por verificacao individual em PRODUTO_EMPRESA antes do proximo.
Qualquer divergencia interrompe o lote imediatamente. Nenhum produto fora do preflight
aprovado pode ser enviado.

Uso: python scripts/execute_microbatch_118508.py --batch 02

Nao imprime credencial. Nao envia empresaCodigo. Sem PUT, PATCH, DELETE ou rollback.
"""

from __future__ import annotations

import argparse
import json
import os
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

BASE_URL = "https://web.qualityautomacao.com.br"
LEGACY_ENDPOINT = "/INTEGRACAO/INCLUIR_PRODUTO"
COMPANY_CODE = 118508
PROFILE = "WEBPOSTO_CONVENIENCIA_24_HORAS_KEY"
COST_CENTER = 24886
MAX_BATCH = 5

REGISTRATION_DIR = ROOT / "data" / "product_registration"
CHECKPOINT = REGISTRATION_DIR / "execution" / "checkpoint_118508.json"
ACCOUNTANT_REVIEW = REGISTRATION_DIR / "accountant_review_118508.json"
PENDING_COST_UPDATE = REGISTRATION_DIR / "pending_cost_update_118508.json"

# Cada lote tem seu proprio preflight e sua propria trava de reexecucao.
BATCHES = {
    "01": ("microbatch_01_118508", "preflight_microbatch.json"),
    "02": ("microbatch_02_118508", "microbatch_selection.json"),
    "03": ("microbatch_03_118508", "pilot_selection.json"),
}

# Custo zero so passa com autorizacao explicita por variavel de ambiente da execucao,
# nunca gravada no .env. Sem a flag, o executor recusa custo zero como antes.
PENDING_COST_FLAG = "ALLOW_PENDING_DFE_COST"
PENDING_COST_STATUS = "PENDING"

BLOCKED_EANS = {"7891000376928", "7891962076317", "7891000377130"}
BLOCKED_CODES = {2481160, 2481344, 2481443}
READY_CATEGORIES = {"READY_FOR_WRITE", "READY_HIGH_CONFIDENCE", "READY_ASSUMED_RISK"}


class BatchHalted(Exception):
    """Interrompe o lote sem enviar mais nenhum POST."""


def load_json(path: Path, default: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def save_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def barcodes(product: dict[str, Any]) -> set[str]:
    values = {
        str((e.get("codigoBarra") if isinstance(e, dict) else e) or "").strip()
        for e in product.get("produtoCodigoBarra") or []
    }
    external = product.get("produtoCodigoExterno")
    if external:
        values.add(str(external).strip())
    return {v for v in values if v}


def pending_cost_allowed() -> bool:
    """Autorizacao de custo zero, valida apenas para o processo atual."""
    return os.environ.get(PENDING_COST_FLAG, "").strip().lower() == "true"


def validate_cost(cost: Any, product: dict[str, Any]) -> tuple[bool, str]:
    """Aprova o custo do body.

    Custo positivo exige origem em DF-e. Custo zero e aceito somente quando o produto
    esta declarado como pendente de DF-e e a flag de autorizacao esta presente nesta
    execucao: assim o padrao continua sendo a recusa.
    """
    if cost is None:
        return False, "CUSTO_AUSENTE"
    cost = float(cost)
    if cost < 0:
        return False, "CUSTO_NEGATIVO"
    if cost > 0:
        if (product.get("custo") or {}).get("source") not in ("DFE", None):
            return False, "CUSTO_POSITIVO_SEM_ORIGEM_DFE"
        return True, "CUSTO_DFE"
    if (product.get("custo") or {}).get("cost_status") != PENDING_COST_STATUS:
        return False, "CUSTO_ZERO_SEM_STATUS_PENDENTE"
    if not pending_cost_allowed():
        return False, "CUSTO_ZERO_SEM_AUTORIZACAO_EXPLICITA"
    return True, "CUSTO_ZERO_AUTORIZADO"


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa um microbatch autorizado da 118508")
    parser.add_argument("--batch", default="01", choices=sorted(BATCHES))
    args = parser.parse_args()

    folder, preflight_name = BATCHES[args.batch]
    out_dir = REGISTRATION_DIR / folder
    preflight_path = out_dir / preflight_name
    result_path = out_dir / "execution_result.json"
    batch_lock = out_dir / "batch_lock.json"

    if batch_lock.is_file():
        lock = load_json(batch_lock, {})
        raise BatchHalted(
            f"Microbatch {args.batch} já executado em {lock.get('executedAt')} "
            f"({lock.get('postCount')} POSTs). Nova execução recusada."
        )

    preflight = load_json(preflight_path, {})
    if preflight.get("status") != "READY_FOR_WRITE":
        raise BatchHalted(f"Pre-flight não aprovado: {preflight.get('status')}")

    products = [
        p
        for p in preflight.get("products", [])
        if (p.get("status") or p.get("categoria")) in READY_CATEGORIES
    ]
    if not products:
        raise BatchHalted("Nenhum produto aprovado no pre-flight")
    if len(products) > MAX_BATCH:
        raise BatchHalted(f"Lote com {len(products)} produtos excede o limite de {MAX_BATCH}")
    for product in products:
        if product["ean"] in BLOCKED_EANS:
            raise BatchHalted(f"EAN permanentemente excluído no lote: {product['ean']}")

    credential = resolve_credential(COMPANY_CODE)
    if credential.variable_name != PROFILE:
        raise BatchHalted(f"Credencial fora do profile exigido: {credential.variable_name}")

    checkpoint = load_json(CHECKPOINT, {})
    review = load_json(ACCOUNTANT_REVIEW, {})
    pending_cost = load_json(PENDING_COST_UPDATE, {})

    print("=" * 78)
    print(f"MICROBATCH {args.batch} — EMPRESA {COMPANY_CODE} — {len(products)} PRODUTOS")
    print("=" * 78)
    print(f"credencial: {credential.variable_name} (nunca impressa)")

    executed: list[dict[str, Any]] = []
    halted_reason: str | None = None
    post_count = 0

    with httpx.Client(timeout=120.0) as client:
        reader = HttpProductReader(client)

        guard = company_guard(credential, reader)
        if not guard.passed:
            raise BatchHalted("Sentinel BONO não confirmado na empresa 118508")
        print(f"sentinel BONO: encontrado={guard.sentinel_found} vinculo={guard.company_link_confirmed}")

        catalog = reader.get_catalog(credential.key, cursor=0, page_size=200)
        cursor = 0
        seen: set[int] = set()
        all_codes: dict[str, int] = {}
        while catalog:
            for entry in catalog:
                code = int(entry.get("produtoCodigo") or 0)
                for bar in barcodes(entry):
                    all_codes.setdefault(bar, code)
            nxt = max(int(p.get("produtoCodigo") or 0) for p in catalog)
            if nxt == cursor or nxt in seen:
                break
            seen.add(nxt)
            cursor = nxt
            catalog = reader.get_catalog(credential.key, cursor=cursor, page_size=200)
        print(f"catalogo indexado: {len(all_codes)} codigos de barras")
        print()

        for product in products:
            ean = product["ean"]
            body = product["body"]["preview"]
            expected_hash = product["body"]["hash"]

            print(f"--- {ean} — {product['descricao']}")

            if ean in checkpoint:
                halted_reason = f"CHECKPOINT_JA_EXISTE:{ean}"
                break
            if ean in all_codes:
                halted_reason = f"DUPLICADO_NO_CATALOGO:{ean}->{all_codes[ean]}"
                break
            if "empresaCodigo" in body:
                halted_reason = f"BODY_COM_EMPRESA_CODIGO:{ean}"
                break
            if body["codigoBarras"] != ean or body["codigoExterno"] != ean:
                halted_reason = f"BODY_DIVERGENTE_DO_EAN:{ean}"
                break
            if not body["precoVenda"] or body["precoVenda"] <= 0:
                halted_reason = f"PRECO_VENDA_INVALIDO:{ean}"
                break
            cost_ok, cost_reason = validate_cost(body.get("precoCusto"), product)
            if not cost_ok:
                halted_reason = f"{cost_reason}:{ean}"
                break

            print(
                f"    custo {body['precoCusto']} ({cost_reason}) | venda {body['precoVenda']}"
                f" | hash {expected_hash[:16]}..."
            )

            response = client.post(
                f"{BASE_URL}{LEGACY_ENDPOINT}",
                params={"CHAVE": credential.key},
                content=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
            post_count += 1
            http_status = response.status_code
            try:
                payload = response.json()
            except Exception:
                payload = {"raw": (response.text or "")[:400]}

            ret = payload.get("RET") if isinstance(payload, dict) else None
            men = payload.get("MEN") if isinstance(payload, dict) else None
            cod_produto = payload.get("codProduto") if isinstance(payload, dict) else None
            print(f"    POST -> HTTP {http_status} | RET={ret} | MEN={men} | codProduto={cod_produto}")

            record: dict[str, Any] = {
                "ean": ean,
                "descricao": product["descricao"],
                "httpStatus": http_status,
                "ret": ret,
                "men": men,
                "codProduto": cod_produto,
                "bodyHash": expected_hash,
                "response": payload,
            }

            if http_status != 200:
                record["classification"] = "HTTP_INESPERADO"
                executed.append(record)
                halted_reason = f"HTTP_INESPERADO:{http_status}"
                break
            if ret not in (None, 0, "0"):
                record["classification"] = "RET_NAO_SUCESSO"
                executed.append(record)
                halted_reason = f"RET_NAO_SUCESSO:{ret}"
                break
            if not cod_produto:
                record["classification"] = "SEM_CODPRODUTO"
                executed.append(record)
                halted_reason = "SEM_CODPRODUTO"
                break

            code = int(cod_produto)
            if code in BLOCKED_CODES:
                record["classification"] = "CODIGO_BLOQUEADO_RETORNADO"
                executed.append(record)
                halted_reason = f"CODIGO_BLOQUEADO_RETORNADO:{code}"
                break

            # Verificacao individual obrigatoria
            links = reader.get_company_links(credential.key, cursor=code - 1, page_size=50)
            matching = [l for l in links if int(l.get("produtoCodigo") or 0) == code]
            company_link = next(
                (l for l in matching if int(l.get("empresaCodigo") or 0) == COMPANY_CODE), None
            )
            rows = reader.get_catalog(credential.key, cursor=code - 1, page_size=50)
            created = next((p for p in rows if int(p.get("produtoCodigo") or 0) == code), None)

            record["verification"] = {
                "produtoCodigo": code,
                "links": [
                    {
                        "empresaCodigo": l.get("empresaCodigo"),
                        "precoVenda": l.get("precoVenda"),
                        "precoCusto": l.get("precoCusto"),
                        "ativo": l.get("ativo"),
                    }
                    for l in matching
                ],
                "companyLinkConfirmed": bool(company_link),
                "catalog": (
                    {
                        "nome": created.get("nome"),
                        "referenciaCodigo": created.get("referenciaCodigo"),
                        "ncm": created.get("ncm"),
                        "cest": created.get("cest"),
                        "grupoCodigo": created.get("grupoCodigo"),
                        "produtoCodigoExterno": created.get("produtoCodigoExterno"),
                    }
                    if created
                    else None
                ),
                "centerSent": COST_CENTER,
            }

            if not company_link:
                record["classification"] = (
                    "CREATED_IN_WRONG_COMPANY" if matching else "ORPHANED_SHARED_CATALOG_RECORD"
                )
                executed.append(record)
                halted_reason = record["classification"]
                print(f"    ALERTA: {record['classification']}")
                break

            # Divergencia entre o enviado e o lido
            divergences = []
            if abs(float(company_link.get("precoVenda") or 0) - float(body["precoVenda"])) > 0.005:
                divergences.append("precoVenda")
            if abs(float(company_link.get("precoCusto") or 0) - float(body["precoCusto"])) > 0.005:
                divergences.append("precoCusto")
            if created and str(created.get("ncm") or "") != str(body["codigoNcm"]):
                divergences.append("ncm")
            if created and str(created.get("cest") or "") != str(body["codigoCest"]):
                divergences.append("cest")
            if created and ean not in barcodes(created):
                divergences.append("codigoBarras")
            record["verification"]["divergences"] = divergences

            if divergences:
                record["classification"] = "DIVERGENCIA_BODY_VS_LIDO"
                executed.append(record)
                halted_reason = f"DIVERGENCIA:{','.join(divergences)}"
                print(f"    ALERTA: divergência em {divergences}")
                break

            record["classification"] = "CREATED_AND_VERIFIED"
            executed.append(record)
            print(
                f"    verificado: empresa {company_link.get('empresaCodigo')} | "
                f"venda {company_link.get('precoVenda')} | custo {company_link.get('precoCusto')} | "
                f"ativo {company_link.get('ativo')} | ref {record['verification']['catalog']['referenciaCodigo']}"
            )

            basis = product["baseFiscal"]
            cost_info = product.get("custo") or {}
            nfe = cost_info.get("nfe") or {}
            entry_tax = product.get("tributacaoEntrada") or {}
            equivalents = product.get("equivalentes") or {}
            checkpoint[ean] = {
                "status": "CREATED_AND_VERIFIED",
                "codProduto": code,
                "referenciaCodigo": record["verification"]["catalog"]["referenciaCodigo"],
                "descricao": product["descricao"],
                "body_hash": expected_hash,
                "empresa_pretendida": COMPANY_CODE,
                "empresa_efetiva": int(company_link.get("empresaCodigo") or 0),
                "credencial_usada": credential.variable_name,
                "preco_venda": company_link.get("precoVenda"),
                "preco_custo": company_link.get("precoCusto"),
                "cost_source": cost_info.get("source") or "DFE",
                "cost_status": cost_info.get("cost_status") or "RESOLVED",
                "cost_risk": cost_info.get("cost_risk"),
                "requires_cost_update": cost_info.get("requires_cost_update", False),
                "dfe_invoice": f"{nfe.get('numero')}/{nfe.get('serie')}" if nfe else None,
                "precoCusto": body["precoCusto"],
                "icms_table_reference": basis["icmsTableReference"],
                "pis_cofins_table_reference": basis["pisCofinsTableReference"],
                "confidence": basis["confidence"],
                "fiscal_risk": basis["fiscalRisk"],
                "requires_accountant_review": basis["requiresAccountantReview"],
                "rollback": "NOT_PERFORMED",
                "bloqueio": "Cadastrado e verificado. Nao reenviar.",
            }
            save_json(CHECKPOINT, checkpoint)

            if basis["requiresAccountantReview"]:
                review[ean] = {
                    "ean": ean,
                    "descricao": product["descricao"],
                    "produtoCodigo": code,
                    "ncm": body["codigoNcm"],
                    "cest": body["codigoCest"],
                    "baseUsada": {
                        "icmsTableReference": basis["icmsTableReference"],
                        "tributoIcms": body["tributoIcms"],
                        "pisCofinsTableReference": basis["pisCofinsTableReference"],
                        "tributoPisCofins": body["tributoPisCofins"],
                        "cfopEntrada": body["cdCfopEntrada"],
                        "cfopSaida": body["cdCfopSaida"],
                    },
                    "evidencias": {
                        "classificacaoEntrada": basis.get("classificacao")
                        or basis.get("classificacaoEntrada"),
                        "cstIcmsEntrada": entry_tax.get("cstIcms") or basis.get("cstIcmsEntrada"),
                        "aliquotaIcmsEntrada": entry_tax.get("aliquotaIcmsEntrada")
                        or basis.get("aliquotaIcmsEntrada"),
                        "icmsDestacado": entry_tax.get("icmsDestacado"),
                        "icmsStRetido": entry_tax.get("icmsStRetido")
                        or basis.get("icmsStRetido"),
                        "nfe": f"{nfe.get('numero')}/{nfe.get('serie')}",
                        "nfeAccessKeyMasked": nfe.get("accessKeyMasked"),
                        "fornecedor": nfe.get("fornecedor"),
                        "equivalentesMesmoNcmCest": equivalents.get("mesmoNcmCest"),
                        "distribuicaoMensuravel": equivalents.get("distribuicaoMensuravel"),
                        "motivoNaoMensuravel": equivalents.get("motivoNaoMensuravel"),
                    },
                    "confidence": basis["confidence"],
                    "fiscal_risk": basis["fiscalRisk"],
                    "requires_accountant_review": True,
                    "justificativa": basis["justificativa"],
                    "criadoEm": datetime.now(timezone.utc).isoformat(),
                }
                save_json(ACCOUNTANT_REVIEW, review)

            if cost_info.get("requires_cost_update"):
                pending_cost[ean] = {
                    "ean": ean,
                    "descricao": product["descricao"],
                    "produtoCodigo": code,
                    "referenciaCodigo": record["verification"]["catalog"]["referenciaCodigo"],
                    "precoCustoCadastrado": body["precoCusto"],
                    "precoVenda": body["precoVenda"],
                    "cost_source": cost_info.get("source"),
                    "cost_status": cost_info.get("cost_status"),
                    "cost_risk": cost_info.get("cost_risk"),
                    "requires_cost_update": True,
                    "motivo": cost_info.get("motivoRevisao")
                    or "Sem NF-e de entrada autorizada com o EAN no armazenamento de DF-e",
                    "acaoNecessaria": (
                        "Atualizar custo quando a NF-e de compra entrar no DF-e. "
                        "Correcao de cadastro existente depende de operacao de escrita "
                        "hoje proibida (PUT)."
                    ),
                    "criadoEm": datetime.now(timezone.utc).isoformat(),
                }
                save_json(PENDING_COST_UPDATE, pending_cost)
            print()

    created_count = sum(1 for r in executed if r.get("classification") == "CREATED_AND_VERIFIED")
    save_json(
        batch_lock,
        {
            "executedAt": datetime.now(timezone.utc).isoformat(),
            "postCount": post_count,
            "createdAndVerified": created_count,
            "haltedReason": halted_reason,
        },
    )
    save_json(
        result_path,
        {
            "title": f"MICROBATCH {args.batch} EXECUTION — 118508",
            "executedAt": datetime.now(timezone.utc).isoformat(),
            "endpoint": f"POST {LEGACY_ENDPOINT}",
            "urlSanitized": f"{LEGACY_ENDPOINT}?CHAVE=***REDACTED***",
            "routing": "CHAVE_ONLY",
            "empresaCodigoInQuery": "OMITTED",
            "credentialVariable": credential.variable_name,
            "keyExposed": False,
            "postCount": post_count,
            "createdAndVerified": created_count,
            "haltedReason": halted_reason,
            "products": executed,
            "rollback": "NOT_PERFORMED",
            "nextBatch": "PAUSED_AWAITING_AUTHORIZATION",
        },
    )

    print("=" * 78)
    print(f"POSTS ENVIADOS: {post_count}")
    print(f"CRIADOS E VERIFICADOS: {created_count}/{len(products)}")
    print(f"INTERROMPIDO POR: {halted_reason or 'NADA — lote concluido'}")
    print("PROXIMO LOTE: PAUSADO aguardando autorizacao")
    print(f"resultado: {result_path}")


if __name__ == "__main__":
    try:
        main()
    except BatchHalted as exc:
        print(f"LOTE NAO EXECUTADO: {exc}")
        print("POSTS ENVIADOS: 0")
        sys.exit(1)
