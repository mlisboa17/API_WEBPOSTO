"""Verificacao independente dos produtos criados em um microbatch (somente leitura).

Confere, produto por produto, os sete campos exigidos apos cada POST: empresaCodigo,
ativo, EAN, NCM, CEST, preco de venda e preco de custo. A leitura e feita de novo na API,
sem reaproveitar a resposta do POST.

Uso: python scripts/verify_microbatch_118508.py --batch 02
"""

from __future__ import annotations

import argparse
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
    resolve_credential,
)

COMPANY_CODE = 118508
PROFILE = "WEBPOSTO_CONVENIENCIA_24_HORAS_KEY"
REGISTRATION_DIR = ROOT / "data" / "product_registration"
BATCH_FOLDERS = {
    "01": "microbatch_01_118508",
    "02": "microbatch_02_118508",
    "03": "microbatch_03_118508",
    "04": "microbatch_04_118508",
    "05": "microbatch_05_118508",
}
PREFLIGHT_NAMES = {
    "01": "preflight_microbatch.json",
    "02": "microbatch_selection.json",
    "03": "pilot_selection.json",
    "04": "microbatch_selection.json",
    "05": "microbatch_selection.json",
}
TOLERANCE = 0.005


def main() -> None:
    parser = argparse.ArgumentParser(description="Verifica os produtos criados em um microbatch")
    parser.add_argument("--batch", default="02", choices=sorted(BATCH_FOLDERS))
    args = parser.parse_args()

    out_dir = REGISTRATION_DIR / BATCH_FOLDERS[args.batch]
    execution = json.loads((out_dir / "execution_result.json").read_text(encoding="utf-8"))
    preflight = json.loads(
        (out_dir / PREFLIGHT_NAMES[args.batch]).read_text(encoding="utf-8")
    )
    expected = {p["ean"]: p for p in preflight.get("products", [])}

    credential = resolve_credential(COMPANY_CODE)
    if credential.variable_name != PROFILE:
        raise SystemExit(f"credencial fora do profile exigido: {credential.variable_name}")

    created = [
        r for r in execution.get("products", []) if r.get("classification") == "CREATED_AND_VERIFIED"
    ]

    print("=" * 78)
    print(f"VERIFICACAO INDEPENDENTE — MICROBATCH {args.batch} — {len(created)} PRODUTOS")
    print("=" * 78)
    print(f"credencial: {credential.variable_name} (nunca impressa)")
    print()

    findings: list[dict[str, Any]] = []
    all_ok = True

    with httpx.Client(timeout=120.0) as client:
        reader = HttpProductReader(client)
        for record in created:
            code = int(record["codProduto"])
            ean = record["ean"]
            body = expected[ean]["body"]["preview"]

            links = reader.get_company_links(credential.key, cursor=code - 1, page_size=50)
            link = next(
                (
                    l
                    for l in links
                    if int(l.get("produtoCodigo") or 0) == code
                    and int(l.get("empresaCodigo") or 0) == COMPANY_CODE
                ),
                None,
            )
            rows = reader.get_catalog(credential.key, cursor=code - 1, page_size=50)
            product = next((p for p in rows if int(p.get("produtoCodigo") or 0) == code), None)

            barcodes = {
                str((e.get("codigoBarra") if isinstance(e, dict) else e) or "").strip()
                for e in (product or {}).get("produtoCodigoBarra") or []
            }

            checks = {
                "empresaCodigo": bool(link) and int(link.get("empresaCodigo")) == COMPANY_CODE,
                "ativo": bool(link) and bool(link.get("ativo")),
                "ean": ean in barcodes,
                "ncm": str((product or {}).get("ncm") or "") == str(body["codigoNcm"]),
                "cest": str((product or {}).get("cest") or "") == str(body["codigoCest"]),
                "precoVenda": bool(link)
                and abs(float(link.get("precoVenda") or 0) - float(body["precoVenda"])) <= TOLERANCE,
                "precoCusto": bool(link)
                and abs(float(link.get("precoCusto") or 0) - float(body["precoCusto"])) <= TOLERANCE,
            }
            failed = [name for name, ok in checks.items() if not ok]
            all_ok = all_ok and not failed

            print(f"--- produto {code} | {ean} | {record['descricao']}")
            print(
                f"    empresa {link.get('empresaCodigo') if link else None} | ativo "
                f"{link.get('ativo') if link else None} | venda {link.get('precoVenda') if link else None}"
                f" | custo {link.get('precoCusto') if link else None}"
            )
            print(
                f"    NCM {(product or {}).get('ncm')} | CEST {(product or {}).get('cest')}"
                f" | EAN no cadastro: {ean in barcodes} | ref {(product or {}).get('referenciaCodigo')}"
            )
            print(f"    {'TODOS OS 7 CAMPOS CONFEREM' if not failed else 'DIVERGENCIA EM ' + str(failed)}")
            print()

            findings.append(
                {
                    "produtoCodigo": code,
                    "ean": ean,
                    "descricao": record["descricao"],
                    "empresaCodigo": link.get("empresaCodigo") if link else None,
                    "ativo": link.get("ativo") if link else None,
                    "ncm": (product or {}).get("ncm"),
                    "cest": (product or {}).get("cest"),
                    "referenciaCodigo": (product or {}).get("referenciaCodigo"),
                    "precoVenda": link.get("precoVenda") if link else None,
                    "precoCusto": link.get("precoCusto") if link else None,
                    "checks": checks,
                    "divergencias": failed,
                }
            )

    payload = {
        "title": f"VERIFICACAO INDEPENDENTE MICROBATCH {args.batch} — 118508",
        "verifiedAt": datetime.now(timezone.utc).isoformat(),
        "apiWrites": 0,
        "productsVerified": len(findings),
        "allFieldsMatch": all_ok,
        "findings": findings,
    }
    (out_dir / "independent_verification.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("=" * 78)
    print(f"RESULTADO: {'TODOS OS PRODUTOS CONFEREM' if all_ok else 'HA DIVERGENCIAS'}")
    print("API WRITES: 0")
    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
