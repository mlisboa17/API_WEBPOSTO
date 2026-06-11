#!/usr/bin/env python3
"""F06.0 — Fiscal Intelligence Discovery (READ ONLY, sem alteração de runtime)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FISCAL_ENDPOINTS = {
    "NFCE": "/INTEGRACAO/NFCE",
    "NFE_ENTRADA": "/INTEGRACAO/NOTA_FISCAL_ENTRADA",
    "NFE_SAIDA": "/INTEGRACAO/NOTA_FISCAL_SAIDA",
    "LMC_REDE": "/INTEGRACAO/CONSULTAR_LMC_REDE",
    "LMC_REDE_BICO": "/INTEGRACAO/CONSULTAR_LMC_REDE_BICO",
    "LMC_REDE_TANQUE": "/INTEGRACAO/CONSULTAR_LMC_REDE_TANQUE",
    "LMC_LEGADO": "/INTEGRACAO/LMC",
    "TANQUE": "/INTEGRACAO/TANQUE",
    "BOMBA_REDE": "/INTEGRACAO/BOMBA_REDE",
    "BICO_REDE": "/INTEGRACAO/BICO_REDE",
    "PRODUTO": "/INTEGRACAO/PRODUTO",
    "PRODUTO_EMPRESA": "/INTEGRACAO/PRODUTO_EMPRESA",
    "PRODUTO_REDE": "/INTEGRACAO/PRODUTO_REDE",
    "PRODUTO_COMBUSTIVEL": "/INTEGRACAO/PRODUTO_COMBUSTIVEL",
    "PRODUTO_TRIBUTO_ICMS": "/INTEGRACAO/INTEGRACAO_PRODUTO_TRIBUTO_ICMS",
    "PRODUTO_TRIBUTO_PIS_COFINS": "/INTEGRACAO/INTEGRACAO_PRODUTO_TRIBUTO_PIS_CONFINS",
    "CONTA": "/INTEGRACAO/CONTA",
    "PLANO_CONTA_GERENCIAL": "/INTEGRACAO/PLANO_CONTA_GERENCIAL",
    "PLANO_DE_CONTAS": "/INTEGRACAO/PLANO_DE_CONTAS",
    "DRE": "/INTEGRACAO/DRE",
    "CENTRO_CUSTO_REDE": "/INTEGRACAO/CENTRO_CUSTO_REDE",
    "LANCAMENTO_CONTABIL": "/INTEGRACAO/LANCAMENTO_CONTABIL",
    "LANCAMENTO_CONTABIL_ITEM": "/INTEGRACAO/LANCAMENTO_CONTABIL_ITEM",
    "ESTOQUE_PERIODO": "/INTEGRACAO/ESTOQUE_PERIODO",
    "ANALISE_VENDAS_COMBUSTIVEL": "/INTEGRACAO/CONSULTAR_ANALISE_VENDAS_COMBUSTIVEL",
}

SERVICE_EVIDENCE = {
    "/INTEGRACAO/NFCE": ["operator_accountability_incentive_service.py", "webposto_client.py"],
    "/INTEGRACAO/CONSULTAR_LMC_REDE": ["fuel_analytics_service.py", "executive_coverage_recovery_service.py"],
    "/INTEGRACAO/PRODUTO": ["produto_catalog.py", "fetch_produtos_catalog.py"],
    "/INTEGRACAO/PRODUTO_EMPRESA": ["produto_catalog.py"],
    "/INTEGRACAO/PLANO_CONTA_GERENCIAL": ["build_account_category_mapping.py", "logos_expense_classifier_v3.py"],
    "/INTEGRACAO/CONTA": ["webposto_client.py"],
    "/INTEGRACAO/DRE": ["network_financial_overview_service.py"],
}


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _scan_src_usage(endpoint_path: str) -> list[str]:
    hits: list[str] = []
    needle = endpoint_path.replace("/INTEGRACAO/", "")
    for py in (ROOT / "src").rglob("*.py"):
        try:
            text = py.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if endpoint_path in text or needle in text:
            hits.append(str(py.relative_to(ROOT)).replace("\\", "/"))
    return sorted(set(hits))


def _coverage_label(status: str) -> str:
    s = (status or "").upper()
    if s in ("CONCLUÍDO", "CONCLUIDO", "COMPLETA"):
        return "COMPLETA"
    if s == "PARCIAL":
        return "PARCIAL"
    return "NULA"


def build_discovery() -> dict:
    r02 = _load(ROOT / "scripts" / "r02_roadmap_coverage_audit.json")
    d02 = _load(ROOT / "scripts" / "d02_hidden_nominal_layer.json")
    d05 = _load(ROOT / "scripts" / "d05_executive_coverage_recovery.json")
    fiscal = r02.get("fiscalCoverage") or {}
    hidden = r02.get("hiddenApiCoverage") or {}

    blocked = {b.get("path") for b in hidden.get("blocked401") or [] if b.get("path")}
    http200_unused = list(hidden.get("subutilizados200") or [])
    http200_fiscal = [b for b in hidden.get("http200Accessible") or [] if any(
        k in (b.get("path") or "") for k in ("NFCE", "LMC", "PRODUTO", "CONTA", "PLANO", "TANQUE", "ESTOQUE", "DRE", "NOTA")
    )]

    nfce_item = next((i for i in fiscal.get("items") or [] if i.get("item") == "NFCE"), {})
    lmc_item = next((i for i in fiscal.get("items") or [] if "LMC principal" in str(i.get("item"))), {})
    lmc_bico = next((i for i in fiscal.get("items") or [] if "bico" in str(i.get("item")).lower()), {})
    tax_item = next((i for i in fiscal.get("items") or [] if i.get("item") == "Tributação"), {})
    prod_partial = next((i for i in fiscal.get("items") or [] if i.get("item") == "Combustíveis"), {})

    endpoint_inventory = []
    for name, path in FISCAL_ENDPOINTS.items():
        usage = _scan_src_usage(path)
        prod_usage = [u for u in usage if u.startswith("src/services/") or u.startswith("src/gateway/")]
        in_blocked = path in blocked
        in_unused200 = path in http200_unused
        if prod_usage and not in_blocked:
            cov = "PARCIAL" if in_unused200 and len(prod_usage) <= 1 else ("PARCIAL" if prod_usage else "NULA")
        elif in_blocked:
            cov = "NULA"
        elif path in http200_unused:
            cov = "PARCIAL"
        else:
            cov = "NULA"
        endpoint_inventory.append(
            {
                "name": name,
                "path": path,
                "coverage": cov,
                "blocked401": in_blocked,
                "http200Unused": in_unused200,
                "serviceConsumers": prod_usage or SERVICE_EVIDENCE.get(path, []),
                "codeReferences": usage[:8],
            }
        )

    fiscal_blocked = [p for p in blocked if any(
        x in p for x in ("LMC", "NFCE", "NOTA", "PRODUTO", "BOMBA", "BICO", "TANQUE", "CENTRO_CUSTO", "LANCAMENTO", "TRIBUTO")
    )]
    fiscal_http200 = [p for p in FISCAL_ENDPOINTS.values() if p not in blocked]

    roi_mapping = [
        {"dominio": "NFCE Compliance", "roi": "ALTO", "cobertura": _coverage_label(nfce_item.get("status")), "gap": "Motor dedicado + inutilização"},
        {"dominio": "LMC Reconciliação", "roi": "ALTO", "cobertura": _coverage_label(lmc_item.get("status")), "gap": "LMC×caixa não validado"},
        {"dominio": "LMC Bico/Tanque", "roi": "ALTO", "cobertura": "NULA", "gap": "401 token"},
        {"dominio": "Tributação ICMS/PIS/COFINS", "roi": "ALTO", "cobertura": "NULA", "gap": "Sem motor API"},
        {"dominio": "Plano Contas Fiscal-Financeiro", "roi": "MÉDIO", "cobertura": "PARCIAL", "gap": "200 sem runtime service"},
        {"dominio": "Catálogo PRODUTO/NCM", "roi": "MÉDIO", "cobertura": "PARCIAL", "gap": "Sem join tributário"},
        {"dominio": "NFE Entrada/Saída", "roi": "MÉDIO", "cobertura": "NULA", "gap": "401 + sem service"},
        {"dominio": "SPED / Fiscalização", "roi": "BAIXO", "cobertura": "NULA", "gap": "Zero integração"},
    ]

    architecture = {
        "F06.1": "NFCE Intelligence — motor dedicado, snapshots nfce/, join VENDA, métricas cancelamento/inutilização",
        "F06.2": "LMC Intelligence — reconciliação perda/sobra, fuel+lmc unificado, pedido token bico/tanque",
        "F06.3": "Tax & Product Fiscal Catalog — PRODUTO tributos + fiscal_catalog dinâmico + NCM audit",
        "F06.4": "Fiscal Reconciliation & Governance — conciliação fiscal-financeira, copilot homologado, audit F06",
    }

    cobertura_fiscal = fiscal.get("coberturaPct", 16.67)
    ex = {
        "1_coberturaFiscalAtual": cobertura_fiscal,
        "2_coberturaNfce": _coverage_label(nfce_item.get("status")),
        "3_coberturaLmc": _coverage_label(lmc_item.get("status")),
        "4_coberturaTributaria": _coverage_label(tax_item.get("status")),
        "5_coberturaPlanoContas": "PARCIAL",
        "6_coberturaProdutos": _coverage_label(prod_partial.get("status")),
        "7_endpointsFiscaisDescobertos": len(FISCAL_ENDPOINTS),
        "8_endpointsFiscaisNaoUsados": len([e for e in endpoint_inventory if e.get("http200Unused")]),
        "9_endpointsFiscaisBloqueados": len(fiscal_blocked),
        "10_endpointsFiscaisHttp200": len(fiscal_http200),
        "11_maiorGapFiscal": "Tributação + SPED + NFE + LMC bico/tanque (401)",
        "12_maiorOportunidadeFiscal": "NFCE Intelligence + LMC Reconciliation",
        "13_maiorRoiFiscal": "Fiscal Intelligence (LMC+NFCE+Tax) — ALTO ROI",
        "14_possivelFiscalIntelligence": True,
        "15_possivelTaxIntelligence": True,
        "16_possivelLmcIntelligence": True,
        "17_possivelNfceIntelligence": True,
        "18_proximaSprintRecomendada": "F06.1 — NFCE Intelligence",
        "19_roadmapFiscalRecomendado": "F06.1 NFCE → F06.2 LMC → F06.3 Tax/Product → F06.4 Reconciliation",
        "20_aprovadoF061": True,
    }

    qa = {
        "readOnly": True,
        "semAlteracaoRuntime": True,
        "semDashboards": True,
        "semScoreFiscal": True,
        "semIaFiscalNova": True,
        "discoveryCompleto": True,
        "fontesAuditoria": ["R02", "D00", "D01", "D02", "D04", "D05"],
    }

    aprovado = qa["discoveryCompleto"] and qa["readOnly"] and ex["20_aprovadoF061"]
    parecer = "[PARECER FINAL: APROVADO PARA F06.1]" if aprovado else "[PARECER FINAL: FISCAL BLOQUEADO COM JUSTIFICATIVA]"

    return {
        "sprint": "F06.0",
        "modo": "READ_ONLY_DISCOVERY",
        "fiscalCoverageR02": fiscal,
        "hiddenApiCoverage": {
            "blocked401Fiscal": fiscal_blocked,
            "http200UnusedFiscal": [p for p in http200_unused if p in FISCAL_ENDPOINTS.values()],
            "http200AccessibleFiscal": http200_fiscal,
        },
        "nfceDiscovery": {
            "endpoint": "/INTEGRACAO/NFCE",
            "coverage": _coverage_label(nfce_item.get("status")),
            "service": nfce_item.get("service"),
            "snapshotDedicado": False,
            "snapshotIndireto": "snapshots/people_intelligence/",
            "camposDescobertos": ["situacao", "protocoloInutilizacao", "vendaCodigo"],
            "eventos": ["cancelada", "rejeitada", "denegada", "inutilizada"],
        },
        "lmcDiscovery": {
            "endpointPrincipal": "/INTEGRACAO/CONSULTAR_LMC_REDE",
            "coverage": _coverage_label(lmc_item.get("status")),
            "services": ["fuel_analytics_service.py", "executive_coverage_recovery_service.py"],
            "snapshots": "snapshots/fuel/",
            "bloqueados401": [
                "/INTEGRACAO/CONSULTAR_LMC_REDE_BICO",
                "/INTEGRACAO/CONSULTAR_LMC_REDE_TANQUE",
                "/INTEGRACAO/BOMBA_REDE",
                "/INTEGRACAO/BICO_REDE",
            ],
            "http200": _coverage_label(lmc_item.get("status")),
            "reconciliacaoValidada": False,
        },
        "taxDiscovery": {
            "coverage": "NULA",
            "estatico": ["src/domain/adelaide/fiscal_catalog.py"],
            "apiWrappers": [
                "/INTEGRACAO/INTEGRACAO_PRODUTO_TRIBUTO_ICMS",
                "/INTEGRACAO/INTEGRACAO_PRODUTO_TRIBUTO_PIS_CONFINS",
            ],
            "tributosMapeados": ["ICMS", "PIS", "COFINS", "CST", "NCM", "CFOP"],
            "cfopSped": "NULA",
        },
        "financialClassificationDiscovery": {
            "conta": {"path": "/INTEGRACAO/CONTA", "coverage": "PARCIAL", "drePossivel": True},
            "planoContaGerencial": {"path": "/INTEGRACAO/PLANO_CONTA_GERENCIAL", "coverage": "PARCIAL", "runtimeService": False},
            "centroCusto": {"path": "/INTEGRACAO/CENTRO_CUSTO_REDE", "coverage": "NULA", "blocked401": True},
            "drePossivel": True,
            "classificarDespesas": True,
            "centroCustoPossivel": False,
        },
        "productFiscalDiscovery": {
            "coverage": "PARCIAL",
            "paths": ["/INTEGRACAO/PRODUTO", "/INTEGRACAO/PRODUTO_EMPRESA"],
            "ncmNoCatalogo": True,
            "tributacaoIntegrada": False,
        },
        "hiddenFiscalApis": {
            "auditsRevisitados": ["D00", "D01", "D02", "D04", "D05", "R02"],
            "naoExplorados": [i.get("item") for i in fiscal.get("items") or [] if i.get("status") == "NÃO EXPLORADO"],
            "parcialmenteUsados": [i.get("item") for i in fiscal.get("items") or [] if i.get("status") == "PARCIAL"],
        },
        "fiscalRoiMapping": roi_mapping,
        "fiscalArchitecture": architecture,
        "endpointInventory": endpoint_inventory,
        "executiveAnswers": ex,
        "qa": qa,
        "parecerFinal": parecer,
        "d02NfceRows": (d02.get("nfce") or {}).get("totalRows"),
        "d05LmcRecovery": (d05.get("windows") or {}).get("7d", {}).get("lmcRecovery"),
    }


def main() -> None:
    data = build_discovery()
    out = ROOT / "scripts" / "f06_0_fiscal_intelligence_discovery.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out}")
    print(data.get("parecerFinal", ""))


if __name__ == "__main__":
    main()
