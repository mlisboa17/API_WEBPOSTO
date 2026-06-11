#!/usr/bin/env python3
"""Gera relatórios F04.0 a partir de scripts/f04_0_operator_intelligence.json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f04_0_operator_intelligence.json"


def load() -> dict:
    if not AUDIT.exists():
        raise SystemExit("Execute: python scripts/audit_f04_0_operator_intelligence.py")
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def w(d: dict) -> dict:
    return d.get("windows", {}).get("7d") or next(iter(d.get("windows", {}).values()), {})


def yn(v) -> str:
    if v is True:
        return "**Sim**"
    if v is False:
        return "**Não**"
    return str(v)


def md_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def op_label(entry) -> str:
    if not entry or not isinstance(entry, dict):
        return "—"
    name = entry.get("employeeName")
    code = entry.get("funcionarioCodigo") or entry.get("employeeCode")
    return f"{name or code} ({code})" if name else str(code or "—")


def main() -> None:
    data = load()
    ref = w(data)
    ex = ref.get("executiveAnswers") or data.get("executiveAnswers") or {}
    dim = ref.get("dimEmployee") or {}
    parecer = ref.get("parecerFinal") or data.get("parecerFinal") or ""
    cockpit = ref.get("cockpit") or {}

    (ROOT / "DIM_EMPLOYEE_REPORT.md").write_text(
        f"""# DIM EMPLOYEE — F04.0 · Agente 1

Janela: **{ref.get('window')}** · {ref.get('periodo')}

| Campo | Status |
|-------|--------|
| employeeId / employeeCode | `funcionarioCodigo` |
| employeeName | `/INTEGRACAO/FUNCIONARIO.nome` |
| employeeCpf | `FUNCIONARIO.cpf` |
| employeeReference | `funcionarioReferencia` |
| employeeStatus | `ativo` → ATIVO/INATIVO |
| empresaCodigo | `FUNCIONARIO.empresaCodigo` |

## Métricas

| Métrica | Valor |
|---------|-------|
| Total cadastro | {dim.get('total', '—')} |
| Ativos | {dim.get('ativos', '—')} |
| Nominalização | {dim.get('nominalizacaoPct', '—')}% |

Serviço: `EmployeeDimensionService` · endpoint registrado: `funcionario`
""",
        encoding="utf-8",
    )

    (ROOT / "OPERATOR_SALES_PERFORMANCE_REPORT.md").write_text(
        f"""# OPERATOR SALES PERFORMANCE — F04.0 · Agente 2

Operadores com vendas: **{ref.get('salesOperators', 0)}**

| # | Pergunta | Resposta |
|---|----------|----------|
| 2 | Quem mais vende? | {op_label(ex.get('2_quemMaisVende'))} |
| 6 | Maior ticket médio? | {op_label(ex.get('6_maiorTicketMedio'))} |

Métricas: totalVendas, quantidadeVendas, ticketMedio, volumeCombustivel, volumeConveniência.
""",
        encoding="utf-8",
    )

    bands = ref.get("productivityBands") or {}
    (ROOT / "PRODUCTIVITY_ENGINE_REPORT.md").write_text(
        f"""# PRODUCTIVITY ENGINE — F04.0 · Agente 3

Fórmula: vendas + abastecimentos + itens + volume financeiro (normalizado).

## Bandas

{md_table(["Banda", "Qtd"], [[k, v] for k, v in bands.items()]) if bands else '—'}

| # | Pergunta | Resposta |
|---|----------|----------|
| 7 | Melhor produtividade | {op_label(ex.get('7_melhorProdutividade'))} |
| 15 | Operador ELITE | {op_label(ex.get('15_operadorElite'))} |
| 16 | Operador CRÍTICO | {op_label(ex.get('16_operadorCritico'))} |
""",
        encoding="utf-8",
    )

    (ROOT / "DISCOUNT_INTELLIGENCE_REPORT.md").write_text(
        f"""# DISCOUNT INTELLIGENCE — F04.0 · Agente 4

Total descontos: **R$ {ref.get('discountTotal', 0)}**

**Quem mais concede desconto?** {op_label(ex.get('5_quemMaisDescontos'))}

Mapeamento: `VENDA_ITEM.totalDesconto` por operador e PDV.
""",
        encoding="utf-8",
    )

    (ROOT / "PAYMENT_MIX_REPORT.md").write_text(
        f"""# PAYMENT MIX — F04.0 · Agente 5

Cruzamento: VENDA_FORMA_PAGAMENTO → VENDA.funcionarioCodigo → FUNCIONARIO.nome

Buckets: DINHEIRO, PIX, DÉBITO, CRÉDITO, CONVÊNIO, OUTROS (via `nomeFormaPagamento`).
""",
        encoding="utf-8",
    )

    (ROOT / "FUEL_PERFORMANCE_REPORT.md").write_text(
        f"""# FUEL PERFORMANCE — F04.0 · Agente 6

| # | Pergunta | Resposta |
|---|----------|----------|
| 3 | Quem vende combustível? | {op_label(ex.get('3_quemVendeCombustivel'))} |
| 4 | Quem vende conveniência? | {op_label(ex.get('4_quemVendeConveniencia'))} |

Fonte: ABASTECIMENTO.codigoFrentista + VENDA_ITEM (bico/tanque/LMC).
""",
        encoding="utf-8",
    )

    (ROOT / "CASH_ACCOUNTABILITY_REPORT.md").write_text(
        f"""# CASH ACCOUNTABILITY — F04.0 · Agente 7

Integração F03.3 Employee Cash Ledger.

| # | Pergunta | Resposta |
|---|----------|----------|
| 9 | Maior saldo devedor | {op_label(ex.get('9_maiorSaldoDevedor'))} |
| 10 | Maior saldo credor | {op_label(ex.get('10_maiorSaldoCredor'))} |
| 11 | Mais faltas | {op_label(ex.get('11_maisFaltas'))} |
| 12 | Mais sobras | {op_label(ex.get('12_maisSobras'))} |
""",
        encoding="utf-8",
    )

    (ROOT / "OPERATOR_RISK_ENGINE_REPORT.md").write_text(
        f"""# OPERATOR RISK ENGINE — F04.0 · Agente 8

Pesos: 40% quebras · 20% descontos · 20% recorrência · 20% contexto

Operadores críticos (risco): **{ref.get('riskCriticos', 0)}**

| # | Pergunta | Resposta |
|---|----------|----------|
| 8 | Maior risco | {op_label(ex.get('8_maiorRiscoOperacional'))} |
| 17 | Em risco | {ex.get('17_operadoresEmRisco', '—')} |
| 18 | R$ operadores críticos | {ex.get('18_dinheiroOperadoresCriticos', '—')} |
""",
        encoding="utf-8",
    )

    top_ops = cockpit.get("topOperadores") or []
    crit_ops = cockpit.get("operadoresCriticos") or []
    (ROOT / "OPERATOR_COCKPIT_REPORT.md").write_text(
        f"""# OPERATOR COCKPIT — F04.0 · Agente 9

Rota UI: `view=operator-performance`

## Widgets

| Widget | Fonte |
|--------|-------|
| Top Operadores | productivityEngine.top 10 |
| Operadores Críticos | operatorRiskEngine (band Critico) |
| Vendas | salesPerformance |
| Descontos | discountIntelligence |
| Risco | operatorRiskEngine |
| Accountability | cashAccountability |

API: `GET /api/v1/operator-intelligence/cockpit`

Top operadores (amostra):

{md_table(["Operador", "Score", "Banda"], [[o.get('employeeName') or o.get('funcionarioCodigo'), o.get('productivityScore'), o.get('productivityBand')] for o in top_ops[:5]]) if top_ops else '—'}
""",
        encoding="utf-8",
    )

    (ROOT / "DW_OPERATOR_INTELLIGENCE_MODEL.md").write_text(
        f"""# DW OPERATOR INTELLIGENCE MODEL — F04.0 · Agente 10

## Dimensions

| Tabela | Arquivo | Chave |
|--------|---------|-------|
| dim_employee | `dw/ddl/dim_employee.sql` | funcionario_codigo |
| dim_pdv | `dw/ddl/dim_pdv.sql` | pdv_codigo |
| dim_turn | `dw/ddl/dim_turn.sql` | turno_codigo |
| dim_date | `dw/ddl/dim_cash_date.sql` | date_sk |

## Facts

| Tabela | Arquivo |
|--------|---------|
| fact_operator_sales | `dw/ddl/fact_operator_sales.sql` |
| fact_operator_discount | `dw/ddl/fact_operator_discount.sql` |
| fact_operator_productivity | `dw/ddl/fact_operator_productivity.sql` |
| fact_operator_risk | `dw/ddl/fact_operator_risk.sql` |
| fact_operator_accountability | `dw/ddl/fact_operator_accountability.sql` |

Paridade auditada: **{ref.get('paridadeDelta', '—')}** · OK: {yn(ref.get('paridadeOk'))}
""",
        encoding="utf-8",
    )

    exec_rows = [
        ["1", "Operadores ativos", ex.get("1_operadoresAtivos")],
        ["2", "Quem mais vende", op_label(ex.get("2_quemMaisVende"))],
        ["3", "Combustível", op_label(ex.get("3_quemVendeCombustivel"))],
        ["4", "Conveniência", op_label(ex.get("4_quemVendeConveniencia"))],
        ["5", "Mais descontos", op_label(ex.get("5_quemMaisDescontos"))],
        ["6", "Maior ticket", op_label(ex.get("6_maiorTicketMedio"))],
        ["7", "Melhor produtividade", op_label(ex.get("7_melhorProdutividade"))],
        ["8", "Maior risco", op_label(ex.get("8_maiorRiscoOperacional"))],
        ["9", "Maior devedor", op_label(ex.get("9_maiorSaldoDevedor"))],
        ["10", "Maior credor", op_label(ex.get("10_maiorSaldoCredor"))],
        ["11", "Mais faltas", op_label(ex.get("11_maisFaltas"))],
        ["12", "Mais sobras", op_label(ex.get("12_maisSobras"))],
        ["13", "Bom em PDV crítico", str(ex.get("13_bomEmPdvCritico"))[:120]],
        ["14", "Dependente contexto", str(ex.get("14_dependenteContexto"))[:120]],
        ["15", "ELITE", op_label(ex.get("15_operadorElite"))],
        ["16", "CRÍTICO", op_label(ex.get("16_operadorCritico"))],
        ["17", "Em risco", ex.get("17_operadoresEmRisco")],
        ["18", "R$ críticos", ex.get("18_dinheiroOperadoresCriticos")],
        ["19", "Pronto gestão pessoas", yn(ex.get("19_prontoGestaoPessoas"))],
        ["20", "Aprovado F04.1", yn(ex.get("20_aprovadoF041"))],
    ]

    (ROOT / "F04_0_OPERATOR_PERFORMANCE_INTELLIGENCE_REPORT.md").write_text(
        f"""# F04.0 — OPERATOR PERFORMANCE & SALES INTELLIGENCE REPORT

Baseline: F01–F03.4 · D01 · D02 (`FUNCIONARIO` nominal)

## Respostas executivas (20)

{md_table(["#", "Pergunta", "Resposta"], exec_rows)}

## Critérios de aceite

| Critério | Status |
|----------|--------|
| dim_employee | {yn((data.get('acceptance') or {}).get('dimEmployee'))} |
| nominalização completa | {yn((data.get('acceptance') or {}).get('nominalizacao'))} |
| paridade 0,00 | {yn((data.get('acceptance') or {}).get('paridadeZero'))} (Δ={ex.get('paridadeDelta', '—')}) |

## Entregáveis

- DIM_EMPLOYEE_REPORT.md
- OPERATOR_SALES_PERFORMANCE_REPORT.md
- PRODUCTIVITY_ENGINE_REPORT.md
- DISCOUNT_INTELLIGENCE_REPORT.md
- PAYMENT_MIX_REPORT.md
- FUEL_PERFORMANCE_REPORT.md
- CASH_ACCOUNTABILITY_REPORT.md
- OPERATOR_RISK_ENGINE_REPORT.md
- OPERATOR_COCKPIT_REPORT.md
- DW_OPERATOR_INTELLIGENCE_MODEL.md

{parecer}
""",
        encoding="utf-8",
    )

    print("Relatórios F04.0 gerados (11 arquivos + consolidado)")


if __name__ == "__main__":
    main()
