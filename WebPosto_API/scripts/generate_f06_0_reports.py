#!/usr/bin/env python3
"""Gera relatórios F06.0 Fiscal Intelligence Discovery (READ ONLY)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f06_0_fiscal_intelligence_discovery.json"


def _load() -> dict:
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def _w(name: str, body: str) -> None:
    p = ROOT / name
    p.write_text(body, encoding="utf-8")
    print(f"Wrote {p}")


def main() -> None:
    data = _load()
    ex = data.get("executiveAnswers") or {}
    qa = data.get("qa") or {}
    nfce = data.get("nfceDiscovery") or {}
    lmc = data.get("lmcDiscovery") or {}
    tax = data.get("taxDiscovery") or {}
    fin = data.get("financialClassificationDiscovery") or {}
    prod = data.get("productFiscalDiscovery") or {}
    hidden = data.get("hiddenFiscalApis") or {}
    roi = data.get("fiscalRoiMapping") or []
    arch = data.get("fiscalArchitecture") or {}
    parecer = data.get("parecerFinal") or ""

    _w(
        "NFCE_DISCOVERY_REPORT.md",
        f"# NFCE Discovery (F06.0)\n\n"
        f"- Endpoint: **{nfce.get('endpoint')}**\n"
        f"- Cobertura: **{nfce.get('coverage')}**\n"
        f"- Service: **{nfce.get('service')}**\n"
        f"- Snapshot dedicado: **{nfce.get('snapshotDedicado')}**\n"
        f"- Snapshot indireto: **{nfce.get('snapshotIndireto')}**\n"
        f"- Eventos: {', '.join(nfce.get('eventos') or [])}\n"
        f"- Campos descobertos: {', '.join(nfce.get('camposDescobertos') or [])}\n",
    )
    _w(
        "LMC_DISCOVERY_REPORT.md",
        f"# LMC Discovery\n\n"
        f"- Endpoint principal: **{lmc.get('endpointPrincipal')}** — HTTP 200\n"
        f"- Cobertura: **{lmc.get('coverage')}**\n"
        f"- Services: {', '.join(lmc.get('services') or [])}\n"
        f"- Snapshots: **{lmc.get('snapshots')}**\n"
        f"- Bloqueados 401: {len(lmc.get('bloqueados401') or [])} endpoints\n"
        f"- Reconciliação LMC×caixa validada: **{lmc.get('reconciliacaoValidada')}**\n",
    )
    _w(
        "TAX_DISCOVERY_REPORT.md",
        f"# Tax Discovery\n\n"
        f"- Cobertura motor tributário: **{tax.get('coverage')}**\n"
        f"- Tributos mapeados: {', '.join(tax.get('tributosMapeados') or [])}\n"
        f"- CFOP/SPED: **{tax.get('cfopSped')}**\n"
        f"- Estático: {', '.join(tax.get('estatico') or [])}\n",
    )
    _w(
        "FINANCIAL_CLASSIFICATION_DISCOVERY_REPORT.md",
        f"# Financial Classification Discovery\n\n"
        f"- CONTA: **{fin.get('conta', {}).get('coverage')}** — DRE possível: **{fin.get('drePossivel')}**\n"
        f"- PLANO_CONTA_GERENCIAL: **{fin.get('planoContaGerencial', {}).get('coverage')}** — runtime service: **{fin.get('planoContaGerencial', {}).get('runtimeService')}**\n"
        f"- Centro de custo: **{fin.get('centroCusto', {}).get('coverage')}** (401)\n"
        f"- Classificar despesas: **{fin.get('classificarDespesas')}**\n",
    )
    _w(
        "PRODUCT_FISCAL_DISCOVERY_REPORT.md",
        f"# Product Fiscal Discovery\n\n"
        f"- Cobertura: **{prod.get('coverage')}**\n"
        f"- NCM no catálogo: **{prod.get('ncmNoCatalogo')}**\n"
        f"- Tributação integrada: **{prod.get('tributacaoIntegrada')}**\n"
        f"- Endpoints: {', '.join(prod.get('paths') or [])}\n",
    )
    _w(
        "HIDDEN_FISCAL_APIS_REPORT.md",
        f"# Hidden Fiscal APIs\n\n"
        f"- Audits revisitados: {', '.join(hidden.get('auditsRevisitados') or [])}\n"
        f"- Não explorados ({len(hidden.get('naoExplorados') or [])}): {', '.join(hidden.get('naoExplorados') or [])}\n"
        f"- Parcialmente usados: {', '.join(hidden.get('parcialmenteUsados') or [])}\n"
        f"- Endpoints 200 subutilizados: **{ex.get('8_endpointsFiscaisNaoUsados')}**\n"
        f"- Endpoints 401 bloqueados: **{ex.get('9_endpointsFiscaisBloqueados')}**\n",
    )
    _w(
        "FISCAL_ROI_MAPPING_REPORT.md",
        f"# Fiscal ROI Mapping\n\n"
        + "\n".join(f"- **{r['dominio']}** — ROI {r['roi']} — cobertura {r['cobertura']} — gap: {r['gap']}" for r in roi)
        + "\n",
    )
    _w(
        "FISCAL_ARCHITECTURE_REPORT.md",
        f"# Fiscal Architecture (proposta, sem implementação)\n\n"
        + "\n".join(f"## {k}\n\n{v}\n" for k, v in arch.items())
        + "\n",
    )
    _w(
        "F06_DISCOVERY_QA_REPORT.md",
        f"# F06 Discovery QA Gate\n\n"
        f"| Critério | OK |\n|---|---|\n"
        f"| READ ONLY | {qa.get('readOnly')} |\n"
        f"| Sem alteração runtime | {qa.get('semAlteracaoRuntime')} |\n"
        f"| Sem dashboards | {qa.get('semDashboards')} |\n"
        f"| Sem score fiscal | {qa.get('semScoreFiscal')} |\n"
        f"| Sem IA fiscal nova | {qa.get('semIaFiscalNova')} |\n"
        f"| Discovery completo | {qa.get('discoveryCompleto')} |\n\n"
        f"{parecer}\n",
    )
    _w(
        "F06_0_FISCAL_INTELLIGENCE_DISCOVERY_REPORT.md",
        f"# F06.0 — Fiscal Intelligence Discovery\n\n"
        f"**Modo:** READ ONLY · sem dashboards · sem score · sem IA nova\n\n"
        f"## Respostas executivas 1–20\n\n"
        + "\n".join(f"{k}: {v}" for k, v in sorted(ex.items()))
        + f"\n\n## Cobertura R02\n\n"
        f"- Fiscal: **{ex.get('1_coberturaFiscalAtual')}%** (3 PARCIAL / 6 NÃO EXPLORADO / 9 itens)\n"
        f"- Maior gap: **{ex.get('11_maiorGapFiscal')}**\n"
        f"- Maior ROI: **{ex.get('13_maiorRoiFiscal')}**\n\n"
        f"{parecer}\n",
    )


if __name__ == "__main__":
    main()
