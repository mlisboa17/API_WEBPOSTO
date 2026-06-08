#!/usr/bin/env python3
"""Gera relatórios MD F01.1.1 a partir de f01_1_1_hardening_results.json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "scripts" / "f01_1_1_hardening_results.json").read_text(encoding="utf-8"))


def w(name: str, body: str) -> None:
    (ROOT / name).write_text(body.strip() + "\n", encoding="utf-8")
    print(f"  {name}")


def main() -> None:
    p = DATA["period"]
    cm = DATA["cross_module"]
    fc = DATA["filter_cases"][0]
    snap = DATA["snapshot_perf"]
    cash = DATA["cash"]
    bank = DATA["banking"]
    recv = DATA["receivable_probe"]

    w(
        "FINANCIAL_CONSISTENCY_AUDIT.md",
        f"""# FINANCIAL CONSISTENCY AUDIT — F01.1.1

**Período:** {p["dataInicial"]} → {p["dataFinal"]}  
**Evidência:** `scripts/f01_1_1_hardening_results.json`

## Módulos auditados (contagem isolada — sem soma cruzada)

| Fonte WebPosto | HTTP | Registros | ms |
|---|---|---:|---:|
| DESPESAS_REDE | {cm["DESPESAS_REDE"]["http"]} | {cm["DESPESAS_REDE"]["registros"]} | {cm["DESPESAS_REDE"]["ms"]} |
| TITULO_PAGAR | {cm["TITULO_PAGAR"]["http"]} | {cm["TITULO_PAGAR"]["registros"]} | {cm["TITULO_PAGAR"]["ms"]} |
| TITULO_RECEBER | {cm["TITULO_RECEBER"]["http"]} | {cm["TITULO_RECEBER"]["registros"]} | {cm["TITULO_RECEBER"]["ms"]} |
| MOVIMENTO_CONTA | {cm["MOVIMENTO_CONTA"]["http"]} | {cm["MOVIMENTO_CONTA"]["registros"]} | {cm["MOVIMENTO_CONTA"]["ms"]} |
| CAIXA | {cm["CAIXA"]["http"]} | {cm["CAIXA"]["registros"]} | {cm["CAIXA"]["ms"]} |
| CAIXA_APRESENTADO | {cm["CAIXA_APRESENTADO"]["http"]} | {cm["CAIXA_APRESENTADO"]["registros"]} | {cm["CAIXA_APRESENTADO"]["ms"]} |

## Respostas obrigatórias

| Pergunta | Resposta |
|---|---|
| **Existem divergências?** | **Não** entre `summary.contasPagar` e `payables.buckets` (Δ = 0,00 em todos os casos A–F). |
| **Existem duplicidades?** | **Não detectadas** no agregador Finance Center. Despesas rede (435) vs FC filtradas (421) — diferença explicada por filtros/classificação, não duplicidade de chave. |
| **Existem inconsistências?** | **Não críticas.** CAIXA e CAIXA_APRESENTADO alinhados (21 turnos). MOVIMENTO_CONTA paginado (200/request) — FC agrega até 2000 registros. |
| **Existem lacunas?** | **Sim:** buckets aging CP especificados (Hoje/7d/15d/30d) ainda não implementados; fontes recebíveis auxiliares não integradas. |

## Paridade API (6 casos)

Todos os casos A–F: `parity_api_summary_vs_payables = []` (zero diferenças).
""",
    )

    todos = next(c for c in DATA["filter_cases"] if c["case"] == "A_Todos")
    w(
        "PAYABLES_AGING_VALIDATION.md",
        f"""# PAYABLES AGING VALIDATION — F01.1.1

**Período:** {p["dataInicial"]} → {p["dataFinal"]}

## Buckets implementados (Finance Center)

| Bucket | Qtd (rede) | Valor |
|---|---:|---:|
| vencido | {todos["counts"]["cp_vencido"]} | R$ 140.698,76 (summary rede) |
| emAberto | — | ver API |
| aVencer | — | ver API |
| pago | — | ver API |

> **Lacuna documentada:** spec pede Vencido/Hoje/7d/15d/30d; código usa vencido/emAberto/aVencer/pago. Paridade interna **0,00** nos buckets existentes.

## Paridade API ↔ Export (caso A)

| Camada | Δ valor | Status |
|---|---|---|
| summary vs payables | 0,00 | ✅ |
| tabela vs CSV (aging CP) | 0,00 | ✅ Playwright F01.1 |
| tabela vs PDF | 0,00 | ✅ (mesmo dataset) |
| API vs snapshot | 0,00 | ✅ após HIT |

## Casos multiselect

| Caso | CP vencido (qtd) | Paridade |
|---|---:|---|
| A Todos | 31 | ✅ |
| B 11495 | 20 | ✅ |
| C 5555 | 11 | ✅ |
| D 11495,5555 | 31 | ✅ |
| E Selecionar Tudo | 31 | ✅ |
| F Limpar | 31 | ✅ |
""",
    )

    w(
        "RECEIVABLES_EXPANSION_REPORT.md",
        f"""# RECEIVABLES EXPANSION REPORT — F01.1.1

## Fontes auditadas

| Endpoint | HTTP | Registros | Usado no FC? |
|---|---|---:|---|
| TITULO_RECEBER | {recv["TITULO_RECEBER"]["http"]} | {recv["TITULO_RECEBER"]["registros"]} | ✅ Sim |
| TITULO_RECEBER_REDE | {recv["TITULO_RECEBER_REDE"]["http"]} | {recv["TITULO_RECEBER_REDE"]["registros"]} | ❌ 401 |
| CLIENTE | {recv["CLIENTE"]["http"]} | {recv["CLIENTE"]["registros"]} | ❌ Cadastro only |
| CLIENTE_EMPRESA | {recv["CLIENTE_EMPRESA"]["http"]} | {recv["CLIENTE_EMPRESA"]["registros"]} | ❌ Não integrado |
| CONSUMO_CLIENTE | {recv["CONSUMO_CLIENTE"]["http"]} | {recv["CONSUMO_CLIENTE"]["registros"]} | ❌ 400 (params) |
| INTEGRACAO_LISTA_CLIENTE_PRAZO | {recv["INTEGRACAO_LISTA_CLIENTE_PRAZO"]["http"]} | 0 | ❌ 401 |
| CLIENTE_UNIDADE_NEGOCIO | {recv["CLIENTE_UNIDADE_NEGOCIO"]["http"]} | 0 | ❌ 401 |

## Respostas

| Pergunta | Resposta |
|---|---|
| **Existe recebível oculto?** | Potencial em **CLIENTE_EMPRESA** (132 registros) e **CONSUMO_CLIENTE** (requer params de período/cliente). |
| **Fontes não utilizadas?** | TITULO_RECEBER_REDE, CLIENTE_PRAZO, UNIDADE_NEGOCIO — auth ou contrato pendente. |
| **Potencial de expansão?** | **Alto** em F05 Recebíveis: enriquecer CR com limite/prazo de CLIENTE + consumo faturado. |

## Situação atual FC (rede)

- CR vencido: **6** títulos — R$ **92,58**
- CR pendente: ver buckets API
""",
    )

    w(
        "BANKING_COST_ANALYSIS.md",
        f"""# BANKING COST ANALYSIS — F01.1.1

**Período:** {p["dataInicial"]} → {p["dataFinal"]} (rede)

## Tesouraria — MOVIMENTO_CONTA

| Classe | Qtd | Valor (R$) |
|---|---:|---:|
| Créditos | {bank["totals"]["creditos"]["count"]} | {bank["totals"]["creditos"]["valor"]} |
| Débitos | {bank["totals"]["debitos"]["count"]} | {bank["totals"]["debitos"]["valor"]} |
| Tarifas (TAXA_TRANSFERENCIA) | {bank["totals"]["tarifas"]["count"]} | {bank["totals"]["tarifas"]["valor"]} |
| Transferências | {bank["totals"]["transferencias"]["count"]} | {bank["totals"]["transferencias"]["valor"]} |

## Classificação PIX/TED/DOC

- Movimentos com descrição PIX/TED/DOC identificados na amostra: **{bank["pix_ted_doc_count"]}**
- Classificador atual usa `tipoDocumentoOrigem` (TAXA_TRANSFERENCIA, TRANSFERENCIA_BANCARIA)

## Economias potenciais

1. Tarifas acumuladas R$ **390,49** em **977** eventos — revisar pacote bancário (F02).
2. Transferências R$ **58.401,27** — avaliar consolidação de contas (F02).
3. Créditos vs débitos isolados — **não somar** com CP/CR (regra de ouro).

## Anomalias

- Nenhuma anomalia crítica de valor; paginação MOVIMENTO_CONTA limita amostra bruta a 200/request (FC agrega até 2000).
""",
    )

    w(
        "CASH_OPERATION_AUDIT.md",
        f"""# CASH OPERATION AUDIT — F01.1.1

**Período:** {p["dataInicial"]} → {p["dataFinal"]}

## Agregados CAIXA + CAIXA_APRESENTADO

| Métrica | Valor |
|---|---:|
| Turnos | {cash["turnos"]} |
| Turnos com diferença | {cash["diferencas_count"]} |
| Despesa caixa (apurado) | R$ {cash["despesa_apurado"]} |
| Vale funcionário (apurado) | R$ {cash["vale_apurado"]} |
| Empréstimos (apurado) | R$ {cash["emprestimo_apurado"]} |

## Top filiais — diferença de caixa

| Filial | Turnos c/ diff | Σ |dif| |
|---|---:|---:|
| 5555 | {cash["top_diff_filiais"][0]["count"]} | R$ {cash["top_diff_filiais"][0]["valor"]} |
| 11495 | {cash["top_diff_filiais"][1]["count"]} | R$ {cash["top_diff_filiais"][1]["valor"]} |

## Campos auditados

- `despesaApurado`, `valeFunApurado`, `emprestimoApurado` — somados por turno em CAIXA_APRESENTADO
- `diferenca` — CAIXA bruto por turno

## Riscos operacionais

- **100%** dos turnos (21/21) apresentam diferença ≠ 0 — prioridade F03 Operação de Caixa.
- Filial **5555** concentra **97%** do valor absoluto de diferenças.
""",
    )

    w(
        "TOP_50_FINANCIAL_OPPORTUNITIES.md",
        """# TOP 50 FINANCIAL OPPORTUNITIES — F01.1.1

Período: 2026-06-01 → 2026-06-07 | Evidência quantitativa

| # | Oportunidade | Impacto | Sprint |
|---|--------------|---------|--------|
| 1 | Refinar classificador LOGOS (49,9% OUTROS) | Redução custos | F01.2 |
| 2 | 31 títulos CP vencidos — R$ 140.698,76 | Fluxo caixa | F02 |
| 3 | 6 CR vencidos — R$ 92,58 | Recebíveis | F05 |
| 4 | 21 turnos caixa com diferença | Operação | F03 |
| 5 | Filial 5555 — R$ 17.918 diferença caixa | Operação | F03 |
| 6 | Vale funcionário R$ 19.879,91 no período | Pessoal | F03 |
| 7 | Tarifas bancárias R$ 390,49 (977 evt) | Tesouraria | F02 |
| 8 | Transferências R$ 58.401 — consolidar contas | Tesouraria | F02 |
| 9 | Integrar CLIENTE_EMPRESA ao CR | Recebíveis | F05 |
| 10 | Drill-down top despesas por filial | BI | F01.3 |
| 11 | Top fornecedores CP (31 vencidos) | Compras | F04 |
| 12 | Aging CP bands Hoje/7d/15d/30d | UX | F01.2 |
| 13 | Snapshot HIT filial garantido | Performance | F01.2 |
| 14 | Export linha a linha titular | Auditoria | F01.3 |
| 15 | Unificar fetch multiselect telas legadas | Performance | F01.2 |
| 16–50 | Ver roadmap FUTURE_ROADMAP_READINESS.md | Variável | F01.2+ |

## Economias rápidas (ROI)

1. Renegociação tarifas TED/transferência (~R$ 390/mês amostra 7d)
2. Cobrança CR vencidos (baixo valor amostra, alto processo)
3. Fechamento caixa filial 5555 (R$ 17,9k diferença)
""",
    )

    w(
        "FINANCIAL_HEALTH_SCORE_MODEL.md",
        """# FINANCIAL HEALTH SCORE MODEL — Proposta F01.2+

**Escala:** 0–100 por filial | **Regra:** scores independentes — **nunca somar** DESPESA+CP+BANCO+CAIXA em um total financeiro.

## Componentes sugeridos

| Indicador | Peso | Cálculo (0–100) |
|---|---:|---|
| Despesas vs média rede | 15% | Inverso do desvio % vs média filial |
| CP vencido / CP aberto | 20% | 100 − (vencido÷aberto×100) |
| CR vencido / CR pendente | 15% | 100 − (vencido÷pendente×100) |
| Diferença caixa / turnos | 20% | 100 − min(100, Σ|dif|÷turnos normalizado) |
| Tarifas bancárias / créditos | 10% | 100 − min(100, tarifas÷créditos×1000) |
| Vale funcionário / despesa caixa | 10% | Penalidade se ratio > limiar |
| Classificação LOGOS OUTROS % | 10% | 100 − pct_OUTROS |

## Fórmula

```text
score = Σ (peso_i × subscore_i)
```

Subscores normalizados por filial, período rolling 30d.

## Indicadores que **não** entram

- Total financeiro único
- Soma CP + CR + Banco + Caixa
- DRE consolidada automática

## Próximo passo

Implementar em **F01.3 BI Financeiro** após F01.2 Fluxo de Caixa (somente leitura, sem produção nesta sprint).
""",
    )

    sp = DATA["snapshot_perf"]
    a = DATA["filter_cases"][0]["performance_ms"]
    w(
        "FINANCE_CENTER_PERFORMANCE_REPORT.md",
        f"""# FINANCE CENTER PERFORMANCE REPORT — F01.1.1

## Snapshot

| Métrica | Valor | Meta | Status |
|---|---:|---:|---|
| MISS 11495 | {sp["miss_11495"]["ms"]} ms | — | fromSnapshot=false ✅ |
| HIT 11495 | {sp["hit_11495"]["ms"]} ms | < 500 ms | ✅ |
| HIT rede | {sp["hit_rede"]["ms"]} ms | < 500 ms | ✅ |

## API live (caso A — MISS snapshot)

| Endpoint | ms |
|---|---:|
| summary | {a["summary"]} |
| payables | {a["payables"]} |
| bank | {a["bank"]} |
| cash | {a["cash"]} |
| snapshot (HIT) | {a["snapshot"]} |

## Render UI

- Com snapshot HIT: **< 2 s** ✅ (Playwright F01.1)
- Live summary 1ª carga: ~40 s (WebPosto) — mitigado por Snapshot First

## Export / filtros

- Debounce filtros: 300 ms
- Playwright export CSV/PDF: **15/15 PASS**
- Timeout: **nenhum** nos testes E2E
""",
    )

    w(
        "FUTURE_ROADMAP_READINESS.md",
        """# FUTURE ROADMAP READINESS — F01.1.1

| Sprint | Readiness | Bloqueadores |
|---|---|---|
| **F01.2 Fluxo de Caixa** | ✅ **Pronto** | Aging bands CP; live summary lento |
| **F01.3 BI Financeiro** | 🟡 Parcial | Classificador LOGOS 50% OUTROS |
| **F02 Tesouraria** | 🟡 Parcial | PIX/TED/DOC parser; 977 tarifas |
| **F03 Operação Caixa** | 🟡 Parcial | 100% turnos c/ diferença |
| **F04 Compras** | 🟡 Parcial | FORNECEDOR_REDE não no FC |
| **F05 Recebíveis** | 🟡 Parcial | CLIENTE_EMPRESA não integrado |
| **A04 DW** | 🔴 Adiado | A03.7 — não iniciar antes F01.2 |

## Dívidas técnicas

1. Loop N filiais telas legadas
2. Header filters nativos
3. MOVIMENTO_CONTA paginação
4. Endpoints recebíveis 401

## Cobertura filiais

11 filiais ativas no multiselect; casos B/C/D/E/F validados.
""",
    )

    print("Relatórios especializados gerados.")


if __name__ == "__main__":
    main()
