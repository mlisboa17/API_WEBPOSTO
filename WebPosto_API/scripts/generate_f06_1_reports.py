#!/usr/bin/env python3
"""Gera relatórios F06.1 NFCE Intelligence."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f06_1_nfce_intelligence.json"


def _load() -> dict:
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def _w(name: str, body: str) -> None:
    p = ROOT / name
    p.write_text(body, encoding="utf-8")
    print(f"Wrote {p}")


def main() -> None:
    data = _load()
    w = data.get("windows", {}).get("7d") or {}
    ex = w.get("executiveAnswers") or data.get("executiveAnswers") or {}
    qa = w.get("qa") or {}
    catalog = w.get("nfceCatalogEngine") or {}
    lineage = w.get("nfceLineageEngine") or {}
    recon = w.get("nfceReconciliationEngine") or {}
    risks = w.get("nfceRiskEngine") or {}
    anomalies = w.get("nfceAnomalyEngine") or {}
    exec_intel = w.get("nfceExecutiveIntelligence") or {}
    cockpit = w.get("cockpit") or {}
    parecer = w.get("parecerFinal") or data.get("parecerFinal") or ""

    _w(
        "NFCE_CATALOG_REPORT.md",
        f"# NFCE Catalog (F06.1)\n\n"
        f"- Emitidas: **{catalog.get('emitidas')}**\n"
        f"- Canceladas: **{catalog.get('canceladas')}**\n"
        f"- Inutilizadas: **{catalog.get('inutilizadas')}**\n"
        f"- Pendentes: **{catalog.get('pendentes')}**\n"
        f"- Total homologado: **{catalog.get('total')}**\n"
        f"- Cobertura: **{catalog.get('coverage')}**\n"
        f"- Endpoint: `/INTEGRACAO/NFCE` (D01, sem live)\n",
    )
    _w(
        "NFCE_LINEAGE_REPORT.md",
        f"# NFCE Lineage\n\n"
        f"- Itens rastreados: **{lineage.get('total')}**\n"
        f"- Join NFCE↔VENDA: **{ex.get('13_joinNfceVendaPct')}%**\n"
        f"- Chaves: `empresaCodigo`, `vendaCodigo`\n"
        f"- Lineage completo: **{qa.get('lineageCompleto')}**\n"
        f"- WebPosto live: **{not qa.get('fonteWebPostoLive', True)}**\n",
    )
    _w(
        "NFCE_RECONCILIATION_REPORT.md",
        f"# NFCE Reconciliation\n\n"
        f"- Vendas total: **{recon.get('vendasTotal')}**\n"
        f"- NFCE emitidas: **{recon.get('nfceEmitidasTotal')}**\n"
        f"- Matched: **{recon.get('matched')}**\n"
        f"- Cobertura: **{recon.get('coveragePct')}%**\n"
        f"- Sem nota: **{recon.get('semNota')}**\n"
        f"- Duplicadas: **{recon.get('duplicadas')}**\n"
        f"- Canceladas: **{recon.get('canceladas')}**\n"
        f"- Divergentes: **{recon.get('divergentes')}**\n",
    )
    _w(
        "NFCE_RISK_ENGINE_REPORT.md",
        f"# NFCE Risk Engine\n\n"
        f"- Filiais classificadas: **{risks.get('total')}**\n"
        f"- Risco máximo: **{ex.get('9_riscoMaximo')}**\n"
        f"- Filial maior risco: **{ex.get('10_filialMaiorRisco')}**\n\n"
        + "\n".join(
            f"- Filial {r.get('empresaCodigo')}: **{r.get('risco')}** "
            f"(cancel={r.get('cancelamentos')}, aus={r.get('ausencias')}, div={r.get('divergencias')})"
            for r in (risks.get("risks") or [])[:5]
        )
        + "\n",
    )
    _w(
        "NFCE_ANOMALY_ENGINE_REPORT.md",
        f"# NFCE Anomaly Engine\n\n"
        f"- Padrões detectados: **{anomalies.get('total')}**\n\n"
        + "\n".join(
            f"- **{p.get('tipo')}**: valor={p.get('valor')} severidade={p.get('severidade')}"
            for p in (anomalies.get("patterns") or [])
        )
        + "\n",
    )
    _w(
        "NFCE_EXECUTIVE_INTELLIGENCE_REPORT.md",
        f"# NFCE Executive Intelligence\n\n"
        f"- Filial maior risco: **{exec_intel.get('filialMaiorRisco', {}).get('empresaCodigo')}** "
        f"({exec_intel.get('filialMaiorRisco', {}).get('risco')})\n"
        f"- PDV maior divergência: **{exec_intel.get('pdvMaiorDivergencia', {}).get('pdvCodigo')}** "
        f"({exec_intel.get('pdvMaiorDivergencia', {}).get('ocorrencias')} ocorrências)\n"
        f"- Operador mais ocorrências: **{exec_intel.get('operadorMaisOcorrencias', {}).get('nome') or '—'}**\n"
        f"- Cobertura reconciliação: **{exec_intel.get('reconciliacaoCoveragePct')}%**\n",
    )
    _w(
        "NFCE_COCKPIT_REPORT.md",
        f"# NFCE Cockpit\n\n"
        f"- View: **`nfce-intelligence`**\n"
        f"- API: `/api/v1/nfce-intelligence/cockpit`\n"
        f"- Widgets: NFCE emitidas, canceladas, risco fiscal, divergências, top ocorrências\n"
        f"- Emitidas cockpit: **{cockpit.get('nfceEmitidas')}**\n"
        f"- Canceladas cockpit: **{cockpit.get('nfceCanceladas')}**\n"
        f"- Divergências: **{cockpit.get('divergencias')}**\n"
        f"- Cockpit aprovado: **{ex.get('18_cockpitAprovado')}**\n",
    )
    _w(
        "NFCE_DW_REPORT.md",
        f"# NFCE DW Layer\n\n"
        f"- `fact_nfce_catalog`\n"
        f"- `fact_nfce_lineage`\n"
        f"- `fact_nfce_risk`\n"
        f"- `fact_nfce_reconciliation`\n"
        f"- DDL: `dw/ddl/fact_nfce_intelligence.sql`\n"
        f"- Amostras exportadas: catalog={len((w.get('dwLayer') or {}).get('factNfceCatalog') or [])}, "
        f"lineage={len((w.get('dwLayer') or {}).get('factNfceLineage') or [])}, "
        f"risk={len((w.get('dwLayer') or {}).get('factNfceRisk') or [])}\n",
    )
    _w(
        "NFCE_QA_REPORT.md",
        f"# NFCE QA Gate\n\n"
        f"| Critério | OK |\n|---|---|\n"
        f"| Snapshots homologados | {qa.get('snapshotsHomologados')} |\n"
        f"| Sem WebPosto live | {not qa.get('fonteWebPostoLive', True)} |\n"
        f"| Motor auditável | {qa.get('motorAuditavel')} |\n"
        f"| Lineage completo | {qa.get('lineageCompleto')} |\n"
        f"| Sem cross-tenant | {qa.get('semCrossTenant')} |\n"
        f"| Ausência NFCE detectável | {ex.get('14_ausenciaNfce')} |\n"
        f"| Cockpit aprovado | {ex.get('18_cockpitAprovado')} |\n"
        f"| Fiscal Intelligence viável | {ex.get('19_fiscalIntelligenceViavel')} |\n\n"
        f"{parecer}\n",
    )
    _w(
        "F06_1_NFCE_INTELLIGENCE_REPORT.md",
        f"# F06.1 — NFCE Intelligence\n\n"
        f"## Respostas executivas 1–20\n\n"
        + "\n".join(f"{k}: {v}" for k, v in sorted(ex.items()))
        + f"\n\n## Critérios de aceite\n\n"
        f"- Fonte: snapshots homologados D01 + people + operator + cash + F06.0\n"
        f"- WebPosto live: **False**\n"
        f"- Join NFCE↔VENDA: **{ex.get('13_joinNfceVendaPct')}%**\n"
        f"- Trust executivo: **{ex.get('trustExecutivo')}**\n"
        f"- QA motor auditável: **{qa.get('motorAuditavel')}**\n\n"
        f"{parecer}\n",
    )


if __name__ == "__main__":
    main()
