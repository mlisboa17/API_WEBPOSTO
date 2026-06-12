#!/usr/bin/env python3
"""Gera relatórios F06.2 LMC Intelligence."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f06_2_lmc_intelligence.json"


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
    catalog = w.get("lmcCatalogEngine") or {}
    recon = w.get("fuelReconciliationEngine") or {}
    loss = w.get("lossSurplusEngine") or {}
    tanks = w.get("tankIntelligence") or {}
    pumps = w.get("pumpIntelligence") or {}
    exec_intel = w.get("lmcExecutiveIntelligence") or {}
    cockpit = w.get("cockpit") or {}
    parecer = w.get("parecerFinal") or data.get("parecerFinal") or ""

    _w(
        "LMC_CATALOG_REPORT.md",
        f"# LMC Catalog (F06.2)\n\n"
        f"- Entradas: **{catalog.get('entradas')} L**\n"
        f"- Saídas: **{catalog.get('saidas')} L**\n"
        f"- Perdas: **{catalog.get('perdas')} L**\n"
        f"- Sobras: **{catalog.get('sobras')} L**\n"
        f"- Movimentações: **{catalog.get('movimentacoes')}**\n"
        f"- Registros evidenciados: **{catalog.get('registrosLmcEvidenciados')}**\n"
        f"- Registros homologados: **{catalog.get('registrosLmcHomologados')}**\n"
        f"- Cobertura: **{catalog.get('coverage')}**\n",
    )
    _w(
        "FUEL_RECONCILIATION_REPORT.md",
        f"# Fuel Reconciliation\n\n"
        f"- ABASTECIMENTO total: **{recon.get('abastecimentoTotal')}**\n"
        f"- ABASTECIMENTO matched: **{recon.get('abastecimentoMatched')}**\n"
        f"- Cobertura ABAST↔VENDA_ITEM: **{recon.get('coverageAbastVendaItemPct')}%**\n"
        f"- LMC registros: **{recon.get('lmcRegistros')}**\n"
        f"- Venda litros: **{recon.get('vendaLitros')} L**\n"
        f"- LMC saída litros: **{recon.get('lmcSaidaLitros')} L**\n"
        f"- Divergentes: **{recon.get('divergentes')}**\n"
        f"- Confiável: **{recon.get('confiavel')}**\n",
    )
    _w(
        "LOSS_SURPLUS_ENGINE_REPORT.md",
        f"# Loss & Surplus Engine\n\n"
        f"- Perda operacional: **{loss.get('perdaOperacional')} L**\n"
        f"- Sobra operacional: **{loss.get('sobraOperacional')} L**\n"
        f"- Índice de perda: **{loss.get('indicePerda')}%**\n"
        f"- Banda: **{loss.get('banda')}**\n\n"
        + "\n".join(
            f"- Filial {f.get('empresaCodigo')}: perda={f.get('perdaOperacional')} "
            f"sobra={f.get('sobraOperacional')} índice={f.get('indicePerda')}% banda={f.get('banda')}"
            for f in (loss.get("filiais") or [])[:5]
        )
        + "\n",
    )
    _w(
        "TANK_INTELLIGENCE_REPORT.md",
        f"# Tank Intelligence\n\n"
        f"- Tanques mapeados: **{tanks.get('totalTanques')}**\n"
        f"- Endpoint tanque 401: **{tanks.get('endpointTanque401')}**\n"
        f"- Maior perda: tanque **{(tanks.get('maiorPerda') or {}).get('tanqueCodigo')}**\n"
        f"- Maior sobra: tanque **{(tanks.get('maiorSobra') or {}).get('tanqueCodigo')}**\n\n"
        + "\n".join(
            f"- Tanque {t.get('tanqueCodigo')} filial {t.get('empresaCodigo')}: "
            f"perda={t.get('perda')} sobra={t.get('sobra')}"
            for t in (tanks.get("tanquesCriticos") or [])[:5]
        )
        + "\n",
    )
    _w(
        "PUMP_INTELLIGENCE_REPORT.md",
        f"# Pump Intelligence\n\n"
        f"- Endpoint dedicado bico: **{pumps.get('classificacaoEndpointDedicado')}** (401)\n"
        f"- Fonte nested LMC_REDE: **{pumps.get('fonteNestedLmcRede')}**\n"
        f"- Total bicos nested: **{pumps.get('totalBicos')}**\n\n"
        f"## Bicos críticos\n\n"
        + "\n".join(
            f"- Bico {b.get('bicoCodigo')}: {b.get('status')} venda={b.get('vendaLitros')} L"
            for b in (pumps.get("bicosCriticos") or [])[:5]
        )
        + "\n",
    )
    _w(
        "LMC_EXECUTIVE_INTELLIGENCE_REPORT.md",
        f"# LMC Executive Intelligence\n\n"
        f"- Filial mais perda: **{exec_intel.get('filialMaisPerda', {}).get('empresaCodigo')}**\n"
        f"- Filial mais eficiente: **{exec_intel.get('filialMaisEficiente', {}).get('empresaCodigo')}**\n"
        f"- PDV maior risco: **{exec_intel.get('pdvMaiorRisco', {}).get('pdvCodigo')}**\n"
        f"- Tanque mais perdas: **{(exec_intel.get('tanqueMaisPerdas') or {}).get('tanqueCodigo')}**\n"
        f"- Bico mais crítico: **{(exec_intel.get('bicoMaisCritico') or {}).get('bicoCodigo')}**\n"
        f"- Oportunidade recuperação: **R$ {exec_intel.get('maiorOportunidadeRecuperacao')}**\n",
    )
    _w(
        "LMC_COCKPIT_REPORT.md",
        f"# LMC Cockpit\n\n"
        f"- View: **`lmc-intelligence`**\n"
        f"- API: `/api/v1/lmc-intelligence/cockpit`\n"
        f"- Widgets: Perdas, Sobras, Risco combustível, Top tanques, Top divergências\n"
        f"- Perdas: **{cockpit.get('perdas')} L**\n"
        f"- Sobras: **{cockpit.get('sobras')} L**\n"
        f"- Risco: **{cockpit.get('riscoCombustivel')}**\n",
    )
    _w(
        "DW_LMC_MODEL.md",
        f"# DW LMC Model\n\n"
        f"- `fact_lmc`\n"
        f"- `fact_lmc_loss`\n"
        f"- `fact_lmc_surplus`\n"
        f"- `fact_lmc_reconciliation`\n"
        f"- DDL: `dw/ddl/fact_lmc_intelligence.sql`\n",
    )
    _w(
        "LMC_QA_REPORT.md",
        f"# LMC QA Gate\n\n"
        f"| Critério | OK |\n|---|---|\n"
        f"| Sem cálculo sem origem | {qa.get('semCalculoSemOrigem')} |\n"
        f"| Sem perda sem evidência | {qa.get('semPerdaSemEvidencia')} |\n"
        f"| Sem cross-tenant | {qa.get('semCrossTenant')} |\n"
        f"| Sem reconciliação sem lineage | {qa.get('semReconciliacaoSemLineage')} |\n"
        f"| Motor auditável | {qa.get('motorAuditavel')} |\n"
        f"| Lineage completo | {qa.get('lineageCompleto')} |\n"
        f"| Reconciliação confiável | {ex.get('15_reconciliacaoConfiavel')} |\n"
        f"| LMC Intelligence viável | {ex.get('19_lmcIntelligenceViavel')} |\n\n"
        f"{parecer}\n",
    )
    _w(
        "F06_2_LMC_INTELLIGENCE_REPORT.md",
        f"# F06.2 — LMC Intelligence\n\n"
        f"## Respostas executivas 1–20\n\n"
        + "\n".join(f"{k}: {v}" for k, v in sorted(ex.items()))
        + f"\n\n## Critérios de aceite\n\n"
        f"- Fonte: snapshots fuel + fuel_network_audit + D01/D05/F06.0\n"
        f"- WebPosto live: **False**\n"
        f"- Endpoint bico dedicado: **{ex.get('endpointBicoDedicado')}**\n"
        f"- Trust executivo: **{ex.get('trustExecutivo')}**\n\n"
        f"{parecer}\n",
    )


if __name__ == "__main__":
    main()
