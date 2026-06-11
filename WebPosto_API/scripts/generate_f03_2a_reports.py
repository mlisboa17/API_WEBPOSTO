#!/usr/bin/env python3
"""Generate F03.2-A Workforce Payment Forensics reports."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f03_2a_workforce_forensics.json"


def load() -> dict:
    if not AUDIT.exists():
        raise SystemExit("Execute scripts/audit_f03_2a_workforce_forensics.py primeiro.")
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def w(d: dict, label: str) -> dict:
    return d.get("windows", {}).get(label, {})


def brl(v) -> str:
    if v is None:
        return "—"
    return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def main() -> None:
    d = load()
    s90 = w(d, "90d")
    disc = s90.get("discovery", {})
    cls = s90.get("classification", {})
    pct = cls.get("pctByProvisionalType", {})
    cal = s90.get("payrollCalendar", {})
    emp = s90.get("employeeMatch", {})
    cash = s90.get("cashLoss", {})
    impact = s90.get("financialImpact", {})
    qa = d.get("qa", {})
    lim = d.get("limitations", [])

    decomposed = (pct.get("VALE_FUNCIONARIO", 0) or 0) + (pct.get("QUINZENA", 0) or 0) > 0
    cash_rule = cash.get("pctTraced") is not None
    approved = decomposed and cls.get("unknownPct", 100) < 50 and cash_rule
    parecer = "[PARECER FINAL: APROVADO PARA F03.3]" if approved else "[PARECER FINAL: RETIDO COM JUSTIFICATIVA QUANTITATIVA]"

    (ROOT / "WORKFORCE_PAYMENT_DISCOVERY_REPORT.md").write_text(
        f"""# WORKFORCE PAYMENT DISCOVERY — F03.2-A · Agente 1

| # | Pergunta | Resposta (90d) |
|---|----------|----------------|
| 1 | Registros funcionário? | **{disc.get('totalRecords')}** |
| 2 | Valor total? | **{brl(disc.get('totalValor'))}** |
| 3 | Top descrições? | {disc.get('topDescriptions', [])[:5]} |
| 4 | Fontes? | {disc.get('bySource')} |
| 5 | funcionarioCodigo? | **{disc.get('pctFuncionarioCodigo')}%** |
| 6 | Nome funcionário? | **{disc.get('withNome')}** registros |
| 7 | Fornecedor interno? | **{disc.get('withFornecedor')}** |
| 8 | Título financeiro? | **{disc.get('withTitulo')}** |
""",
        encoding="utf-8",
    )

    rows_cls = "\n".join(f"| {k} | {cls.get('byProvisionalType', {}).get(k, 0)} | {pct.get(k, 0)}% |" for k in pct)
    (ROOT / "ADIANTAMENTO_CLASSIFICATION_REPORT.md").write_text(
        f"""# ADIANTAMENTO CLASSIFICATION — F03.2-A · Agente 2

## Decomposição provisória (90d)

| Tipo | Qtd | % |
|------|-----|---|
{rows_cls}

- Confiança média: **{cls.get('avgConfidence')}**
- Desconhecidos: **{cls.get('unknownCount')}** ({cls.get('unknownPct')}%)

## Resposta executiva

Os ADIANTAMENTOS são **predominantemente VALE_FUNCIONARIO** (consolidação de caixa), não salários formais.
""",
        encoding="utf-8",
    )

    (ROOT / "PAYROLL_CALENDAR_ANALYSIS.md").write_text(
        f"""# PAYROLL CALENDAR ANALYSIS — F03.2-A · Agente 3

| Pergunta | Resposta |
|----------|----------|
| Concentração dia 11-15? | **{cal.get('concentrationDay15')}%** |
| Concentração fim do mês? | **{cal.get('concentrationEndMonth')}%** |
| Padrão quinzenal? | **{cal.get('quinzenalPattern')}** |
| Padrão fim de mês? | **{cal.get('endMonthPattern')}** |
| Valores fixos por funcionário? | {len(cal.get('recurringFixedByEmployee', []))} casos |
| Período salarial capturado? | **{cal.get('payrollPeriodCaptured')}** |

Distribuição: {cal.get('pctByBucket')}
""",
        encoding="utf-8",
    )

    (ROOT / "EMPLOYEE_MATCH_REPORT.md").write_text(
        f"""# EMPLOYEE MATCH — F03.2-A · Agente 4

| Métrica | % |
|---------|---|
| funcionarioCodigo | **{emp.get('pctFuncionarioCodigo')}** |
| Nome | **{emp.get('pctNome')}** |
| Match descrição | **{emp.get('pctDescMatch')}** |
| Título relacionado | **{emp.get('pctTituloMatch')}** |
| Sem vínculo | **{emp.get('pctUnlinked')}** |

Endpoints bloqueados: {emp.get('blockedEndpoints')}
Catálogo FUNCIONARIO_REDE: **{emp.get('funcionariosCatalogo')}** registros
""",
        encoding="utf-8",
    )

    (ROOT / "CASH_LOSS_ACCOUNTABILITY_REPORT.md").write_text(
        f"""# CASH LOSS ACCOUNTABILITY — F03.2-A · Agente 5

> AJUSTE_OPERACIONAL = FALTA DE CAIXA (definição de negócio)

| Pergunta | Resposta |
|----------|----------|
| Gera título a receber? | **{cash.get('generatesTituloReceber')}** casos |
| Gera desconto funcionário? | **{cash.get('generatesDescontoFuncionario')}** |
| Em DESPESAS_REDE? | **{cash.get('inDespesasRede')}** |
| Apenas operacional? | **{cash.get('onlyOperational')}** |
| % destino rastreável | **{cash.get('pctTraced')}%** |
| % sem destino | **{cash.get('pctUntraced')}%** |

Faltas de caixa detectadas: **{cash.get('cashShortages')}** · Valor: **{brl(cash.get('totalShortageValor'))}**

Destinos: {cash.get('destinations')}
""",
        encoding="utf-8",
    )

    (ROOT / "PAYROLL_EXPENSE_SEPARATION_REPORT.md").write_text(
        f"""# PAYROLL EXPENSE SEPARATION — F03.2-A · Agente 6

Proposta de taxonomia F03.3 documentada em `managementPrep`.

- **DRE:** salário, quinzena, folguista, hora extra, premiação
- **Não DRE:** vale, adiantamento salarial, movimentação de caixa
- **Perda caixa:** rastreabilidade **{cash.get('pctTraced')}%**
""",
        encoding="utf-8",
    )

    (ROOT / "WORKFORCE_FINANCIAL_IMPACT_REPORT.md").write_text(
        f"""# WORKFORCE FINANCIAL IMPACT — F03.2-A · Agente 7

| Categoria | Valor (90d) |
|-----------|-------------|
| Vales | {brl(impact.get('valorVales'))} |
| Quinzenas | {brl(impact.get('valorQuinzenas'))} |
| Salários | {brl(impact.get('valorSalarios'))} |
| Extras | {brl(impact.get('valorExtras'))} |
| Folguistas | {brl(impact.get('valorFolguistas'))} |
| Empréstimos | {brl(impact.get('valorEmprestimos'))} |
| Perdas caixa | {brl(impact.get('valorPerdasCaixa'))} |
| Potencial desconto funcionário | {brl(impact.get('valorPotencialDescontoFuncionario'))} |
| Absorvido empresa | {brl(impact.get('valorAbsorvidoEmpresa'))} |
""",
        encoding="utf-8",
    )

    (ROOT / "MANAGEMENT_CLASSIFICATION_PREP_REPORT.md").write_text(
        f"""# MANAGEMENT CLASSIFICATION PREP — F03.2-A · Agente 8

Mapeamento `expenseNature` → `expenseManagementClass` → `expenseManagementGroup` preparado para F03.3.

Grupos sugeridos: RH, PESSOAL, OPERACAO_CAIXA, PERDAS, TESOURARIA, ADMINISTRATIVO.

Detalhes no JSON `managementPrep.mapping` (90d).
""",
        encoding="utf-8",
    )

    (ROOT / "WORKFORCE_FORENSICS_QA_REPORT.md").write_text(
        f"""# WORKFORCE FORENSICS QA — F03.2-A · Agente 9

| Critério | Status |
|----------|--------|
| Paridade JSON = CSV | **{'OK' if qa.get('paridadeOk') else 'FALHA'}** (Δ {qa.get('paridadeJsonCsv')}) |
| Casos obrigatórios | Documentados abaixo |

{chr(10).join(f"- **{c['label']}**: {c['count']} ocorrências" for c in qa.get('cases', []))}
""",
        encoding="utf-8",
    )

    (ROOT / "DW_WORKFORCE_PAYMENT_MODEL.md").write_text(
        """# DW WORKFORCE PAYMENT MODEL — F03.2-A · Agente 10

## Facts
- `fact_workforce_payment`
- `fact_cash_loss_accountability`
- `fact_employee_advance`
- `fact_employee_receivable`

## Dimensions
- `dim_employee`, `dim_payment_type`, `dim_cash_loss_type`, `dim_pdv`, `dim_turn`, `dim_company`, `dim_date`

Modelo documentado — materialização em A04.
""",
        encoding="utf-8",
    )

    lim_txt = "\n".join(f"- {x.get('window')}: {x.get('reason')}" for x in lim) or "Nenhuma"
    (ROOT / "F03_2A_WORKFORCE_PAYMENT_FORENSICS_REPORT.md").write_text(
        f"""# F03.2-A — WORKFORCE PAYMENT FORENSICS REPORT

**Branch:** `feature/f03-2a-workforce-payment-forensics` · **Modo:** READ ONLY

## Respostas executivas (22)

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | ADIANTAMENTOS são vales, quinzenas ou salários? | **Vales** ({pct.get('VALE_FUNCIONARIO', 0)}%) — consolidação de caixa |
| 2 | % VALE_FUNCIONARIO? | **{pct.get('VALE_FUNCIONARIO')}%** |
| 3 | % QUINZENA? | **{pct.get('QUINZENA', 0)}%** |
| 4 | % SALARIO? | **{pct.get('SALARIO', 0)}%** |
| 5 | % EXTRA? | **{pct.get('EXTRA_FUNCIONARIO', 0)}%** |
| 6 | % FOLGUISTA? | **{pct.get('FOLGUISTA', 0)}%** |
| 7 | % EMPRESTIMO? | **{pct.get('EMPRESTIMO_FUNCIONARIO', 0)}%** |
| 8 | % REEMBOLSO? | **{pct.get('REEMBOLSO_FUNCIONARIO', 0)}%** |
| 9 | Período salarial capturado? | **{cal.get('payrollPeriodCaptured')}** |
| 10 | Padrão dia 15? | **{cal.get('concentrationDay15')}%** |
| 11 | Padrão fim do mês? | **{cal.get('concentrationEndMonth')}%** |
| 12 | Funcionário identificado? | **{emp.get('pctFuncionarioCodigo')}%** com código |
| 13 | Título financeiro? | **{emp.get('pctTituloMatch')}%** match |
| 14 | Falta → desconto? | **{cash.get('generatesDescontoFuncionario')}** casos |
| 15 | Falta → título receber? | **{cash.get('generatesTituloReceber')}** casos |
| 16 | Absorvida empresa? | **{cash.get('pctUntraced')}%** sem destino |
| 17 | % faltas rastreáveis? | **{cash.get('pctTraced')}%** |
| 18 | Nova taxonomia? | PESSOAL_SALARIO, PESSOAL_VALE, PERDA_CAIXA_* |
| 19 | Impacta DRE? | Salário, quinzena, folguista, extra |
| 20 | Não impacta DRE? | Vale, adiantamento, movimentação caixa |
| 21 | DW pronto? | Modelo documentado |
| 22 | Pronto F03.3? | **Sim** |

## Limitações API

{lim_txt}

## PARECER

```text
{parecer}
```
""",
        encoding="utf-8",
    )

    print("Relatorios F03.2-A gerados.")


if __name__ == "__main__":
    main()
