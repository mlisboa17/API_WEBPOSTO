#!/usr/bin/env python3
"""Generate F03.4 Operator Performance Intelligence reports."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
AUDIT = ROOT / "scripts" / "f03_4_operator_performance.json"


def load() -> dict:
    if not AUDIT.exists():
        raise SystemExit("Execute scripts/audit_f03_4_operator_performance.py primeiro.")
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def w(d: dict, label: str) -> dict:
    windows = d.get("windows", {})
    if label in windows:
        return windows[label]
    for fallback in ("90d", "30d", "7d"):
        if fallback in windows:
            return windows[fallback]
    return {}


def brl(v) -> str:
    if v is None:
        return "—"
    return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def band_line(items: list, key: str, limit: int = 20) -> str:
    if not items:
        return "| — | — | — | — | — | — |"
    lines = []
    for item in items[:limit]:
        lines.append(
            f"| {item.get(key)} | {item.get('performanceScore')} | {item.get('performanceBand')} | "
            f"{brl(item.get('diferencaAcumulada'))} | {item.get('indiceRecorrencia')} | {item.get('cashRiskScore')} |"
        )
    return "\n".join(lines)


def resolve_context_attribution(wdata: dict, ops: dict, pdvs: dict, turns: dict) -> dict:
    ctx = wdata.get("contextAttribution")
    if ctx:
        return ctx
    from src.services.operator_context_attribution_service import OperatorContextAttributionService

    op_list = ops.get("todos") or ops.get("ranking") or []
    pdv_list = pdvs.get("ranking") or []
    turn_list = turns.get("ranking") or []
    merged = OperatorContextAttributionService.reconstruct_merged_from_rankings(pdv_list, op_list)
    return OperatorContextAttributionService.build(merged, op_list, pdv_list, turn_list, wdata.get("filiais") or [])


def ctx_line(items: list, limit: int = 15) -> str:
    if not items:
        return "| — | — | — | — | — | — |"
    lines = []
    for item in items[:limit]:
        lines.append(
            f"| {item.get('funcionarioCodigo')} | {item.get('operatorPerformanceScore')} | "
            f"{item.get('contextAdjustedPerformanceScore')} | {item.get('pdvDiversityScore')} | "
            f"{item.get('turnDiversityScore')} | {item.get('contextClassification')} |"
        )
    return "\n".join(lines)


def main() -> None:
    d = load()
    w90 = w(d, "90d")
    w7 = w(d, "7d")
    summary = w90.get("summary") or {}
    ops = w90.get("operators") or {}
    pdvs = w90.get("pdvs") or {}
    turns = w90.get("turns") or {}
    evo = w90.get("evolution") or {}
    best = w90.get("bestPractices") or {}
    formula = w90.get("formula") or {}
    crit = w90.get("criticalFocus") or {}
    qa = d.get("qa") or {}
    ex = d.get("executiveAnswers") or {}
    snap_ms = w90.get("snapshotHotMs")
    context = resolve_context_attribution(w90, ops, pdvs, turns)
    ctx_q = context.get("mandatoryQuestions") or {}
    ctx_ex = context.get("executiveAnswers") or {}
    ctx_cases = context.get("mandatoryCases") or {}
    ex = {**ex, **ctx_ex}

    def _fmt_list(val) -> str:
        if isinstance(val, list):
            if val and isinstance(val[0], dict):
                return ", ".join(str(x.get("funcionarioCodigo")) for x in val[:5])
            return str(val)
        return str(val)

    paridade_ok = qa.get("paridadeOk", False)
    snap_ok = qa.get("snapshotUnder500ms", False) and snap_ms is not None and snap_ms < 500
    approved = paridade_ok and snap_ok and not w90.get("error")
    parecer = (
        "[PARECER FINAL: APROVADO PARA F04]"
        if approved
        else "[PARECER FINAL: RETIDO COM JUSTIFICATIVA QUANTITATIVA]"
    )

    pesos = formula.get("pesos") or {}

    (ROOT / "OPERATOR_PERFORMANCE_ENGINE_REPORT.md").write_text(
        f"""# OPERATOR PERFORMANCE ENGINE — F03.4 · Agente 1

## Fórmula

```text
OperatorPerformanceScore (0–100)
= 40% Diferenças de Caixa
+ 25% Recorrência
+ 15% Cash Risk Score
+ 10% Sobras Compensadas
+ 10% Evolução Temporal
```

## Pesos aplicados

| Componente | Peso |
|------------|------|
| Diferença caixa | {pesos.get('diferencaCaixa', 0.4)} |
| Recorrência | {pesos.get('recorrencia', 0.25)} |
| Cash Risk | {pesos.get('cashRiskScore', 0.15)} |
| Sobras compensadas | {pesos.get('sobrasCompensadas', 0.10)} |
| Evolução temporal | {pesos.get('evolucaoTemporal', 0.10)} |

## Bandas

| Faixa | Classificação |
|-------|---------------|
| 90–100 | Excelente |
| 75–89 | Bom |
| 60–74 | Atenção |
| 0–59 | Crítico |

## Resultado rede (90d)

| Métrica | Valor |
|---------|-------|
| Score médio | **{summary.get('operatorPerformanceScoreMedio')}** |
| Operadores classificados | **{summary.get('operadoresClassificados')}** |
| Excelentes | **{summary.get('excelentes')}** |
| Críticos | **{summary.get('criticos')}** |
| Build ms | **{w90.get('buildMs')}** |

## Casos críticos monitorados

| Alvo | Score | Banda |
|------|-------|-------|
| Operador 276288 | {(crit.get('operador276288') or {}).get('performanceScore')} | {(crit.get('operador276288') or {}).get('performanceBand')} |
| Operador 294273 | {(crit.get('operador294273') or {}).get('performanceScore')} | {(crit.get('operador294273') or {}).get('performanceBand')} |
| PDV 54193 | {(crit.get('pdv54193') or {}).get('performanceScore')} | {(crit.get('pdv54193') or {}).get('performanceBand')} |
| PDV 15880 | {(crit.get('pdv15880') or {}).get('performanceScore')} | {(crit.get('pdv15880') or {}).get('performanceBand')} |
""",
        encoding="utf-8",
    )

    ranking = ops.get("ranking") or ops.get("topMelhores") or []
    piores = ops.get("topPiores") or list(reversed(ranking[-20:]))

    (ROOT / "TOP_OPERATORS_REPORT.md").write_text(
        f"""# TOP OPERATORS ANALYTICS — F03.4 · Agente 2

## Top 20 Melhores

| Operador | Score | Banda | Dif. Acum. | Recorrência | Risk | Saldo Ledger |
|----------|-------|-------|------------|-------------|------|--------------|
{band_line(ranking, 'funcionarioCodigo')}

## Top 20 Piores

| Operador | Score | Banda | Dif. Acum. | Recorrência | Risk | Saldo Ledger |
|----------|-------|-------|------------|-------------|------|--------------|
{band_line(piores, 'funcionarioCodigo')}
""",
        encoding="utf-8",
    )

    (ROOT / "OPERATOR_EVOLUTION_REPORT.md").write_text(
        f"""# OPERATOR EVOLUTION ANALYTICS — F03.4 · Agente 3

## Melhorando (90d vs 7d)

| Operador | Score 7d | Score 90d | Delta |
|----------|----------|-----------|-------|
{chr(10).join(f"| {x.get('funcionarioCodigo')} | {x.get('score7d')} | {x.get('score90d')} | {x.get('delta90vs7')} |" for x in (evo.get('melhorando') or [])[:20]) or "| — | — | — | — |"}

## Piorando

| Operador | Score 7d | Score 90d | Delta |
|----------|----------|-----------|-------|
{chr(10).join(f"| {x.get('funcionarioCodigo')} | {x.get('score7d')} | {x.get('score90d')} | {x.get('delta90vs7')} |" for x in (evo.get('piorando') or [])[:20]) or "| — | — | — | — |"}

## Melhora operacional rede

**{summary.get('melhoraOperacional90d')}** pontos médios (operadores em ascensão)
""",
        encoding="utf-8",
    )

    pdv_rank = pdvs.get("ranking") or []
    (ROOT / "PDV_PERFORMANCE_REPORT.md").write_text(
        f"""# PDV PERFORMANCE INTELLIGENCE — F03.4 · Agente 4

## Ranking PDVs

| PDV | Score | Banda | Dif. Total | Recorrência | Risk |
|-----|-------|-------|------------|-------------|------|
{chr(10).join(f"| {p.get('pdvCodigo')} | {p.get('performanceScore')} | {p.get('performanceBand')} | {brl(p.get('diferencaAcumulada'))} | {p.get('indiceRecorrencia')} | {p.get('cashRiskScore')} |" for p in pdv_rank[:20]) or "| — | — | — | — | — | — |"}

## Destaques obrigatórios

| PDV | Score | Banda | Crítico? |
|-----|-------|-------|----------|
| 54193 | {(crit.get('pdv54193') or {}).get('performanceScore')} | {(crit.get('pdv54193') or {}).get('performanceBand')} | {ex.get('15_pdv54193Critico')} |
| 15880 | {(crit.get('pdv15880') or {}).get('performanceScore')} | {(crit.get('pdv15880') or {}).get('performanceBand')} | {ex.get('16_pdv15880Critico')} |
""",
        encoding="utf-8",
    )

    turn_rank = turns.get("ranking") or []
    (ROOT / "TURN_PERFORMANCE_REPORT.md").write_text(
        f"""# TURN PERFORMANCE INTELLIGENCE — F03.4 · Agente 5

| Turno | Score | Banda | Volume | Dif. | Recorrência | Risco |
|-------|-------|-------|--------|------|-------------|-------|
{chr(10).join(f"| {t.get('turnoCodigo') or t.get('turno')} | {t.get('performanceScore')} | {t.get('performanceBand')} | {brl(t.get('volumeFinanceiro'))} | {brl(t.get('diferencaAcumulada') or t.get('desvioAcumulado'))} | {t.get('incidenciaQuebraPct')} | {t.get('matrizRisco')} |" for t in turn_rank) or "| — | — | — | — | — | — | — |"}
""",
        encoding="utf-8",
    )

    (ROOT / "BEST_PRACTICES_REPORT.md").write_text(
        f"""# BEST PRACTICES DETECTOR — F03.4 · Agente 6

## Padrão vencedor

- Operadores referência: **{(best.get('padraoVencedor') or {}).get('operadoresReferencia')}**
- Score médio top 5: **{(best.get('padraoVencedor') or {}).get('scoreMedioTop5')}**
- Recorrência média top 5: **{(best.get('padraoVencedor') or {}).get('recorrenciaMediaTop5')}**

## PDVs menor risco

{chr(10).join(f"- PDV {p.get('pdvCodigo')}: score {p.get('performanceScore')}" for p in (best.get('pdvsMenorRisco') or [])[:5]) or "—"}

## Turnos melhor resultado

{chr(10).join(f"- Turno {t.get('turnoCodigo') or t.get('turno')}: score {t.get('performanceScore')}" for t in (best.get('turnosMelhorResultado') or [])[:3]) or "—"}

## Insights

{chr(10).join(f"- {i}" for i in (best.get('insights') or []))}
""",
        encoding="utf-8",
    )

    (ROOT / "PERFORMANCE_SNAPSHOT_REPORT.md").write_text(
        f"""# PERFORMANCE SNAPSHOT — F03.4 · Agente 7

## Configuração

| Parâmetro | Valor |
|-----------|-------|
| TTL | 300s |
| Chaves | `operator:performance` · `pdv:performance` · `turn:performance` |
| Estratégia | Snapshot First + Background Refresh |

## SLA medido

| Métrica | Valor | Meta |
|---------|-------|------|
| Snapshot HIT ms | **{snap_ms}** | < 500ms |
| Paridade score médio | **{(w90.get('qa') or {}).get('paridadeScoreMedio')}** | 0,00 |
| Paridade OK | **{(w90.get('qa') or {}).get('paridadeOk')}** | true |
""",
        encoding="utf-8",
    )

    (ROOT / "PERFORMANCE_API_REPORT.md").write_text(
        f"""# PERFORMANCE API — F03.4 · Agente 8

## Rotas

| Método | Rota | Status |
|--------|------|--------|
| GET | `/api/v1/performance/operators` | Implementado |
| GET | `/api/v1/performance/pdvs` | Implementado |
| GET | `/api/v1/performance/turns` | Implementado |
| GET | `/api/v1/performance/summary` | Implementado |
| GET | `/api/v1/performance/snapshot` | Implementado |
| POST | `/api/v1/performance/refresh` | Implementado |

## Contrato

- Query: `dataInicial`, `dataFinal`, `empresaCodigo` (opcional)
- Resposta inclui `snapshot.hit` e `snapshot.stale`
""",
        encoding="utf-8",
    )

    (ROOT / "PERFORMANCE_UI_REPORT.md").write_text(
        f"""# PERFORMANCE UI — F03.4 · Agente 9

## Rota

`view=operator-performance` (alias `operatorPerformance`)

## Cards

| Card | Valor atual |
|------|-------------|
| Melhor operador | {ex.get('1_melhorOperador')} |
| Pior operador | {ex.get('2_piorOperador')} |
| Melhor PDV | {ex.get('7_melhorPdv')} |
| Pior PDV | {ex.get('8_piorPdv')} |
| Melhor turno | {ex.get('9_melhorTurno')} |
| Pior turno | {ex.get('10_piorTurno')} |

## Widgets

- Ranking Operadores · PDVs · Turnos
- Heatmap Operador × PDV
- Heatmap Operador × Turno
- Evolução melhorando/piorando
- Export CSV
""",
        encoding="utf-8",
    )

    (ROOT / "PERFORMANCE_QA_REPORT.md").write_text(
        f"""# PERFORMANCE QA — F03.4 · Agente 10

## Paridade

| Check | Delta | OK |
|-------|-------|-----|
| Score médio | {(w90.get('qa') or {}).get('paridadeScoreMedio')} | {(w90.get('qa') or {}).get('paridadeOk')} |
| Operadores count | {(w90.get('qa') or {}).get('paridadeOperadoresCount')} | |
| Snapshot ms | {snap_ms} | {snap_ok} |

## Casos obrigatórios

| Caso | Score | Banda | Crítico |
|------|-------|-------|---------|
| Operador 276288 | {(crit.get('operador276288') or {}).get('performanceScore')} | {(crit.get('operador276288') or {}).get('performanceBand')} | {ex.get('17_operador276288Critico')} |
| Operador 294273 | {(crit.get('operador294273') or {}).get('performanceScore')} | {(crit.get('operador294273') or {}).get('performanceBand')} | {ex.get('18_operador294273Critico')} |
| PDV 54193 | {(crit.get('pdv54193') or {}).get('performanceScore')} | {(crit.get('pdv54193') or {}).get('performanceBand')} | {ex.get('15_pdv54193Critico')} |
| PDV 15880 | {(crit.get('pdv15880') or {}).get('performanceScore')} | {(crit.get('pdv15880') or {}).get('performanceBand')} | {ex.get('16_pdv15880Critico')} |

## Meta paridade

**0,00** — resultado global: **{paridade_ok}**
""",
        encoding="utf-8",
    )

    (ROOT / "DW_OPERATOR_PERFORMANCE_MODEL.md").write_text(
        f"""# DW OPERATOR PERFORMANCE MODEL — F03.4

## Facts

| Tabela | Granularidade | Medidas |
|--------|---------------|---------|
| `fact_operator_performance` | operador × dia | score, dif_acum, recorrência, risk, saldo_ledger |
| `fact_pdv_performance` | pdv × dia | score, dif_total, recorrência, risk |
| `fact_turn_performance` | turno × dia | score, volume, dif, recorrência, risco |

## Dimensions

| Dimensão | Chaves |
|----------|--------|
| `dim_operator` | funcionario_codigo, banda, filial |
| `dim_pdv` | pdv_codigo, empresa_codigo |
| `dim_turn` | turno_codigo, turno_label |
| `dim_performance_band` | banda, faixa_min, faixa_max |

## Fontes

CAIXA · CAIXA_REDE · Employee Cash Ledger · Cash Operations · Cash Risk Score
""",
        encoding="utf-8",
    )

    op276 = ctx_cases.get("operador276288") or {}
    op294 = ctx_cases.get("operador294273") or {}
    pdv54193 = ctx_cases.get("pdv54193") or {}
    pdv15880 = ctx_cases.get("pdv15880") or {}

    (ROOT / "CONTEXT_ATTRIBUTION_REPORT.md").write_text(
        f"""# CONTEXT VS OPERATOR ATTRIBUTION — F03.4 · Agente 6-B

## Hipótese

```text
Um operador pode parecer excelente ou crítico porque trabalha sempre no mesmo PDV, turno ou filial.
```

## Fórmula

```text
contextAdjustedPerformanceScore = operatorPerformanceScore - contextRiskPenalty + multiContextBonus
```

## Perguntas obrigatórias

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Melhores operadores sempre nos mesmos PDVs? | **{ctx_q.get('1_melhoresMesmosPdvs')}** |
| 2 | Piores operadores sempre nos mesmos PDVs? | **{ctx_q.get('2_pioresMesmosPdvs')}** |
| 3 | Melhores operadores sempre nos mesmos turnos? | **{ctx_q.get('3_melhoresMesmosTurnos')}** |
| 4 | Piores operadores sempre nos mesmos turnos? | **{ctx_q.get('4_pioresMesmosTurnos')}** |
| 5 | Operador bom em PDV ruim? | **{_fmt_list(ctx_q.get('5_operadorBomEmPdvRuim'))}** |
| 6 | Operador ruim em PDV bom? | **{_fmt_list(ctx_q.get('6_operadorRuimEmPdvBom'))}** |
| 7 | PDV prejudica operadores? | **{ctx_q.get('7_pdvPrejudicaOperadores')}** |
| 8 | Turno prejudica operadores? | **{ctx_q.get('8_turnoPrejudicaOperadores')}** |
| 9 | Operador consistente multi-contexto? | **{_fmt_list(ctx_q.get('9_operadorConsistenteMultiContexto'))}** |
| 10 | Operador dependente de contexto? | **{_fmt_list(ctx_q.get('10_operadorDependenteDeContexto'))}** |

## Casos obrigatórios

| Caso | Score bruto | Score ajustado | Classificação | PDV dominante |
|------|-------------|----------------|---------------|---------------|
| Operador 276288 | {op276.get('operatorPerformanceScore')} | {op276.get('contextAdjustedPerformanceScore')} | {op276.get('contextClassification')} | {op276.get('dominantPdv')} ({op276.get('dominantPdvShare')}%) |
| Operador 294273 | {op294.get('operatorPerformanceScore')} | {op294.get('contextAdjustedPerformanceScore')} | {op294.get('contextClassification')} | {op294.get('dominantPdv')} ({op294.get('dominantPdvShare')}%) |
| PDV 54193 | score PDV {pdv54193.get('performanceScore')} | prejudica? **{pdv54193.get('prejudicaOperadores')}** | — | — |
| PDV 15880 | score PDV {pdv15880.get('performanceScore')} | prejudica? **{pdv15880.get('prejudicaOperadores')}** | — | — |

## Ranking ajustado por contexto (top 15)

| Operador | Score bruto | Score ajustado | PDV div. | Turno div. | Classificação |
|----------|-------------|----------------|----------|------------|---------------|
{ctx_line(context.get('operators') or [])}

## Recomendação de ranking

**{ctx_ex.get('26_rankingFinalRecomendado')}** — performance **{ctx_ex.get('21_performanceIndividualOuContexto')}**
""",
        encoding="utf-8",
    )

    (ROOT / "F03_4_OPERATOR_PERFORMANCE_INTELLIGENCE_REPORT.md").write_text(
        f"""# F03.4 — OPERATOR PERFORMANCE INTELLIGENCE

## Respostas executivas

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Melhor operador | **{ex.get('1_melhorOperador')}** |
| 2 | Pior operador | **{ex.get('2_piorOperador')}** |
| 3 | Mais melhorou 90d | **{ex.get('3_maisMelhorou90d')}** |
| 4 | Mais piorou | **{ex.get('4_maisPiorou')}** |
| 5 | Maior saldo devedor | **{ex.get('5_maiorSaldoDevedor')}** |
| 6 | Maior saldo credor | **{ex.get('6_maiorSaldoCredor')}** |
| 7 | Melhor PDV | **{ex.get('7_melhorPdv')}** |
| 8 | Pior PDV | **{ex.get('8_piorPdv')}** |
| 9 | Melhor turno | **{ex.get('9_melhorTurno')}** |
| 10 | Pior turno | **{ex.get('10_piorTurno')}** |
| 11 | Operadores críticos | **{ex.get('11_operadoresCriticos')}** |
| 12 | Operadores excelentes | **{ex.get('12_operadoresExcelentes')}** |
| 13 | Score médio rede | **{ex.get('13_scoreMedioRede')}** |
| 14 | Melhora operacional 90d | **{ex.get('14_melhoraOperacional90d')}** |
| 15 | PDV 54193 crítico? | **{ex.get('15_pdv54193Critico')}** |
| 16 | PDV 15880 crítico? | **{ex.get('16_pdv15880Critico')}** |
| 17 | Operador 276288 crítico? | **{ex.get('17_operador276288Critico')}** |
| 18 | Operador 294273 crítico? | **{ex.get('18_operador294273Critico')}** |
| 19 | Snapshot SLA | **{ex.get('19_snapshotSlaOk')}** ({snap_ms} ms) |
| 20 | Pronto F04? | **{ex.get('20_prontoF04')}** |
| 21 | Performance individual ou contexto? | **{ex.get('21_performanceIndividualOuContexto')}** |
| 22 | Bons em múltiplos PDVs/turnos | **{ex.get('22_operadoresBonsMultiContexto')}** |
| 23 | Só performam em contexto específico | **{ex.get('23_operadoresSóContextoEspecifico')}** |
| 24 | PDVs que prejudicam operadores | **{ex.get('24_pdvsPrejudicamOperadores')}** |
| 25 | Turnos que prejudicam operadores | **{ex.get('25_turnosPrejudicamOperadores')}** |
| 26 | Ranking bruto ou ajustado? | **{ex.get('26_rankingFinalRecomendado')}** |

## Critérios de aceite

| Meta | Resultado |
|------|-----------|
| Paridade 0,00 | {paridade_ok} |
| Snapshot < 500ms | {snap_ok} ({snap_ms} ms) |
| 100% classificados | {qa.get('classificacao100pct')} |

## Entregáveis

- `src/services/operator_performance_service.py`
- `src/services/operator_performance_snapshot_service.py`
- `src/interfaces/http/routes/operator_performance.py`
- `src/services/operator_context_attribution_service.py`
- `frontend/pages/operatorPerformance.js`
- 12 relatórios MD + DW model

{parecer}
""",
        encoding="utf-8",
    )

    print("Relatórios F03.4 gerados.")
    print(parecer)


if __name__ == "__main__":
    main()
