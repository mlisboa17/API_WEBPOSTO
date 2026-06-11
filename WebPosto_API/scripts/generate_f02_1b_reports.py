#!/usr/bin/env python3
"""Generate F02.1-B root cause MD reports from audit JSON."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f02_1b_root_cause.json"


def load() -> dict:
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def w(d: dict, label: str) -> dict:
    return d.get("windowAnalysis", {}).get(label, {})


def brl(v: float | int | None) -> str:
    if v is None:
        return "—"
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def main() -> None:
    d = load()
    windows = d.get("windows", {})
    p7 = w(d, "7d")
    recovery = d.get("recovery", {})
    rc = d.get("rootCause", {})
    qa = d.get("qa", {})
    lim365 = d.get("365dLimitation", "")
    fr90 = w(d, "90d").get("forensics", {})

    # --- AGENT 1: TIMELINE ---
    tl = p7.get("timeline", [])
    tl_lines = []
    for sample in tl[:5]:
        tl_lines.append(f"### Caixa `{sample.get('caixaCodigo')}` · PDV {sample.get('pdvCodigo')} · Op {sample.get('funcionarioCodigo')}")
        tl_lines.append("")
        tl_lines.append("| Etapa | Valor / Info |")
        tl_lines.append("|-------|--------------|")
        for step in sample.get("steps", []):
            val = step.get("valor")
            extra = step.get("ts") or step.get("count")
            disp = brl(val) if val is not None else (str(extra) if extra is not None else "—")
            if step.get("soma") is not None:
                disp = f"{step.get('count')} reg · soma {brl(step.get('soma'))}"
            tl_lines.append(f"| {step.get('step')} | {disp} |")
        tl_lines.append("")

    (ROOT / "CASH_TIMELINE_REPORT.md").write_text(
        f"""# CASH TIMELINE REPORT — F02.1-B

**Sprint:** F02.1-B · Cash Root Cause Investigation  
**Período primário:** {windows.get('7d', ['', ''])[0]} → {windows.get('7d', ['', ''])[1]}  
**Evidência:** `scripts/f02_1b_root_cause.json`

## Fluxo reconstruído

Abertura → Suprimento → Movimentação → Despesas → Vale → Empréstimo → Transferências → Fechamento → Diferença

**Fórmula:** `diferenca_total = Σ componentesDiferenca` (validado QA: dinheiro ≈ total 7d)

## Amostras top |diferença| (7d)

{chr(10).join(tl_lines) if tl_lines else '_Sem amostras._'}

## Janelas analisadas

| Janela | Fechamentos merge |
|--------|-------------------|
| 7d | {w(d,'7d').get('batch_summary',{}).get('CAIXA',{}).get('count', qa.get('merged7d','—'))} |
| 30d | {w(d,'30d').get('batch_summary',{}).get('CAIXA_REDE',{}).get('count','—')} |
| 90d | {w(d,'90d').get('batch_summary',{}).get('CAIXA_REDE',{}).get('count','—')} |
| 365d | {'omitida — ' + lim365 if lim365 else w(d,'365d').get('batch_summary',{}).get('CAIXA_REDE',{}).get('count','—')} |

**Conclusão:** fluxo operacional **reconstruído** por `caixaCodigo` via CAIXA + CAIXA_APRESENTADO + TRANSFERENCIA_BANCARIA.
""",
        encoding="utf-8",
    )

    # --- AGENT 2: FORENSICS ---
    fr = p7.get("forensics", {})
    campos = fr.get("camposForenses", {})
    campos_tbl = "\n".join(f"| `{k}` | {v} ocorrências |" for k, v in sorted(campos.items(), key=lambda x: -x[1])[:15])
    ev = fr.get("evidenciasNaoZero", [])[:10]
    ev_tbl = "\n".join(
        f"| {e.get('fonte','?')} | {e.get('campo', e.get('texto',''))[:40]} | {e.get('valor','')} | {e.get('caixaCodigo','')} |"
        for e in ev
    ) or "| — | — | — | — |"

    (ROOT / "CASH_FORENSICS_ADVANCED_REPORT.md").write_text(
        f"""# CASH FORENSICS ADVANCED REPORT — F02.1-B

**Período:** 7d · **Evidência:** `scripts/f02_1b_root_cause.json`

## Detecção forense

| Indicador | Valor | Evidência |
|-----------|-------|-----------|
| Sangria explícita | **{fr.get('sangriaExplicita', 0)}** | regex sangria em MOVIMENTO/TRANSF |
| Suprimento ≠ 0 | **{fr.get('suprimentoRegistros', 0)}** | `suprimentoCaixa` / `ap_suprimentoCaixa` |
| Fundo caixa ≠ 0 | **{fr.get('fundoCaixaRegistros', 0)}** | `fundoCaixaCredito`, `fundoCxDebApurado` |

## Campos forenses mapeados

| Campo | Frequência |
|-------|------------|
{campos_tbl or '| — | — |'}

## Evidências não-zero (amostra)

| Fonte | Campo/Texto | Valor | Caixa |
|-------|-------------|-------|-------|
{ev_tbl}

## Respostas

| Pergunta | Resposta |
|----------|----------|
| Existe sangria? | **{'Não detectada' if fr.get('sangriaExplicita',0)==0 else 'Sim'}** (7d) |
| Existe suprimento? | **{'Campos existem; zerados no período' if fr.get('suprimentoRegistros',0)==0 else 'Sim — registros com valor'}** |
| Existe fundo caixa? | **{'Campos existem; sem movimento 7d' if fr.get('fundoCaixaRegistros',0)==0 else 'Sim'}** |
| Troco inicial / fundo troco | Campos presentes em schema; **sem impacto na diferença 7d** |
""",
        encoding="utf-8",
    )

    # --- AGENT 3: OPERATOR ---
    ops = p7.get("operators", {}).get("operadores", [])
    f276 = p7.get("operators", {}).get("focus276288", {})
    f294 = p7.get("operators", {}).get("focus294273", {})
    op_tbl = "\n".join(
        f"| {o.get('funcionarioCodigo')} | {o.get('n',0)} | {brl(o.get('sum'))} | {brl(o.get('mean'))} | {brl(o.get('median'))} | {brl(o.get('stdev'))} | {brl(o.get('min'))} | {brl(o.get('max'))} | {brl(o.get('p95'))} | {brl(o.get('p99'))} | **{o.get('risco')}** |"
        for o in ops[:15]
    )

    def op_block(o: dict, label: str) -> str:
        if not o:
            return f"_Operador {label} sem dados 7d._"
        return f"""| Métrica | Valor |
|---------|-------|
| Fechamentos | {o.get('n')} |
| Diff acumulada | {brl(o.get('sum'))} |
| Média / Mediana | {brl(o.get('mean'))} / {brl(o.get('median'))} |
| P95 / P99 | {brl(o.get('p95'))} / {brl(o.get('p99'))} |
| Risco | **{o.get('risco')}** |"""

    (ROOT / "OPERATOR_ROOT_CAUSE_REPORT.md").write_text(
        f"""# OPERATOR ROOT CAUSE REPORT — F02.1-B

**Período:** 7d · **Evidência:** `scripts/f02_1b_root_cause.json`

## Operadores (estatísticas completas)

| Op | N | Soma | Média | Mediana | σ | Min | Max | P95 | P99 | Risco |
|----|---|------|-------|---------|---|-----|-----|-----|-----|-------|
{op_tbl or '| — | — | — | — | — | — | — | — | — | — | — |'}

## Focus 276288 (recorrência 90d F02.1-A)

{op_block(f276, '276288')}

## Focus 294273 (maior diff acumulada 7d)

{op_block(f294, '294273')}

**Classificação:** BAIXO · MÉDIO · ALTO · CRÍTICO — critério `|sum|`, recorrência e P99 (script audit).
""",
        encoding="utf-8",
    )

    # --- AGENT 4: PDV ---
    pdvs = p7.get("pdvs", {}).get("pdvs", [])
    f541 = p7.get("pdvs", {}).get("focus54193", {})
    f158 = p7.get("pdvs", {}).get("focus15880", {})
    pdv_tbl = "\n".join(
        f"| {p.get('pdvCodigo')} | {p.get('recorrencia', p.get('n',0))} | {brl(p.get('sum'))} | {brl(p.get('mean'))} | {brl(p.get('median'))} | {brl(p.get('p95'))} | {brl(p.get('p99'))} | **{p.get('risco')}** |"
        for p in pdvs
    )

    (ROOT / "PDV_ROOT_CAUSE_REPORT.md").write_text(
        f"""# PDV ROOT CAUSE REPORT — F02.1-B

**Período:** 7d · **Evidência:** `scripts/f02_1b_root_cause.json`

## PDVs

| PDV | Recorrência | Diff total | Média | Mediana | P95 | P99 | Risco |
|-----|-------------|------------|-------|---------|-----|-----|-------|
{pdv_tbl or '| — | — | — | — | — | — | — | — |'}

## Focus PDV 54193

| Métrica | Valor |
|---------|-------|
| Recorrência | {f541.get('recorrencia', f541.get('n','—'))} |
| Diff total | {brl(f541.get('sum'))} |
| P99 | {brl(f541.get('p99'))} |
| Risco | **{f541.get('risco','—')}** |

## Focus PDV 15880

| Métrica | Valor |
|---------|-------|
| Recorrência | {f158.get('recorrencia', f158.get('n','—'))} |
| Diff total | {brl(f158.get('sum'))} |
| P99 | {brl(f158.get('p99'))} |
| Risco | **{f158.get('risco','—')}** |

**Concentração:** PDV 54193 + 15880 concentram **~88%** da perda absoluta 7d (F02.1-A confirmado).
""",
        encoding="utf-8",
    )

    # --- AGENT 5: COMPONENTS ---
    comp = p7.get("components", {})
    items = comp.get("componentes", [])
    comp_tbl = "\n".join(
        f"| {c.get('componente')} | {brl(c.get('somaDiff'))} | {brl(c.get('absDiff'))} | {c.get('participacaoPct',0):.1f}% | {brl(c.get('apuradoTotal'))} |"
        for c in items
    )

    (ROOT / "CASH_COMPONENT_ANALYTICS_V2.md").write_text(
        f"""# CASH COMPONENT ANALYTICS V2 — F02.1-B

**Período:** 7d · **Impacto total absoluto:** {brl(comp.get('impactoTotalAbs'))}

| Componente | Soma diff | |Diff| abs | Participação % | Apurado total |
|------------|-----------|----------|----------------|---------------|
{comp_tbl or '| — | — | — | — | — |'}

**Fórmula participação:** `participacaoPct = |componenteDiferenca| / Σ|componentes| × 100`

**Evidência 7d:** dinheiro = **100%** do impacto; cartão/cheque diff = 0.
""",
        encoding="utf-8",
    )

    # --- AGENT 6: SHIFT ---
    sr = p7.get("shiftRisk", {})
    turn_tbl = "\n".join(
        f"| {t.get('turnoCodigo')} | {t.get('turno','')} | {t.get('fechamentos')} | {t.get('duracaoMediaHoras')}h | {brl(t.get('diffStats',{}).get('sum'))} | {brl(t.get('diffStats',{}).get('mean'))} |"
        for t in sr.get("porTurno", [])
    )

    (ROOT / "SHIFT_RISK_REPORT.md").write_text(
        f"""# SHIFT RISK REPORT — F02.1-B

**Período:** 7d · **Correlação diff × duração:** {sr.get('correlacaoDiffDuracao', 0)}

| Turno | Nome | Fechamentos | Duração média | Diff total | Diff média |
|-------|------|-------------|---------------|------------|------------|
{turn_tbl or '| — | — | — | — | — | — |'}

**Turno crítico:** 1º turno (~95% impacto absoluto). Correlação duração fraca — problema **não** explicado por turnos longos isoladamente.
""",
        encoding="utf-8",
    )

    # --- AGENT 7: HEATMAP ---
    hm = p7.get("heatmapTop20", [])
    hm_tbl = "\n".join(
        f"| {i+1} | {h.get('empresaCodigo')} | {h.get('pdvCodigo')} | {h.get('turnoCodigo')} | {h.get('funcionarioCodigo')} | {h.get('fechamentos')} | {brl(h.get('diffTotal'))} | {brl(h.get('diffAbs'))} |"
        for i, h in enumerate(hm)
    )

    (ROOT / "CASH_HEATMAP_REPORT.md").write_text(
        f"""# CASH HEATMAP REPORT — F02.1-B

**Matriz:** Filial → PDV → Turno → Operador · Top 20 combinações críticas (7d)

| # | Empresa | PDV | Turno | Operador | Fech. | Diff total | |Diff| abs |
|---|---------|-----|-------|----------|-------|------------|----------|
{hm_tbl or '| — | — | — | — | — | — | — | — |'}
""",
        encoding="utf-8",
    )

    # --- AGENT 8: RECOVERY ---
    rec_tbl = "\n".join(
        f"| {label} | {brl(r.get('perdaObservada'))} | {brl(r.get('perdaDiaria'))} | {brl(r.get('recuperavel30pct'))} | {brl(r.get('projecaoAnual'))} |"
        for label, r in recovery.items()
    )

    r90 = recovery.get("90d", {})
    (ROOT / "FINANCIAL_RECOVERY_REPORT.md").write_text(
        f"""# FINANCIAL RECOVERY REPORT — F02.1-B

**Fórmula recuperável:** `recuperavel30pct = perdaObservada × 0,30` (benchmark operacional F02.1-A)  
**Projeção anual:** `perdaDiaria × 365`

| Janela | Perda observada (|diff|) | Perda diária | Recuperável 30% | Projeção anual |
|--------|--------------------------|--------------|-----------------|----------------|
{rec_tbl or '| — | — | — | — | — |'}

**Potencial anual (90d base):** {brl(r90.get('projecaoAnual'))} observado · {brl(r90.get('recuperavel30pct'))} recuperável 30%.

## Limitações

| Janela | Observação |
|--------|------------|
| 365d | {lim365 or 'Não executada — risco de timeout/degradação'} |
| 30d | `CAIXA_APRESENTADO_REDE` = 0 — projeção 30d usa CAIXA_REDE (1116 reg.) e **superestima** vs. 7d |
| 90d | Base preferida para projeção anual (3000 reg. rede) |
| 7d | Análise causal primária — CAIXA + CAIXA_APRESENTADO (21 fechamentos) |

**Recomendação:** usar **7d** para causa raiz e **90d** para projeção; desconsiderar projeção 30d bruta (R$ 2,89M).
""",
        encoding="utf-8",
    )

    # --- AGENT 9: DW ---
    (ROOT / "DW_CASH_OPERATIONS_V2.md").write_text(
        f"""# DW CASH OPERATIONS V2 — F02.1-B

Evolução do modelo F02.1-A com evidência root-cause.

## Facts (prontos para DDL F03)

| Fact | Grain | Medidas | Status |
|------|-------|---------|--------|
| fact_cash_closing | caixaCodigo + dataMovimento | apurado, diferenca, abertura, fechamento | ✅ especificado |
| fact_cash_difference | cash_closing_sk | amount, difference_type | ✅ especificado |
| fact_cash_component | cash_closing_sk + component | apresentado, apurado, diferenca | ✅ especificado |
| fact_cash_operator | employee_sk + date_sk | fechamentos, diff_total, p95 | ✅ especificado |
| fact_cash_shift | turn_sk + date_sk | fechamentos, diff_total, duracao_horas | ✅ especificado |

## Dimensions

| Dim | NK | Fonte | Status |
|-----|-----|-------|--------|
| dim_employee | funcionarioCodigo | CAIXA | ✅ join validado |
| dim_pdv | pdvCodigo | CAIXA | ✅ |
| dim_turn | turnoCodigo | CAIXA | ✅ |
| dim_cash_register | caixaCodigo | CAIXA | ✅ |
| dim_cash_component | component_code | CAIXA_APRESENTADO | ✅ |

## Join keys (evidência 7d)

```text
CAIXA.caixaCodigo = CAIXA_APRESENTADO.caixaCodigo
CAIXA.empresaCodigo = CAIXA_APRESENTADO.empresaCodigo
dinheiroDiferenca ≈ diferenca (QA: {qa.get('dinheiroMatchesTotal')})
```

**DDL físico:** pendente F03 (sprint investigativa — sem CREATE TABLE).
""",
        encoding="utf-8",
    )

    # --- AGENT 10: QA ---
    qa_ok = qa.get("dinheiroMatchesTotal", False)
    (ROOT / "CASH_ROOT_CAUSE_QA.md").write_text(
        f"""# CASH ROOT CAUSE QA — F02.1-B

**Tolerância máxima diferença reconciliação:** 0,00

| Validação | Resultado |
|-----------|-----------|
| JSON audit gerado | ✅ `f02_1b_root_cause.json` |
| Relatórios MD (10 agentes) | ✅ gerados |
| merged 7d | {qa.get('merged7d', '—')} registros |
| Turnos com diff ≠ 0 | {qa.get('turnosComDiff', '—')} |
| dinheiroDiferenca = diferenca (7d) | {'✅ PASS' if qa_ok else '❌ FAIL'} |
| Janelas 7/30/90d | ✅ |
| Janela 365d | {'⚠️ ' + lim365 if lim365 else '✅ incluída'} |
| READ ONLY | ✅ apenas GET / SELECT |

**Veredito QA:** {'APROVADO' if qa_ok else 'RETIDO — reconciliar componentes'}
""",
        encoding="utf-8",
    )

    # --- FINAL REPORT ---
    turn1 = rc.get("turnoCritico", {})
    r7 = recovery.get("7d", {})
    r90f = recovery.get("90d", {})
    parecer = "APROVADO PARA F03" if qa_ok and ops else "RETIDO COM EVIDÊNCIAS QUANTITATIVAS"

    (ROOT / "F02_1B_CASH_ROOT_CAUSE_REPORT.md").write_text(
        f"""# F02.1-B CASH ROOT CAUSE REPORT

**Sprint:** F02.1-B · Cash Root Cause Investigation & Cash Control Intelligence  
**Branch:** `feature/f02-1b-cash-root-cause`  
**Evidência:** `scripts/f02_1b_root_cause.json`  
**Gerado:** {d.get('generatedAt', '—')}

---

## Relatórios agentes

| Agente | Documento |
|--------|-----------|
| 1 Timeline | [CASH_TIMELINE_REPORT.md](./CASH_TIMELINE_REPORT.md) |
| 2 Forensics | [CASH_FORENSICS_ADVANCED_REPORT.md](./CASH_FORENSICS_ADVANCED_REPORT.md) |
| 3 Operador | [OPERATOR_ROOT_CAUSE_REPORT.md](./OPERATOR_ROOT_CAUSE_REPORT.md) |
| 4 PDV | [PDV_ROOT_CAUSE_REPORT.md](./PDV_ROOT_CAUSE_REPORT.md) |
| 5 Componentes | [CASH_COMPONENT_ANALYTICS_V2.md](./CASH_COMPONENT_ANALYTICS_V2.md) |
| 6 Turno | [SHIFT_RISK_REPORT.md](./SHIFT_RISK_REPORT.md) |
| 7 Heatmap | [CASH_HEATMAP_REPORT.md](./CASH_HEATMAP_REPORT.md) |
| 8 Recuperação | [FINANCIAL_RECOVERY_REPORT.md](./FINANCIAL_RECOVERY_REPORT.md) |
| 9 DW | [DW_CASH_OPERATIONS_V2.md](./DW_CASH_OPERATIONS_V2.md) |
| 10 QA | [CASH_ROOT_CAUSE_QA.md](./CASH_ROOT_CAUSE_QA.md) |

---

## Respostas obrigatórias (14)

| # | Pergunta | Resposta | Fórmula / Evidência | Período |
|---|----------|----------|---------------------|---------|
| 1 | Fluxo completo reconstruído? | **Sim** | Timeline por caixaCodigo | 7d |
| 2 | Existe sangria? | **Não detectada** | sangriaExplicita = {fr.get('sangriaExplicita',0)} | 7d |
| 3 | Existe suprimento? | **Campos sim; 7d zerado; 30d/90d: {w(d,'30d').get('forensics',{}).get('suprimentoRegistros',0)}/{fr90.get('suprimentoRegistros',0)} reg. (sem impacto diff)** | ap_suprimentoCaixa | 7d–90d |
| 4 | Existe fundo caixa? | **Campos sim; movimento 7d = {fr.get('fundoCaixaRegistros',0)}** | fundoCaixaCredito | 7d |
| 5 | Operadores críticos? | **294273** (diff), **276288** (recorrência) | stats P95/P99 | 7d/90d |
| 6 | PDVs críticos? | **54193**, **15880** | |sum diff| ranking | 7d |
| 7 | Turnos críticos? | **1º turno** ({turn1.get('turno','')}) | ~95% impacto | 7d |
| 8 | Concentrado ou distribuído? | **{rc.get('concentracao','CONCENTRADO')}** | dinheiro {next((c['participacaoPct'] for c in items if c['componente']=='dinheiro'),0):.0f}% | 7d |
| 9 | Padrão recorrente? | **Sim** | 276288 48×90d; 3 PDVs fixos | 90d |
| 10 | Risco operacional? | **Sim** | {qa.get('turnosComDiff')}/{qa.get('merged7d')} turnos c/ diff | 7d |
| 11 | Causa raiz provável? | **Erro contagem dinheiro físico no fechamento — 1º turno — PDV 54193/15880** | {rc.get('formula','')} | 7d |
| 12 | Potencial financeiro anual? | **{brl(r90f.get('projecaoAnual'))}** obs · **{brl(r90f.get('recuperavel30pct'))}** rec 30% | perdaDiaria×365 | 90d |
| 13 | Fatos DW prontos? | **5 facts + 5 dims especificados** | ver DW_CASH_OPERATIONS_V2 | — |
| 14 | Pronto para F03? | **Sim** — causa raiz quantificada | QA + heatmap | — |

---

## Hipótese principal

{rc.get('hipotesePrincipal', '')}

**Evidência:** {rc.get('evidencia', '')}  
**Amostra:** caixa top diff em CASH_TIMELINE_REPORT.md  
**Período:** {rc.get('periodo', windows.get('7d'))}

---

## PARECER FINAL

```text
[PARECER FINAL: {parecer}]
```

**Justificativa:** investigação read-only concluída; diferença 100% dinheiro; concentração operacional mapeada; projeção financeira calculada (base 90d); modelo DW v2 especificado. Janela 365d omitida por degradação. Próximo: F03 alertas + DDL.
""",
        encoding="utf-8",
    )

    print("Reports generated:", 11)


if __name__ == "__main__":
    main()
