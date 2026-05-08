#!/usr/bin/env python3
"""
Gera mapeamento entre `WebPosto_API/api_hub_get_catalog.json`
e o código do repositório procurando referências aos paths.

Cria dois artefatos em `WebPosto_API/`:
- `webposto_mapping.md` (relatório legível)
- `webposto_mapping.json` (dados estruturados)

Uso:
    python scripts/map_webposto.py

"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "WebPosto_API" / "api_hub_get_catalog.json"
OUT_MD = ROOT / "WebPosto_API" / "webposto_mapping.md"
OUT_JSON = ROOT / "WebPosto_API" / "webposto_mapping.json"

SEARCH_EXT = {".py", ".md", ".js", ".jsx", ".ts", ".json", ".html"}


def load_catalog(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_references(pattern: str, root: Path):
    found = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.suffix.lower() not in SEARCH_EXT:
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if pattern in text:
                found.append(str(p.relative_to(root)))
    return sorted(found)


def main():
    if not CATALOG.exists():
        print("Catálogo não encontrado:", CATALOG)
        return

    catalog = load_catalog(CATALOG)
    mapping = []

    for item in catalog:
        path = item.get("path")
        files = find_references(path, ROOT)
        mapping.append(
            {
                "categoria": item.get("categoria"),
                "nome": item.get("nome"),
                "path": path,
                "found": bool(files),
                "files": files,
                "meta": {
                    k: v
                    for k, v in item.items()
                    if k not in ("categoria", "nome", "path")
                },
            }
        )

    # salvar JSON
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)

    # criar Markdown
    lines = []
    lines.append("# Mapeamento webPosto — API vs Código\n")
    lines.append(f"Total endpoints no catálogo: {len(mapping)}\n")

    implemented = sum(1 for m in mapping if m["found"])
    lines.append(f"Endpoints encontrados no código: {implemented}\n")
    lines.append("---\n")

    for m in mapping:
        status = "✅ Implementado" if m["found"] else "❌ Não encontrado"
        lines.append(f"- **{m['path']}** — {status}  ")
        lines.append(f"  - Nome: {m['nome']}  ")
        if m["found"]:
            for f in m["files"]:
                lines.append(f"    - {f}")
        lines.append("\n")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print("Mapeamento gerado:", OUT_MD)
    print("Dados JSON:", OUT_JSON)


if __name__ == "__main__":
    main()
