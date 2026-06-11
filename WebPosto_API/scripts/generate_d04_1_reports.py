#!/usr/bin/env python3
"""Gera relatórios D04.1 — Coverage Truth Audit."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "d04_1_coverage_truth_audit.json"


def load() -> dict:
    if not AUDIT.exists():
        raise SystemExit("Execute: python scripts/audit_d04_1_coverage_truth_audit.py")
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
    tech = ref.get("technicalCoverageAudit") or {}
    biz = ref.get("businessCoverageAudit") or {}
    prest = ref.get("prestacaoGapAudit") or {}
    people = ref.get("peopleCoverageChallenge") or {}
    fin = ref.get("financialGapAudit") or {}
    ops = ref.get("operationalGapAudit") or {}
    hidden = ref.get("hiddenEndpointDiscovery") or {}
    trust = ref.get("trustScoreChallenge") or {}
    qa = ref.get("qaCertification") or {}
    sabemos = ref.get("oQueSabemos") or {}
    achamos = ref.get("oQueAchamosQueSabemos") or {}
    nao = ref.get("oQueNaoSabemos") or {}
    parecer = ref.get("parecerFinal") or data.get("parecerFinal") or ""

    biz_rows = [[m.get("dominio"), m.get("negocio"), m.get("api"), m.get("coberturaPct")] for m in (biz.get("matrix") or [])]
    prest_rows = [
        [
            f.get("campo"),
            yn(f.get("equivalenteApi")),
            yn(f.get("proxy")),
            yn(f.get("inferencia")),
            yn(f.get("naoExiste")),
        ]
        for f in (prest.get("fields") or [])
    ]
    fin_rows = [[g.get("item"), g.get("endpoint"), g.get("coberturaPct")] for g in (fin.get("gaps") or [])]
    ops_rows = [[g.get("item"), g.get("fonte"), g.get("coberturaPct")] for g in (ops.get("gaps") or [])]
    hidden_rows = [
        [e.get("endpoint"), e.get("path"), e.get("httpStatus"), e.get("registros", 0)]
        for e in (hidden.get("neverConsumed") or [])[:12]
    ]

    reports = {
        "TECHNICAL_COVERAGE_AUDIT.md": f"""# TECHNICAL COVERAGE AUDIT — D04.1 · IA-1

| Métrica | Valor |
|---------|-------|
| Endpoints no catálogo (D00 probe) | **{tech.get('totalEndpoints', '—')}** |
| Endpoints no client Logos | {tech.get('endpointsCatalogClient', '—')} |
| Endpoints consumidos | **{tech.get('endpointsConsumidos', '—')}** |
| Endpoints ignorados | **{tech.get('endpointsIgnorados', '—')}** |
| HTTP 200 | **{tech.get('http200', '—')}** |
| HTTP 401 | **{tech.get('http401', '—')}** |
| Consumo pipeline % | {tech.get('consumptionPct', '—')} |
| Alcance técnico token % | {tech.get('technicalReachPct', '—')} |

**Conclusão:** D04 mede completude do pipeline capturado ({tech.get('endpointsConsumidos')} endpoints), não o universo de {tech.get('totalEndpoints')} endpoints descobertos.
""",
        "BUSINESS_COVERAGE_AUDIT.md": f"""# BUSINESS COVERAGE AUDIT — D04.1 · IA-2

Cobertura real de negócio: **{biz.get('businessCoveragePct', '—')}%**

F03.4-B API média: {biz.get('f034bApiCoveragePct', '—')}% · D01 reconstrução: {biz.get('d01ReconstructionPct', '—')}% · D02 prestação: {biz.get('d02PrestacaoPct', '—')}%

{md_table(["Domínio", "Negócio", "API", "Cobertura %"], biz_rows)}
""",
        "PRESTACAO_GAP_AUDIT.md": f"""# PRESTAÇÃO DE CONTAS GAP — D04.1 · IA-3

Cobertura D02: **{prest.get('coberturaD02Pct', '—')}%** · Atinge 100%: {yn(prest.get('atinge100'))}

{md_table(["Campo", "Equivalente API", "Proxy", "Inferência", "Não existe"], prest_rows)}

**Exclusivos UI:** {', '.join(prest.get('exclusivoPrestacao') or []) or '—'}
""",
        "PEOPLE_COVERAGE_CHALLENGE_REPORT.md": f"""# PEOPLE COVERAGE CHALLENGE — D04.1 · IA-4

D04 alegou: **{people.get('d04ClaimPct', '—')}%** — {people.get('d04ClaimMeaning', '')}

| Camada | Cobertura |
|--------|-----------|
| Técnica (join/nome) | **{people.get('coberturaTecnicaPct', '—')}%** |
| Operacional (prod/participação oficial) | **{people.get('coberturaOperacionalPct', '—')}%** |
| Gerencial (meta/ranking) | **{people.get('coberturaGerencialPct', '—')}%** |
| **Real consolidada** | **{people.get('coberturaRealPct', '—')}%** |
| Δ vs D04 | **{people.get('deltaVsD04', '—')}** |

Catálogo FUNCIONARIO: {people.get('funcionariosCatalogo', '—')} registros
""",
        "FINANCIAL_GAP_REPORT.md": f"""# FINANCIAL GAP — D04.1 · IA-5

D04 alegou: **{fin.get('d04ClaimPct', '—')}%** · Real: **{fin.get('coberturaRealPct', '—')}%** · Δ: **{fin.get('deltaVsD04', '—')}**

{md_table(["Item", "Endpoint", "Cobertura %"], fin_rows)}
""",
        "OPERATIONAL_GAP_REPORT.md": f"""# OPERATIONAL GAP — D04.1 · IA-6

D04 alegou vendas: **{ops.get('d04ClaimPct', '—')}%** · Real operacional: **{ops.get('coberturaRealPct', '—')}%** · Δ: **{ops.get('deltaVsD04', '—')}**

{md_table(["Item", "Fonte", "Cobertura %"], ops_rows)}
""",
        "HIDDEN_ENDPOINT_DISCOVERY_REPORT.md": f"""# HIDDEN ENDPOINT DISCOVERY — D04.1 · IA-7

| Categoria | Total |
|-----------|-------|
| Nunca consumidos | **{(hidden.get('totals') or {}).get('neverConsumed', '—')}** |
| Parcialmente consumidos | **{(hidden.get('totals') or {}).get('partiallyConsumed', '—')}** |
| Bloqueados 401 | **{(hidden.get('totals') or {}).get('blocked401', '—')}** |
| Potencial estratégico | **{(hidden.get('totals') or {}).get('strategicPotential', '—')}** |

## Amostra nunca consumidos

{md_table(["Endpoint", "Path", "HTTP", "Registros"], hidden_rows)}
""",
        "TRUST_SCORE_CHALLENGE_REPORT.md": f"""# TRUST SCORE CHALLENGE — D04.1 · IA-8

| Camada | Score | Banda |
|--------|-------|-------|
| Trust Técnico (D04) | **{trust.get('trustTecnico', '—')}** | {trust.get('trustTecnicoBand', '—')} |
| Trust Negócio | **{trust.get('trustNegocio', '—')}** | {trust.get('trustNegocioBand', '—')} |
| Trust Executivo | **{trust.get('trustExecutivo', '—')}** | {trust.get('trustExecutivoBand', '—')} |

Gap técnico vs negócio: **{trust.get('gapTecnicoVsNegocio', '—')}** pontos

Trust 100 é apenas técnico: {yn(trust.get('d04Trust100IsTechnicalOnly'))}

{trust.get('formula', '')}
""",
        "D04_CERTIFICATION_REPORT.md": f"""# D04 CERTIFICATION — D04.1 · IA-9

**O D04 superestimou a cobertura?** {yn(qa.get('d04SuperestimouCobertura'))}

| Classificação | Valor |
|---------------|-------|
| Certificação D04 | **{qa.get('certificacao', '—')}** |
| Classificação adversarial | **{qa.get('classificacaoD04', '—')}** |
| Válido camada técnica | {yn(qa.get('d04ValidoCamadaTecnica'))} |
| Válido camada negócio | {yn(qa.get('d04ValidoCamadaNegocio'))} |

Evidências: gap={((qa.get('evidenciasRefutacao') or {}).get('gapTrustTecnicoNegocio'))} · campos sem origem={(qa.get('evidenciasRefutacao') or {}).get('camposSemOrigemApi')}
""",
    }

    for name, content in reports.items():
        (ROOT / name).write_text(content, encoding="utf-8")

    (ROOT / "D04_1_COVERAGE_TRUTH_AUDIT_REPORT.md").write_text(
        f"""# D04.1 — COVERAGE TRUTH AUDIT REPORT

Missão adversarial: **tentar derrubar o D04** · Baseline **2026-06-01 → 2026-06-07** · Filiais **11495, 5555**

## Respostas executivas (20)

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | D04 continua válido? | {yn(ex.get('1_d04ContinuaValido'))} ({qa.get('certificacao', '—')}) |
| 2 | Trust 100 é real? | {yn(ex.get('2_trust100Real'))} |
| 3 | Trust 100 é apenas técnico? | {yn(ex.get('3_trust100ApenasTecnico'))} |
| 4 | Cobertura real negócio | **{ex.get('4_coberturaRealNegocio', '—')}%** |
| 5 | Cobertura real pessoas | **{ex.get('5_coberturaRealPessoas', '—')}%** |
| 6 | Cobertura real financeira | **{ex.get('6_coberturaRealFinanceira', '—')}%** |
| 7 | Cobertura real operacional | **{ex.get('7_coberturaRealOperacional', '—')}%** |
| 8 | Cobertura real prestação | **{ex.get('8_coberturaRealPrestacao', '—')}%** |
| 9 | Campos ocultos | {', '.join(ex.get('9_camposOcultos') or []) or '—'} |
| 10 | Indicadores inferidos | {', '.join(ex.get('10_indicadoresInferidos') or []) or '—'} |
| 11 | Indicadores comprovados | {', '.join(ex.get('11_indicadoresComprovados') or []) or '—'} |
| 12 | Indicadores rebaixados | {', '.join(ex.get('12_indicadoresRebaixados') or []) or '—'} |
| 13 | Indicadores bloqueados | {', '.join(ex.get('13_indicadoresBloqueados') or []) or '—'} |
| 14 | Corporate Score confiável | {yn(ex.get('14_corporateScoreConfiavel'))} |
| 15 | Executive Score confiável | {yn(ex.get('15_executiveScoreConfiavel'))} |
| 16 | People Score confiável | {yn(ex.get('16_peopleScoreConfiavel'))} |
| 17 | Logos enxerga 100% operação | {yn(ex.get('17_logosEnxerga100Operacao'))} |
| 18 | Logos enxerga 100% pessoas | {yn(ex.get('18_logosEnxerga100Pessoas'))} |
| 19 | Pronto decisões automatizadas | {yn(ex.get('19_prontoDecisoesAutomatizadas'))} |
| 20 | D04 confirmado ou superestimado | **{ex.get('20_d04ConfirmadoOuSuperestimado', '—')}** |

## Trust Score Challenge

| Camada | Score |
|--------|-------|
| Técnico (D04) | **{trust.get('trustTecnico', '—')}** |
| Negócio | **{trust.get('trustNegocio', '—')}** |
| Executivo | **{trust.get('trustExecutivo', '—')}** |

## O que sabemos / achamos / não sabemos

**Sabemos:** {sabemos.get('snapshotsHomologados', '—')}

**Achamos que sabemos (mas é parcial):** People100 = {achamos.get('people100', '—')} · Prestação = {achamos.get('prestacao975', '—')}

**Não sabemos:** {', '.join((nao or {}).keys()) if isinstance(nao, dict) else '—'}

## Relatórios IA

- TECHNICAL_COVERAGE_AUDIT.md (IA-1)
- BUSINESS_COVERAGE_AUDIT.md (IA-2)
- PRESTACAO_GAP_AUDIT.md (IA-3)
- PEOPLE_COVERAGE_CHALLENGE_REPORT.md (IA-4)
- FINANCIAL_GAP_REPORT.md (IA-5)
- OPERATIONAL_GAP_REPORT.md (IA-6)
- HIDDEN_ENDPOINT_DISCOVERY_REPORT.md (IA-7)
- TRUST_SCORE_CHALLENGE_REPORT.md (IA-8)
- D04_CERTIFICATION_REPORT.md (IA-9)

---

{parecer}
""",
        encoding="utf-8",
    )

    print("Relatórios D04.1 gerados.")
    print(parecer)


if __name__ == "__main__":
    main()
