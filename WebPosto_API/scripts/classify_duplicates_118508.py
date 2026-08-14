"""Classifica os pares retidos por similaridade de descricao (somente leitura).

Separa o que e o mesmo produto com codigo de barras novo, o que e variante e o que e
coincidencia textual. A medida entra aqui como criterio de confirmacao: para gerar o
candidato ela e ignorada, para confirmar duplicidade ela e exigida.

Nao cadastra, nao altera cadastro existente e nao inclui codigo de barras.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.operational.product_registration.company_credentials import (  # noqa: E402
    resolve_credential,
)
from src.operational.product_registration.duplicate_checker import (  # noqa: E402
    FALSE_POSITIVE,
    POSSIBLE_VARIANT,
    SAME_PRODUCT_NEW_GTIN,
    classify_duplicate,
    extract_measure,
    find_description_duplicates,
)
from src.operational.product_registration.fiscal_sheet_loader import load_sheet  # noqa: E402
from src.operational.product_registration.product_family import commercial_family  # noqa: E402

BASE_URL = "https://web.qualityautomacao.com.br"
COMPANY_CODE = 118508
PROFILE = "WEBPOSTO_CONVENIENCIA_24_HORAS_KEY"
SHEET = ROOT / "data" / "product_registration" / "FISCAL_PRODUTOS_A_CADASTRAR_118508.xlsx"
OUT = ROOT / "data" / "product_registration" / "duplicate_review_118508.json"

LABEL_ORDER = {SAME_PRODUCT_NEW_GTIN: 0, POSSIBLE_VARIANT: 1, FALSE_POSITIVE: 2}


def paginate(client: httpx.Client, path: str, key: str) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    cursor = 0
    seen: set[int] = set()
    for _ in range(400):
        params: dict[str, Any] = {"CHAVE": key, "tamanhoPagina": 200}
        if cursor:
            params["ultimoCodigo"] = cursor
        response = client.get(f"{BASE_URL}{path}", params=params)
        response.raise_for_status()
        payload = response.json()
        batch = payload.get("resultados") or []
        collected.extend(batch)
        nxt = int(payload.get("ultimoCodigo") or 0)
        if not batch or not nxt or nxt == cursor or nxt in seen:
            break
        seen.add(nxt)
        cursor = nxt
    return collected


def barcodes(product: dict[str, Any]) -> list[str]:
    values = {
        str((e.get("codigoBarra") if isinstance(e, dict) else e) or "").strip()
        for e in product.get("produtoCodigoBarra") or []
    }
    return sorted(v for v in values if v)


def measure_text(description: str) -> str | None:
    measure = extract_measure(description)
    return f"{measure[0]:g}{measure[1]}" if measure else None


def main() -> None:
    credential = resolve_credential(COMPANY_CODE)
    if credential.variable_name != PROFILE:
        raise SystemExit(f"credencial fora do profile exigido: {credential.variable_name}")

    rows = load_sheet(SHEET)
    with httpx.Client(timeout=120.0) as client:
        catalog = paginate(client, "/INTEGRACAO/PRODUTO", credential.key)
        links = paginate(client, "/INTEGRACAO/PRODUTO_EMPRESA", credential.key)

    linked = {
        int(link.get("produtoCodigo") or 0)
        for link in links
        if int(link.get("empresaCodigo") or 0) == COMPANY_CODE
    }
    existing_barcodes = {code for product in catalog for code in barcodes(product)}

    print("=" * 78)
    print("CLASSIFICACAO DE POSSIVEIS DUPLICADOS — 118508 (READ-ONLY)")
    print("=" * 78)
    print(f"planilha: {len(rows)} | catalogo: {len(catalog)} | vinculos 118508: {len(linked)}")
    print()

    results: list[dict[str, Any]] = []
    for row in rows:
        if not row.ean_valid or row.ean in existing_barcodes:
            continue
        matches = find_description_duplicates(row.descricao, catalog)
        if not matches:
            continue
        candidate_family = commercial_family(row.descricao)
        classified = []
        for product in matches[:5]:
            existing_family = commercial_family(product.get("nome") or "")
            label, reason = classify_duplicate(
                row.descricao,
                product.get("nome") or "",
                candidate_family=candidate_family,
                existing_family=existing_family,
            )
            classified.append(
                {
                    "classificacao": label,
                    "motivo": reason,
                    "produtoCodigo": product.get("produtoCodigo"),
                    "nome": product.get("nome"),
                    "medida": measure_text(product.get("nome") or ""),
                    "familiaComercial": existing_family,
                    "ncm": product.get("ncm"),
                    "cest": product.get("cest"),
                    "codigosBarra": barcodes(product),
                    "vinculadoA118508": int(product.get("produtoCodigo") or 0) in linked,
                }
            )
        # A classificacao do par mais forte define o caso: se algum cadastro existente e o
        # mesmo produto, o candidato nao pode ser cadastrado de novo.
        classified.sort(key=lambda c: LABEL_ORDER[c["classificacao"]])
        results.append(
            {
                "linha": row.line,
                "ean": row.ean,
                "descricao": row.descricao,
                "medida": measure_text(row.descricao),
                "familiaComercial": candidate_family,
                "ncmPlanilha": row.ncm,
                "cestPlanilha": row.cest,
                "precoVenda": row.preco_venda,
                "classificacao": classified[0]["classificacao"],
                "motivo": classified[0]["motivo"],
                "cadastrosExistentes": classified,
                "acao": "NAO_CADASTRAR",
            }
        )

    by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in results:
        by_label[item["classificacao"]].append(item)

    for label in (SAME_PRODUCT_NEW_GTIN, POSSIBLE_VARIANT, FALSE_POSITIVE):
        items = by_label.get(label) or []
        print(f"{label} — {len(items)} produto(s)")
        for item in items:
            existing = item["cadastrosExistentes"][0]
            print(f"   linha {item['linha']:>4} | {item['ean']} | {item['descricao'][:44]}")
            print(f"        medida planilha {item['medida'] or 'ausente'} | "
                  f"cadastro {existing['produtoCodigo']} '{(existing['nome'] or '')[:40]}' "
                  f"medida {existing['medida'] or 'ausente'}")
            print(f"        {item['motivo']}")
        print()

    payload = {
        "title": "REVISAO DE POSSIVEIS DUPLICADOS — 118508",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sheet": SHEET.name,
        "empresa": COMPANY_CODE,
        "criterio": {
            "candidato": "similaridade de termos distintivos, medida ignorada",
            "confirmacao": "medida exigida nos dois lados; ausencia nao confirma",
            "acaoPermitida": "nenhuma; decisao do proprietario",
        },
        "totais": {label: len(by_label.get(label) or []) for label in LABEL_ORDER},
        "produtos": results,
        "apiWrites": 0,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 78)
    print(f"TOTAL RETIDO: {len(results)} | API WRITES: 0")
    print(f"artefato: {OUT}")


if __name__ == "__main__":
    main()
