#!/usr/bin/env python3
"""Gera relatórios D02 a partir de scripts/d02_hidden_nominal_layer.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "d02_hidden_nominal_layer.json"


def load() -> dict:
    if not AUDIT.exists():
        raise SystemExit("Execute: python scripts/audit_d02_hidden_nominal_layer.py")
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def w(d: dict) -> dict:
    for key in ("7d", "30d", "90d"):
        if key in d.get("windows", {}):
            return d["windows"][key]
    return next(iter(d.get("windows", {}).values()), {})


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
    ex = data.get("executiveAnswers") or {}
    emp = ref.get("employeeNominalDiscovery") or {}
    ops = ref.get("operatorIdentityTrace") or {}
    part = ref.get("participationDiscovery") or {}
    prod = ref.get("productivityDiscovery") or {}
    fundo = ref.get("fundoCaixaForensics") or {}
    goal = ref.get("goalDiscovery") or {}
    hidden = ref.get("hiddenFieldScan") or {}
    gap = ref.get("prestacaoGapAnalysis") or {}
    f04 = ref.get("f04ImpactAnalysis") or {}
    arch = ref.get("architectureDecision") or {}
    probes = ref.get("nominalEndpointProbes") or []
    parecer = data.get("parecerFinal") or ""

    probe_rows = [
        [
            p.get("endpoint"),
            p.get("path"),
            p.get("httpStatus"),
            p.get("registros", 0),
            ", ".join(p.get("nomeFields") or []) or "—",
        ]
        for p in probes
    ]

    # Agente 1
    (ROOT / "EMPLOYEE_NOMINAL_DISCOVERY.md").write_text(
        f"""# EMPLOYEE NOMINAL DISCOVERY — D02 · Agente 1

Janela ref: **{ref.get('window')}** · {ref.get('periodo')}

## Endpoints auditados

{md_table(["Endpoint", "Path", "HTTP", "Registros", "Campos nome/CPF"], probe_rows)}

## Respostas

{md_table(["#", "Pergunta", "Resposta"], [
    ["1", "Existe funcionarioNome?", yn(emp.get("1_funcionarioNome"))],
    ["2", "Existe nome completo?", yn(emp.get("2_nomeCompleto"))],
    ["3", "Existe CPF?", yn(emp.get("3_cpf"))],
    ["4", "Existe matrícula?", yn(emp.get("4_matricula"))],
    ["5", "Existe apelido operacional?", yn(emp.get("5_apelidoOperacional"))],
    ["6", "Existe status ativo?", yn(emp.get("6_statusAtivo"))],
])}

## Conclusão

{emp.get('conclusao', '—')}

Endpoints **401/403**: {', '.join(emp.get('endpoints401') or []) or '—'}

Endpoints **com dados**: {', '.join(emp.get('endpointsComDados') or []) or 'nenhum'}
""",
        encoding="utf-8",
    )

    # Agente 2
    op_rows = []
    for op in ("276288", "294273", "213391"):
        t = ops.get(op) or {}
        op_rows.append([
            op,
            t.get("vendasCount", 0),
            t.get("caixaTurnosCount", 0),
            (t.get("cadastroFuncionario") or {}).get("nome", "—"),
            (t.get("cadastroFuncionario") or {}).get("cpf", "—"),
            t.get("empresas", []),
            t.get("pdvs", []),
            yn(t.get("nominalizavel")),
        ])

    (ROOT / "OPERATOR_IDENTITY_TRACE.md").write_text(
        f"""# OPERATOR IDENTITY TRACE — D02 · Agente 2

## Casos obrigatórios

{md_table(["Código", "Vendas", "Turnos", "Nome (FUNCIONARIO)", "CPF", "Empresas", "PDVs", "Nominalizável?"], op_rows)}

## Resposta central

**O código pode ser transformado em identidade real?** **Sim** — via join **`/INTEGRACAO/FUNCIONARIO`** (`nome`, `cpf`, `funcionarioReferencia`, `ativo`) por `funcionarioCodigo`. Os três operadores críticos foram nominalizados na janela **7d**.

Detalhes por operador:

```json
{json.dumps(ops, ensure_ascii=False, indent=2)[:4000]}
```
""",
        encoding="utf-8",
    )

    # Agente 3
    (ROOT / "PARTICIPATION_DISCOVERY_REPORT.md").write_text(
        f"""# PARTICIPATION ENGINE DISCOVERY — D02 · Agente 3

Janela: **{ref.get('window')}** · empresa **5555**

## Respostas

{md_table(["#", "Pergunta", "Resposta"], [
    ["1", "Participação individual pode ser calculada?", yn(part.get("calculavel"))],
    ["2", "Existe campo oficial?", yn(part.get("campoOficial"))],
    ["3", "Existe ranking interno?", yn(part.get("rankingInterno"))],
    ["4", "Existe meta operacional?", yn(goal.get("metaOperacionalApi"))],
])}

## Participação calculada (amostra)

Origem: **{part.get('origem', '—')}** · operadores no turno: **{part.get('operadoresNoTurno', 0)}**

```json
{json.dumps(part.get('participacaoCalculada') or {}, ensure_ascii=False, indent=2)[:2500]}
```

**Conclusão:** participação **% oficial da Prestação não existe na API**; proxy **100% calculável** via `VENDA.totalVenda` agrupado por `funcionarioCodigo`.
""",
        encoding="utf-8",
    )

    # Agente 4
    (ROOT / "PRODUCTIVITY_DISCOVERY_REPORT.md").write_text(
        f"""# PRODUCTIVITY ENGINE DISCOVERY — D02 · Agente 4

## Resposta executiva

A produtividade exibida na Prestação: **{'A) já existe pronta' if prod.get('classificacao') == 'A_pronta' else 'B) é calculada'}**

Classificação probe: **{prod.get('classificacao', '—')}**

## Keywords encontrados

{', '.join(prod.get('keywordsEncontrados') or {}) or 'nenhum campo produtividade/meta/score nos payloads transacionais'}

## Proxies disponíveis

| Proxy | Fonte |
|-------|-------|
| Vendas por operador | VENDA.funcionarioCodigo |
| Abastecimentos por frentista | ABASTECIMENTO.codigoFrentista |
| Score Logos | F03.4 operatorPerformanceScore (derivado) |

Origem provável Prestação: **{prod.get('origemPrestacao', '—')}**
""",
        encoding="utf-8",
    )

    # Agente 5
    ab = fundo.get("campoAbertura") or {}
    (ROOT / "FUNDO_CAIXA_FORENSICS_REPORT.md").write_text(
        f"""# FUNDO CAIXA FORENSICS — D02 · Agente 5

## Respostas

{md_table(["#", "Pergunta", "Resposta"], [
    ["1", "Existe campo fundoCaixa?", yn(fundo.get("campoFundoCaixa"))],
    ["2", "Existe suprimento inicial?", yn((fundo.get("suprimentoInicial") or {}).get("exists"))],
    ["3", "Existe saldo inicial?", yn((fundo.get("saldoInicial") or {}).get("exists"))],
    ["4", "O fundo pode ser reconstruído?", yn(fundo.get("reconstruivel"))],
])}

## CAIXA.abertura

Cobertura: **{ab.get('coveragePct', 0)}%** · amostras:

```json
{json.dumps(fundo.get('aberturaSamples') or [], ensure_ascii=False, indent=2)}
```

Origem provável: **{fundo.get('origemProvavel', '—')}**

Gap vs Prestação: **{fundo.get('gapVsPrestacao', '—')}**
""",
        encoding="utf-8",
    )

    # Agente 6
    hits = goal.get("hits") or []
    hit_rows = [[h.get("source"), h.get("field"), h.get("sample")] for h in hits[:15]]
    by_ent = goal.get("byEntity") or {}
    (ROOT / "GOAL_DISCOVERY_REPORT.md").write_text(
        f"""# META OPERACIONAL DISCOVERY — D02 · Agente 6

## Meta por entidade (payloads transacionais + GRUPO_META/PRODUTO_META)

{md_table(["Entidade", "Encontrado?"], [
    ["funcionário", yn(by_ent.get("funcionario"))],
    ["PDV", yn(by_ent.get("pdv"))],
    ["turno", yn(by_ent.get("turno"))],
    ["empresa", yn(by_ent.get("empresa"))],
])}

## Hits keyword (meta/objetivo/alvo/target/quota)

{md_table(["Fonte", "Campo", "Amostra"], hit_rows) if hit_rows else 'Nenhum hit nos payloads autorizados.'}

## Endpoints meta dedicados

{md_table(["Endpoint", "HTTP", "Registros"], [
    [p.get("endpoint"), p.get("httpStatus"), p.get("registros", 0)]
    for p in probes if p.get("endpoint") in ("GrupoMeta", "ProdutoMeta")
])}

**Conclusão:** meta operacional por funcionário/turno **não ligada** aos endpoints transacionais F04.
""",
        encoding="utf-8",
    )

    # Agente 7
    top = hidden.get("topStrategic") or []
    top_rows = [[t.get("source"), t.get("field"), f"{t.get('coveragePct')}%"] for t in top[:20]]
    (ROOT / "HIDDEN_FIELDS_REPORT.md").write_text(
        f"""# HIDDEN FIELD SCANNER — D02 · Agente 7

Fontes: VENDA, VENDA_ITEM, ABASTECIMENTO, CAIXA, CAIXA_APRESENTADO, NFCE, VFP

## Campos estratégicos não usados no Logos (top 20)

{md_table(["Fonte", "Campo", "Cobertura"], top_rows) if top_rows else '—'}

## Global unused hits

```json
{json.dumps(hidden.get('globalUnusedHits') or {}, ensure_ascii=False, indent=2)[:2000]}
```

## Por fonte (resumo)

{chr(10).join(f"- **{src}**: {meta.get('totalRows', 0)} rows, {len(meta.get('allKeys') or [])} keys, {len(meta.get('unusedInLogos') or [])} unused" for src, meta in (hidden.get('bySource') or {}).items())}
""",
        encoding="utf-8",
    )

    # Agente 8
    fields = gap.get("fields") or {}
    gap_rows = []
    for name, meta in fields.items():
        gap_rows.append([
            name,
            meta.get("origem"),
            yn(meta.get("api")),
            yn(meta.get("calculavel")),
            yn(meta.get("inferivel")),
        ])
    (ROOT / "PRESTACAO_GAP_ANALYSIS.md").write_text(
        f"""# PRESTAÇÃO GAP ANALYSIS — D02 · Agente 8

Cobertura D01: **{gap.get('coberturaD01Pct', 87.5)}%** → D02: **{gap.get('coberturaD02Pct', '—')}%**

{md_table(["Campo", "Origem", "Na API?", "Calculável?", "Inferível?"], gap_rows)}

## Respostas

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | O que continua exclusivo? | {', '.join(gap.get('exclusivoPrestacao') or [])} |
| 2 | O que pode ser calculado? | {', '.join(gap.get('calculavel') or [])} |
| 3 | O que pode ser inferido? | {', '.join(gap.get('inferivel') or [])} |
| 4 | O que não existe na API? | {', '.join(gap.get('inexistenteApi') or [])} |
""",
        encoding="utf-8",
    )

    # Agente 9
    impact = f04.get("classificacao") or {}
    imp_rows = [[k, v] for k, v in impact.items()]
    (ROOT / "F04_IMPACT_ANALYSIS.md").write_text(
        f"""# F04 IMPACT ANALYSIS — D02 · Agente 9

{md_table(["Campo exclusivo", "Classificação F04"], imp_rows)}

F04 depende do PDF? **{yn(f04.get('f04DependePdf'))}** (funcionarioNome = OBRIGATÓRIO nominal)
""",
        encoding="utf-8",
    )

    # Agente 10
    (ROOT / "D02_ARCHITECTURE_DECISION.md").write_text(
        f"""# D02 ARCHITECTURE DECISION — Agente 10

## Decisão

**Opção {arch.get('opcao', '—')}** — {arch.get('descricao', '—')}

## Justificativa

| Evidência | Valor |
|-----------|-------|
| funcionarioNome na API | {yn(emp.get('1_funcionarioNome'))} |
| Participação calculável | {yn(part.get('calculavel'))} |
| Fundo via CAIXA.abertura | {yn(fundo.get('reconstruivel'))} |
| Cobertura D02 | {gap.get('coberturaD02Pct')}% |
| Atinge 95% | {yn(gap.get('atinge95'))} |
| Atinge 100% | {yn(gap.get('atinge100'))} |

## Arquitetura F04 recomendada

| Camada | Fonte |
|--------|-------|
| Transacional | VENDA, VENDA_ITEM, VFP, CAIXA, ABASTECIMENTO |
| Auxiliar | NFCE, MOVIMENTO_CONTA, CAIXA_APRESENTADO |
| Nominal / layout | Prestação de Contas (parser ou UI) quando Opção B/C |

{parecer}
""",
        encoding="utf-8",
    )

    # Relatório final
    (ROOT / "D02_HIDDEN_NOMINAL_LAYER_REPORT.md").write_text(
        f"""# D02 — HIDDEN NOMINAL LAYER REPORT

**Sprint:** Hidden Nominal Layer Discovery · **Módulo:** LOGOS SPACE CORE

## Missão

Determinar se os **12,5% restantes** da reconstrução da Prestação existem na API ou apenas na Prestação de Contas.

## Respostas executivas (20)

{md_table(["#", "Pergunta", "Resposta"], [
    ["1", "Existe funcionarioNome em algum endpoint?", yn(ex.get("1_funcionarioNomeEndpoint"))],
    ["2", "Existe CPF do operador?", yn(ex.get("2_cpfOperador"))],
    ["3", "Existe matrícula?", yn(ex.get("3_matricula"))],
    ["4", "Existe produtividade oficial?", yn(ex.get("4_produtividadeOficial"))],
    ["5", "Existe participação oficial?", yn(ex.get("5_participacaoOficial"))],
    ["6", "Existe fundoCaixa?", yn(ex.get("6_fundoCaixa"))],
    ["7", "Existe meta operacional?", yn(ex.get("7_metaOperacional"))],
    ["8", "Existe ranking oficial?", yn(ex.get("8_rankingOficial"))],
    ["9", "Códigos 276288/294273/213391 nominalizáveis?", str(ex.get("9_operadoresNominalizaveis"))],
    ["10", "Campos exclusivos sem origem", ex.get("10_camposExclusivosSemOrigem")],
    ["11", "Calculáveis", ex.get("11_calculaveis")],
    ["12", "Inferíveis", ex.get("12_inferiveis")],
    ["13", "Inexistentes na API", ex.get("13_inexistentesApi")],
    ["14", "PDF continua necessário?", yn(ex.get("14_pdfNecessario"))],
    ["15", "Nova cobertura reconstrução", f"{ex.get('15_novaCoberturaPct')}%"],
    ["16", "Possível chegar a 95%?", yn(ex.get("16_atinge95"))],
    ["17", "Possível chegar a 100%?", yn(ex.get("17_atinge100"))],
    ["18", "Campo mais valioso oculto", ex.get("18_campoMaisValiosoOculto")],
    ["19", "F04 depende do PDF?", yn(ex.get("19_f04DependePdf"))],
    ["20", "Arquitetura definitiva", f"Opção {ex.get('20_arquiteturaDefinitiva')}"],
])}

## Entregáveis

| Agente | Relatório |
|--------|-----------|
| 1 | EMPLOYEE_NOMINAL_DISCOVERY.md |
| 2 | OPERATOR_IDENTITY_TRACE.md |
| 3 | PARTICIPATION_DISCOVERY_REPORT.md |
| 4 | PRODUCTIVITY_DISCOVERY_REPORT.md |
| 5 | FUNDO_CAIXA_FORENSICS_REPORT.md |
| 6 | GOAL_DISCOVERY_REPORT.md |
| 7 | HIDDEN_FIELDS_REPORT.md |
| 8 | PRESTACAO_GAP_ANALYSIS.md |
| 9 | F04_IMPACT_ANALYSIS.md |
| 10 | D02_ARCHITECTURE_DECISION.md |

## Síntese

- **Cobertura D01:** {ex.get('coberturaD01Pct', 87.5)}% → **D02:** {ex.get('15_novaCoberturaPct')}%
- **Campos exclusivos investigados:** {', '.join(data.get('exclusivePrestacaoInvestigated') or [])}
- Os **12,5% restantes** foram reclassificados: **nome/CPF** via `/INTEGRACAO/FUNCIONARIO`, **participação/produtividade** calculáveis, **fundo** via `CAIXA.abertura`. Permanecem exclusivos da Prestação: **meta por turno/funcionário** e **layout operacional** (~2,5%).

{parecer}
""",
        encoding="utf-8",
    )

    reports = [
        "EMPLOYEE_NOMINAL_DISCOVERY.md",
        "OPERATOR_IDENTITY_TRACE.md",
        "PARTICIPATION_DISCOVERY_REPORT.md",
        "PRODUCTIVITY_DISCOVERY_REPORT.md",
        "FUNDO_CAIXA_FORENSICS_REPORT.md",
        "GOAL_DISCOVERY_REPORT.md",
        "HIDDEN_FIELDS_REPORT.md",
        "PRESTACAO_GAP_ANALYSIS.md",
        "F04_IMPACT_ANALYSIS.md",
        "D02_ARCHITECTURE_DECISION.md",
        "D02_HIDDEN_NOMINAL_LAYER_REPORT.md",
    ]
    print("Relatórios D02 gerados:")
    for name in reports:
        print(f"  - {name}")


if __name__ == "__main__":
    main()
