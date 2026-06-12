#!/usr/bin/env python3
"""Gera relatórios F07.3 Product Master Optimization."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f07_3_product_master_optimization.json"


def _load() -> dict:
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def _w(name: str, body: str) -> None:
    p = ROOT / name
    p.write_text(body, encoding="utf-8")
    print(f"Wrote {p}")


def main() -> None:
    data = _load()
    w = data.get("windows", {}).get("7d") or {}
    ex = w.get("executiveAnswers") or {}
    forensics = w.get("residualSkuForensics") or {}
    opt = w.get("productLookupOptimization") or {}
    cache = w.get("productCacheStrategy") or {}
    dept = w.get("departmentRefinement") or {}
    scale = w.get("multiBranchProductScale") or {}
    bench = w.get("productPerformanceBenchmark") or {}
    cockpit = w.get("cockpit") or {}
    qa = w.get("qa") or {}
    cov = w.get("productMasterCoverage") or {}
    parecer = w.get("parecerFinal") or ""

    _w(
        "RESIDUAL_SKU_FORENSICS_REPORT.md",
        f"# IA-1 — Residual SKU Forensics\n\n"
        f"- Produto: **{forensics.get('produtoCodigo')}**\n"
        f"- Classificação: **{forensics.get('classificacaoFinal')}**\n"
        f"- Nome: **{forensics.get('nomeResolvido')}**\n"
        f"- Departamento: **{forensics.get('departamento')}**\n"
        f"- Ocorrências VENDA_ITEM: **{forensics.get('vendaItemOcorrencias')}**\n",
    )
    _w(
        "PRODUCT_LOOKUP_OPTIMIZATION_REPORT.md",
        f"# IA-2 — Product Lookup Optimization\n\n"
        f"- Concorrência: **{opt.get('concurrency')}**\n"
        f"- Timeout: **{opt.get('timeoutSec')}s**\n"
        f"- Paralelo PRODUTO+PE: **{opt.get('parallelProdutoProdutoEmpresa')}**\n"
        f"- Cache: **{opt.get('cacheEnabled')}**\n"
        f"- Lookup depois: **{bench.get('tempoTotalLookupDepoisSec')}s**\n"
        f"- Redução: **{bench.get('reducaoPercentual')}%**\n",
    )
    _w(
        "PRODUCT_CACHE_STRATEGY_REPORT.md",
        f"# IA-3 — Product Cache Strategy\n\n"
        f"- Index size: **{cache.get('indexSize')}**\n"
        f"- Hits: **{cache.get('cacheHits')}**\n"
        f"- Misses: **{cache.get('cacheMisses')}**\n"
        f"- Hit rate: **{cache.get('cacheHitRatePct')}%**\n"
        f"- Path: `{cache.get('cachePath')}`\n",
    )
    _w(
        "DEPARTMENT_REFINEMENT_REPORT.md",
        f"# IA-4 — Department Refinement\n\n"
        f"- Refinados: **{dept.get('departamentosRefinados')}**\n"
        f"- NAO_CLASSIFICADO catálogo: **{dept.get('produtosNaoClassificados')}**\n"
        f"- NAO_CLASSIFICADO vendidos: **{dept.get('produtosVendidosNaoClassificados')}**\n"
        f"- Categoria inventada: **{dept.get('categoriaInventada')}**\n",
    )
    _w(
        "MULTI_BRANCH_PRODUCT_SCALE_REPORT.md",
        f"# IA-5 — Multi-Branch Product Scale\n\n"
        f"- Catálogo corporativo: **{scale.get('catalogoCorporativo')}**\n"
        f"- Por filial: **{scale.get('catalogoPorFilial')}**\n"
        f"- Pronto N filiais: **{scale.get('prontoParaNFiliais')}**\n",
    )
    _w(
        "PRODUCT_PERFORMANCE_BENCHMARK_REPORT.md",
        f"# IA-6 — Performance Benchmark\n\n"
        f"- Antes: **{bench.get('tempoTotalLookupAntesSec')}s**\n"
        f"- Depois: **{bench.get('tempoTotalLookupDepoisSec')}s**\n"
        f"- Redução: **{bench.get('reducaoPercentual')}%**\n"
        f"- Lookups: **{bench.get('lookupsExecutados')}**\n"
        f"- Timeouts: **{bench.get('timeouts')}**\n"
        f"- Erros: **{bench.get('errors')}**\n",
    )
    _w(
        "PRODUCT_COCKPIT_REFINEMENT_REPORT.md",
        f"# IA-7 — Cockpit Refinement\n\n"
        f"- Título: **{cockpit.get('tituloVisual')}**\n"
        f"- Pendentes: **{cockpit.get('produtosPendentes')}**\n"
        f"- Performance lookup: **{cockpit.get('performanceLookupSec')}s**\n"
        f"- Residual: **{cockpit.get('residualClassificacao')}**\n",
    )
    _w(
        "DW_PRODUCT_OPTIMIZATION_REPORT.md",
        f"# IA-8 — DW Optimization\n\nVer `dw/ddl/dim_product_master_cache_f073.sql`\n",
    )
    _w(
        "PRODUCT_OPTIMIZATION_QA_REPORT.md",
        f"# IA-9 — QA Governance\n\n"
        f"- Residual resolvido/isolado: **{qa.get('residualSkuResolvidoOuIsolado')}**\n"
        f"- Performance: **{qa.get('performanceAprovada')}**\n"
        f"- Cache: **{qa.get('cacheImplementado')}**\n"
        f"- Sem conveniência: **{qa.get('semTermoConveniencia')}**\n",
    )
    ex_lines = "\n".join(f"{k}: {v}" for k, v in sorted(ex.items()))
    _w(
        "F07_3_PRODUCT_MASTER_OPTIMIZATION_REPORT.md",
        f"# F07.3 — Product Master Optimization\n\n"
        f"Fonte: **{w.get('fonte', {}).get('modo')}**\n\n"
        f"## Respostas executivas 1–20\n\n{ex_lines}\n\n{parecer}\n",
    )


if __name__ == "__main__":
    main()
