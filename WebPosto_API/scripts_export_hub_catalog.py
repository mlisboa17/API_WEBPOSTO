"""Gera o catálogo do hub de consultas: api_hub_get_catalog.json e api_hub_catalog.js.

Uso (na pasta do projeto):
    python scripts_export_hub_catalog.py

O dashboard carrega api_hub_catalog.js (window.API_HUB_CATALOGO) ao lado do HTML.
"""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("ec", ROOT / "explorador_catalog.py")
ec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ec)

EXTRAS = [
    {
        "categoria": "Financeiro",
        "nome": "Cartão — remessa",
        "method": "GET",
        "path": "/INTEGRACAO/CARTAO_REMESSA",
        "dates": True,
        "pag": True,
        "fil": True,
    },
    {
        "categoria": "Financeiro",
        "nome": "Cartão — a pagar",
        "method": "GET",
        "path": "/INTEGRACAO/CARTAO_PAGAR",
        "dates": True,
        "pag": True,
        "fil": True,
    },
    {
        "categoria": "Financeiro",
        "nome": "Cartão — compra",
        "method": "GET",
        "path": "/INTEGRACAO/CARTAO_COMPRA",
        "dates": True,
        "pag": True,
        "fil": True,
    },
]


def norm(e):
    o = {
        "categoria": e.get("categoria") or "Outros",
        "nome": e.get("nome") or e.get("path", "").split("/")[-1],
        "path": e["path"],
        "dates": bool(e.get("dates")),
        "pag": bool(e.get("pag")),
        "fil": bool(e.get("fil")),
    }
    p = o["path"]
    if p == "/INTEGRACAO/ABASTECIMENTO" or p == "/INTEGRACAO/CAIXA_APRESENTADO":
        o["cursor"] = True
    if p == "/INTEGRACAO/FINANCEIRO_EXCLUSAO":
        o["pag"] = True
    return o


def main():
    seen = set()
    out = []
    for e in list(ec.ENDPOINTS) + EXTRAS:
        if e.get("method") != "GET":
            continue
        p = e.get("path", "")
        if "{" in p:
            continue
        if not p.startswith("/INTEGRACAO/"):
            continue
        if p in seen:
            continue
        seen.add(p)
        out.append(norm(e))
    out.sort(key=lambda x: (x["categoria"], x["nome"]))
    dest_json = ROOT / "api_hub_get_catalog.json"
    dest_json.write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    dest_js = ROOT / "api_hub_catalog.js"
    payload = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    dest_js.write_text("window.API_HUB_CATALOGO = " + payload + ";\n", encoding="utf-8")

    print(dest_json, len(out), "GETs")
    print(dest_js, "atualizado")


if __name__ == "__main__":
    main()
