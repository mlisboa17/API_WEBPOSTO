#!/usr/bin/env python3
"""Gera relatórios D05 — Executive Coverage Recovery."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "d05_executive_coverage_recovery.json"


def load() -> dict:
    if not AUDIT.exists():
        raise SystemExit("Execute: python scripts/audit_d05_executive_coverage_recovery.py")
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def w(d: dict) -> dict:
    return d.get("windows", {}).get("7d") or next(iter(d.get("windows", {}).values()), {})


def yn(v) -> str:
    if v is True:
        return "**Sim**"
    if v is False:
        return "**Não**"
    return str(v)


def md_table(headers: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def main() -> None:
    data = load()
    ref = w(data)
    ex = ref.get("executiveAnswers") or data.get("executiveAnswers") or {}
    rec = ref.get("executiveCoverageRecalculation") or {}
    antes = rec.get("antes") or {}
    depois = rec.get("depois") or {}
    delta = rec.get("delta") or {}
    gov = ref.get("executiveTrustGovernance") or {}
    qa = ref.get("qaCertification") or {}
    goal = ref.get("officialGoalDiscovery") or {}
    part = ref.get("officialParticipationDiscovery") or {}
    prod = ref.get("officialProductivityDiscovery") or {}
    prest = ref.get("prestacaoRecovery") or {}
    lmc = ref.get("lmcRecovery") or {}
    mov = ref.get("movimentoCaixaRecovery") or {}
    gaps = ref.get("gapsDelta") or {}
    parecer = ref.get("parecerFinal") or data.get("parecerFinal") or ""

    goal_rows = [[k, v.get("classificacao"), v.get("endpoint"), v.get("coberturaPct")] for k, v in (goal.get("entities") or {}).items()]
    prest_rows = [[f.get("campo"), f.get("status"), f.get("fonte"), f.get("coberturaPct")] for f in (prest.get("fields") or [])]
    mov_rows = [[m.get("movimento"), m.get("status"), m.get("endpoint"), m.get("coberturaPct")] for m in (mov.get("movimentos") or [])]
    cert_rows = [[i.get("name"), i.get("cert"), i.get("score")] for i in (gov.get("indicators") or [])]

    reports = {
        "OFFICIAL_GOAL_DISCOVERY_REPORT.md": f"""# OFFICIAL GOAL DISCOVERY — D05 · IA-1

Meta oficial encontrada (filial/produto): {yn(goal.get('metaOficialEncontrada'))}

GRUPO_META: **{goal.get('grupoMetaRegistros', 0)}** registros · PRODUTO_META: **{goal.get('produtoMetaRegistros', 0)}**

{md_table(["Entidade", "Classificação", "Endpoint", "Cobertura %"], goal_rows)}

Cobertura recovery: **{goal.get('coberturaRecoveryPct', '—')}%**
""",
        "OFFICIAL_PARTICIPATION_DISCOVERY_REPORT.md": f"""# OFFICIAL PARTICIPATION DISCOVERY — D05 · IA-2

Classificação: **{part.get('classificacao', '—')}** · Convergência: **{part.get('convergenciaPct', '—')}%** · Diferença: **{part.get('diferencaPct', '—')}%**

Confiabilidade: **{part.get('confiabilidadePct', '—')}%** · Origem: {part.get('origem', '—')}
""",
        "OFFICIAL_PRODUCTIVITY_DISCOVERY_REPORT.md": f"""# OFFICIAL PRODUCTIVITY DISCOVERY — D05 · IA-3

Classificação: **{prod.get('classificacao', '—')}** · Gap proxy: **{prod.get('gapProxyPct', '—')}%**

Confiabilidade: **{prod.get('confiabilidadePct', '—')}%** · Origem: {prod.get('origem', '—')}
""",
        "PRESTACAO_RECOVERY_REPORT.md": f"""# PRESTAÇÃO RECOVERY — D05 · IA-4

Cobertura recovery: **{prest.get('coberturaRecoveryPct', '—')}%** · Totalmente mapeada: {yn(prest.get('prestacaoTotalmenteMapeada'))}

{md_table(["Campo", "Status", "Fonte", "Cobertura %"], prest_rows)}
""",
        "LMC_RECOVERY_REPORT.md": f"""# LMC RECOVERY — D05 · IA-5

Endpoint: `{lmc.get('endpoint', '—')}` · HTTP **{lmc.get('httpStatus', '—')}** · Registros **{lmc.get('registros', 0)}**

Perda física: {yn(lmc.get('perdaFisica'))} · Tanque: {yn(lmc.get('reconciliacaoTanque'))} · Bico: {yn(lmc.get('reconciliacaoBico'))}

Cobertura recovery: **{lmc.get('coberturaRecoveryPct', '—')}%**
""",
        "MOVIMENTO_CAIXA_RECOVERY_REPORT.md": f"""# MOVIMENTO CAIXA RECOVERY — D05 · IA-6

Carta frete mapeada: {yn(mov.get('cartaFreteMapeada'))} · Cobertura: **{mov.get('coberturaRecoveryPct', '—')}%**

{md_table(["Movimento", "Status", "Endpoint", "Cobertura %"], mov_rows)}
""",
        "EXECUTIVE_COVERAGE_RECALCULATION_REPORT.md": f"""# EXECUTIVE COVERAGE RECALCULATION — D05 · IA-7

| Camada | Antes D04.1 | Depois D05 | Δ |
|--------|-------------|------------|---|
| Trust Técnico | {antes.get('trustTecnico', '—')} | {depois.get('trustTecnico', '—')} | — |
| Trust Negócio | **{antes.get('trustNegocio', '—')}** | **{depois.get('trustNegocio', '—')}** | **+{delta.get('trustNegocio', '—')}** |
| Trust Executivo | **{antes.get('trustExecutivo', '—')}** | **{depois.get('trustExecutivo', '—')}** | **+{delta.get('trustExecutivo', '—')}** |
""",
        "EXECUTIVE_TRUST_GOVERNANCE_REPORT.md": f"""# EXECUTIVE TRUST GOVERNANCE — D05 · IA-8

| Trust | Score | Banda |
|-------|-------|-------|
| Técnico | {gov.get('trustTecnico', '—')} | {gov.get('trustTecnicoBand', '—')} |
| Negócio | **{gov.get('trustNegocio', '—')}** | {gov.get('trustNegocioBand', '—')} |
| Executivo | **{gov.get('trustExecutivo', '—')}** | {gov.get('trustExecutivoBand', '—')} |

{md_table(["Indicador", "Certificação", "Score"], cert_rows)}
""",
        "EXECUTIVE_COVERAGE_QA_REPORT.md": f"""# EXECUTIVE COVERAGE QA — D05 · IA-9

Gaps executivos fechados: {yn(qa.get('gapsExecutivosFechados'))}

| Critério | Status |
|----------|--------|
| Trust Negócio > 80 | {yn(qa.get('trustNegocioOk'))} |
| Trust Executivo > 70 | {yn(qa.get('trustExecutivoOk'))} |
| Sem score sem origem | {yn(qa.get('semScoreSemOrigem'))} |
| Lineage validado | {yn(qa.get('lineageValidado'))} |
| QA aprovado | **{yn(qa.get('aprovado'))}** |
""",
    }

    for name, content in reports.items():
        (ROOT / name).write_text(content, encoding="utf-8")

    (ROOT / "D05_EXECUTIVE_COVERAGE_RECOVERY_REPORT.md").write_text(
        f"""# D05 — EXECUTIVE COVERAGE RECOVERY REPORT

Baseline **2026-06-01 → 2026-06-07** · Filiais **11495, 5555**

## Respostas executivas (20)

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Meta oficial encontrada? | {yn(ex.get('1_metaOficialEncontrada'))} (filial/produto) |
| 2 | Participação oficial encontrada? | {yn(ex.get('2_participacaoOficialEncontrada'))} (proxy convergente) |
| 3 | Produtividade oficial encontrada? | {yn(ex.get('3_produtividadeOficialEncontrada'))} (PRÓXIMA) |
| 4 | Fundo de caixa encontrado? | {yn(ex.get('4_fundoCaixaEncontrado'))} (CAIXA.abertura) |
| 5 | Prestação totalmente mapeada? | {yn(ex.get('5_prestacaoTotalmenteMapeada'))} |
| 6 | LMC totalmente mapeado? | {yn(ex.get('6_lmcTotalmenteMapeado'))} |
| 7 | Carta frete mapeada? | {yn(ex.get('7_cartaFreteMapeada'))} |
| 8 | Serviços mapeados? | {yn(ex.get('8_servicosMapeados'))} |
| 9 | Trocas mapeadas? | {yn(ex.get('9_trocasMapeadas'))} |
| 10 | Suprimentos mapeados? | {yn(ex.get('10_suprimentosMapeados'))} |
| 11 | Trust Técnico mudou? | {yn(ex.get('11_trustTecnicoMudou'))} |
| 12 | Trust Negócio mudou? | {yn(ex.get('12_trustNegocioMudou'))} (+{delta.get('trustNegocio', '—')}) |
| 13 | Trust Executivo mudou? | {yn(ex.get('13_trustExecutivoMudou'))} (+{delta.get('trustExecutivo', '—')}) |
| 14 | Gaps permanecem | {', '.join(ex.get('14_gapsPermanecem') or []) or '—'} |
| 15 | Gaps eliminados | {', '.join(ex.get('15_gapsEliminados') or []) or '—'} |
| 16 | People Score confiável | {yn(ex.get('16_peopleScoreConfiavel'))} |
| 17 | Executive Score confiável | {yn(ex.get('17_executiveScoreConfiavel'))} |
| 18 | Corporate Score confiável | {yn(ex.get('18_corporateScoreConfiavel'))} |
| 19 | Pronto decisões automatizadas | {yn(ex.get('19_prontoDecisoesAutomatizadas'))} |
| 20 | F05.1 pode ser liberado? | {yn(ex.get('20_f051Liberado'))} |

## Trust — Antes vs Depois

| | D04.1 | D05 |
|---|-------|-----|
| Trust Negócio | {antes.get('trustNegocio', '—')} | **{depois.get('trustNegocio', '—')}** |
| Trust Executivo | {antes.get('trustExecutivo', '—')} | **{depois.get('trustExecutivo', '—')}** |

## Relatórios IA

- OFFICIAL_GOAL_DISCOVERY_REPORT.md (IA-1)
- OFFICIAL_PARTICIPATION_DISCOVERY_REPORT.md (IA-2)
- OFFICIAL_PRODUCTIVITY_DISCOVERY_REPORT.md (IA-3)
- PRESTACAO_RECOVERY_REPORT.md (IA-4)
- LMC_RECOVERY_REPORT.md (IA-5)
- MOVIMENTO_CAIXA_RECOVERY_REPORT.md (IA-6)
- EXECUTIVE_COVERAGE_RECALCULATION_REPORT.md (IA-7)
- EXECUTIVE_TRUST_GOVERNANCE_REPORT.md (IA-8)
- EXECUTIVE_COVERAGE_QA_REPORT.md (IA-9)

---

{parecer}
""",
        encoding="utf-8",
    )

    print("Relatórios D05 gerados.")
    print(parecer)


if __name__ == "__main__":
    main()
