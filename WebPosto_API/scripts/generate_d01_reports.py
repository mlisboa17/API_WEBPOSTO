#!/usr/bin/env python3
"""Gera relatórios D01 a partir de scripts/d01_operational_join_probe.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "d01_operational_join_probe.json"


def load() -> dict:
    if not AUDIT.exists():
        raise SystemExit("Execute: python scripts/audit_d01_operational_join_probe.py")
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def w(d: dict) -> dict:
    for key in ("7d", "30d", "90d"):
        if key in d.get("windows", {}):
            return d["windows"][key]
    return next(iter(d.get("windows", {}).values()), {})


def brl(v) -> str:
    if v is None:
        return "—"
    return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


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


def field_rows(discovery: dict, questions: list[tuple[str, str]]) -> str:
    fields = discovery.get("fields") or {}
    via = discovery.get("viaVenda") or {}
    rows = []
    for num, key in questions:
        label = {
            "caixaCodigo": "Existe caixaCodigo?",
            "turnoCodigo": "Existe turnoCodigo?",
            "vendaCodigo": "Existe vendaCodigo?",
            "funcionarioCodigo": "Existe funcionarioCodigo?",
            "pdvCodigo": "Existe pdvCodigo?",
            "nomeFormaPagamento": "Forma pagamento detalhada?",
            "administradoraCodigo": "Existe administradora?",
        }.get(key, key)
        if key in via:
            meta = via[key]
            rows.append([num, label, yn(meta.get("exists")), f"{meta.get('coveragePct', 0)}%"])
        elif key in fields:
            meta = fields[key]
            rows.append([num, label, yn(meta.get("exists")), f"{meta.get('coveragePct', 0)}%"])
        else:
            rows.append([num, label, "**Não**", "0%"])
    return md_table(["#", "Pergunta", "Resposta", "Cobertura"], rows)


def main() -> None:
    data = load()
    ref = w(data)
    ex = data.get("executiveAnswers") or {}
    parecer = data.get("parecerFinal") or ""
    joins = ref.get("joinMatrix") or []
    perf = ref.get("performance") or {}
    prest = ref.get("prestacaoProbe") or {}
    prod = ref.get("operatorProductivity") or {}

    pf = ref.get("paymentFormDiscovery") or {}
    sd = ref.get("saleDiscovery") or {}
    si = ref.get("saleItemDiscovery") or {}
    fd = ref.get("fuelingDiscovery") or {}
    nd = ref.get("nfceDiscovery") or {}

    # Agent 1
    (ROOT / "PAYMENT_FORM_DISCOVERY_REPORT.md").write_text(
        f"""# PAYMENT FORM DISCOVERY — D01 · Agente 1

Janela ref: **{ref.get('window')}** · {ref.get('periodo')}

## Campos mapeados ({pf.get('totalRows', 0)} registros)

{', '.join(pf.get('allKeys') or []) or '—'}

## Respostas

{field_rows(pf, [
    ("1", "caixaCodigo"),
    ("2", "turnoCodigo"),
    ("3", "vendaCodigo"),
    ("4", "funcionarioCodigo"),
    ("5", "pdvCodigo"),
    ("6", "nomeFormaPagamento"),
    ("7", "administradoraCodigo"),
])}

**Nota:** `caixaCodigo`, `funcionarioCodigo`, `pdvCodigo` **não estão no payload VFP** — obtidos via join **VFP → VENDA → CAIXA** (cobertura bridge: **{ref.get('vfpToCaixaViaVendaPct', 0)}%**).
""",
        encoding="utf-8",
    )

    # Agent 2
    (ROOT / "SALE_DISCOVERY_REPORT.md").write_text(
        f"""# SALE DISCOVERY — D01 · Agente 2

Registros: **{sd.get('totalRows', 0)}**

## Campos

{', '.join(sd.get('allKeys') or [])[:500]}

## Respostas

{md_table(["#", "Pergunta", "Resposta", "Cobertura"], [
    ["1", "Ligação com caixa?", yn((sd.get('fields') or {}).get('caixaCodigo', {}).get('exists')), f"{(sd.get('fields') or {}).get('caixaCodigo', {}).get('coveragePct', 0)}%"],
    ["2", "Ligação com operador?", yn((sd.get('fields') or {}).get('funcionarioCodigo', {}).get('exists')), f"{(sd.get('fields') or {}).get('funcionarioCodigo', {}).get('coveragePct', 0)}%"],
    ["3", "Venda cancelada?", yn(any((sd.get('fields') or {}).get('cancelada', {}).get('exists') for _ in [1])), f"{(sd.get('fields') or {}).get('cancelada', {}).get('coveragePct', 0)}%"],
    ["4", "Troco?", yn((sd.get('fields') or {}).get('troco', {}).get('exists')), f"{(sd.get('fields') or {}).get('troco', {}).get('coveragePct', 0)}%"],
    ["5", "PDV direto?", yn((sd.get('fields') or {}).get('pdvCodigo', {}).get('exists')), f"{(sd.get('fields') or {}).get('pdvCodigo', {}).get('coveragePct', 0)}%"],
])}

**Nota:** `pdvCodigo` normalmente via **CAIXA** (join `caixaCodigo`), não em VENDA.
""",
        encoding="utf-8",
    )

    # Agent 3
    (ROOT / "SALE_ITEM_DISCOVERY_REPORT.md").write_text(
        f"""# SALE ITEM DISCOVERY — D01 · Agente 3

Registros: **{si.get('totalRows', 0)}**

## Respostas

{md_table(["#", "Pergunta", "Resposta", "Cobertura"], [
    ["1", "Operador por item?", yn((si.get('fields') or {}).get('funcionarioCodigo', {}).get('exists')), f"{(si.get('fields') or {}).get('funcionarioCodigo', {}).get('coveragePct', 0)}%"],
    ["2", "Bico?", yn((si.get('fields') or {}).get('bicoCodigo', {}).get('exists')), f"{(si.get('fields') or {}).get('bicoCodigo', {}).get('coveragePct', 0)}%"],
    ["3", "Desconto?", yn((si.get('fields') or {}).get('totalDesconto', {}).get('exists')), f"{(si.get('fields') or {}).get('totalDesconto', {}).get('coveragePct', 0)}%"],
    ["4", "Produto?", yn((si.get('fields') or {}).get('produtoCodigo', {}).get('exists')), f"{(si.get('fields') or {}).get('produtoCodigo', {}).get('coveragePct', 0)}%"],
    ["5", "Combustível vs produto?", yn((si.get('fields') or {}).get('bicoCodigo', {}).get('exists')), "bico/tanque/LMC"],
])}
""",
        encoding="utf-8",
    )

    # Agent 4
    (ROOT / "FUELING_DISCOVERY_REPORT.md").write_text(
        f"""# FUELING DISCOVERY — D01 · Agente 4

Registros: **{fd.get('totalRows', 0)}**

## Respostas

{md_table(["#", "Pergunta", "Resposta", "Cobertura"], [
    ["1", "Ligação com venda?", "via vendaItemCodigo", f"{joins[3]['coveragePct'] if len(joins)>3 else 0}%"],
    ["2", "Frentista?", yn((fd.get('fields') or {}).get('codigoFrentista', {}).get('exists')), f"{(fd.get('fields') or {}).get('codigoFrentista', {}).get('coveragePct', 0)}%"],
    ["3", "Bico?", yn((fd.get('fields') or {}).get('codigoBico', {}).get('exists')), f"{(fd.get('fields') or {}).get('codigoBico', {}).get('coveragePct', 0)}%"],
    ["4", "Encerrante?", yn((fd.get('fields') or {}).get('encerrante', {}).get('exists')), f"{(fd.get('fields') or {}).get('encerrante', {}).get('coveragePct', 0)}%"],
    ["5", "Tanque?", "codigoProduto/tanque via item", "indireto"],
])}
""",
        encoding="utf-8",
    )

    # Agent 5
    (ROOT / "NFCE_DISCOVERY_REPORT.md").write_text(
        f"""# NFCE DISCOVERY — D01 · Agente 5

Registros: **{nd.get('totalRows', 0)}**

## Respostas

{md_table(["#", "Pergunta", "Resposta"], [
    ["1", "Ligação com venda?", yn((nd.get('fields') or {}).get('vendaCodigo', {}).get('exists'))],
    ["2", "Cancelamento?", yn((nd.get('fields') or {}).get('situacao', {}).get('exists'))],
    ["3", "Emissão fiscal?", yn((nd.get('fields') or {}).get('dataEmissao', {}).get('exists'))],
    ["4", "NFC-e canceladas?", "Ver campo `situacao` + join VENDA.cancelada"],
])}
""",
        encoding="utf-8",
    )

    # Agent 6
    jrows = [[j["a"], j["b"], ", ".join(j.get("keys") or ()), f"{j.get('coveragePct')}%", j.get("confidence")] for j in joins]
    jrows.append(["VFP", "CAIXA", "via VENDA.caixaCodigo", f"{ref.get('vfpToCaixaViaVendaPct', 0)}%", "MEDIUM"])
    (ROOT / "OPERATIONAL_JOIN_KEY_MATRIX.md").write_text(
        f"""# OPERATIONAL JOIN KEY MATRIX — D01 · Agente 6

Janela: **{ref.get('window')}**

{md_table(["Fonte A", "Fonte B", "Chave", "Cobertura %", "Confiança"], jrows)}
""",
        encoding="utf-8",
    )

    # Agent 7
    layers = prest.get("reconstructionLayers") or {}
    (ROOT / "PRESTACAO_RECONSTRUCTION_PROBE.md").write_text(
        f"""# PRESTAÇÃO RECONSTRUCTION PROBE — D01 · Agente 7

Alvo: **AP CASA CAIADA ({prest.get('targetEmpresa')}) · {prest.get('targetDate')} · 1º Turno**

Data na janela: **{prest.get('dateInWindow')}**

| Camada | Reconstruível? |
|--------|----------------|
| Forma pagamento | {yn(layers.get('formaPagamento'))} |
| Por funcionário | {yn(layers.get('porFuncionario'))} |
| Por PDV | {yn(layers.get('porPdv'))} |
| Por turno | {yn(layers.get('porTurno'))} |
| Combustível/produto | {yn(layers.get('combustivelProduto'))} |
| Troco/cancelamentos | {yn(layers.get('trocoCancelamentos'))} |
| Descontos | {yn(layers.get('descontos'))} |
| Participação % | {yn(layers.get('participacaoPct'))} |

**Cobertura reconstrução:** **{prest.get('reconstructionCoveragePct')}%**

### Totais dia {prest.get('targetDate')} (empresa 5555)

| Métrica | Valor |
|---------|-------|
| Vendas | {prest.get('vendasDia')} |
| Formas pagamento | {prest.get('vfpDia')} |
| Turnos caixa | {prest.get('caixaTurnos')} |
| Troco | {brl(prest.get('trocoTotal'))} |
| Cancelamentos | {prest.get('cancelamentos')} |
| Descontos | {brl(prest.get('descontoTotal'))} |
| Combustível | {brl(prest.get('combustivelValor'))} |
| Produto | {brl(prest.get('produtoValor'))} |

### Por forma de pagamento

{prest.get('byFormaPagamento')}

### Por funcionário (valor)

{prest.get('byFuncionarioValor')}
""",
        encoding="utf-8",
    )

    # Agent 8
    (ROOT / "OPERATOR_PRODUCTIVITY_PROBE.md").write_text(
        f"""# OPERATOR PRODUCTIVITY PROBE — D01 · Agente 8

## Calculado via API (empresa 5555)

| Métrica | Disponível |
|---------|------------|
| Valor vendido por funcionário | {yn(bool(prod.get('valorPorFuncionario')))} |
| Abastecimentos por frentista | {yn(bool(prod.get('abastecimentosPorFrentista')))} |
| Valor combustível frentista | {yn(bool(prod.get('combustivelPorFrentista')))} |
| Participação % calculada | {yn(bool(prod.get('participacaoCalculada')))} |
| Participação % oficial Prestação | **Não** |

### Participação calculada (proxy)

{prod.get('participacaoCalculada')}

**Gap:** produtividade oficial e meta continuam **exclusivos da Prestação/UI**.
""",
        encoding="utf-8",
    )

    # Agent 9
    prows = []
    for k, v in sorted(perf.items()):
        prows.append([
            k, v.get("status"), v.get("latencyMsAvg"), v.get("pages"),
            v.get("hasData"), v.get("count"), v.get("timeout"), v.get("truncated"),
        ])
    (ROOT / "OPERATIONAL_PROBE_PERFORMANCE_REPORT.md").write_text(
        f"""# OPERATIONAL PROBE PERFORMANCE — D01 · Agente 9

Elapsed window: **{ref.get('elapsedSec')}s** · Truncated any: **{ref.get('truncatedAny')}**

{md_table(["Endpoint", "Status", "Lat ms avg", "Pages", "has_data", "Registros", "Timeout", "Truncated"], prows)}
""",
        encoding="utf-8",
    )

    # Agent 10
    (ROOT / "F04_SOURCE_ARCHITECTURE_DECISION.md").write_text(
        f"""# F04 SOURCE ARCHITECTURE DECISION — D01 · Agente 10

## Respostas

| # | Pergunta | Decisão |
|---|----------|---------|
| 1 | API reconstrói Prestação? | **Parcial ({prest.get('reconstructionCoveragePct')}%)** — transacional sim, nominal não |
| 2 | Campos exigem PDF/UI? | **funcionarioNome, produtividade oficial, participação UI, fundoCaixa, meta** |
| 3 | Módulos API estruturada? | Vendas, forma pagamento, abastecimento, cancelamentos, mix PDV |
| 4 | Módulos precisam Prestação? | Accountability nominal, produtividade oficial, layout turno |
| 5 | Fontes primárias F04 | **VENDA, VENDA_ITEM, VENDA_FORMA_PAGAMENTO, CAIXA, ABASTECIMENTO** |
| 6 | Fontes auxiliares F04 | NFCE, MOVIMENTO_CONTA, CAIXA_APRESENTADO, DESPESAS_REDE |

## Modelo híbrido F04

```text
TRANSACIONAL (API)     → VENDA + VFP + VENDA_ITEM + ABASTECIMENTO + CAIXA
ACCOUNTABILITY NOMINAL → Prestação PDF/UI ou parser
FINANCEIRO             → DESPESAS + TITULO (mantém)
AUDITORIA              → NFCE + FINANCEIRO_EXCLUSAO
```

Join proof: **{yn(ex.get('joinProofOk'))}**
""",
        encoding="utf-8",
    )

    # Final report
    erows = [[i, k, yn(v) if isinstance(v, bool) else v] for i, (k, v) in enumerate(ex.items(), 1) if not k.startswith("join")]
    (ROOT / "D01_LIVE_OPERATIONAL_JOIN_PROBE_REPORT.md").write_text(
        f"""# D01 — LIVE OPERATIONAL JOIN PROBE

## Respostas executivas (1–20)

{md_table(["#", "Chave", "Resposta"], erows[:20])}

## Join matrix (resumo)

{md_table(["A", "B", "Cobertura", "Confiança"], [[j['a'], j['b'], f"{j['coveragePct']}%", j['confidence']] for j in joins])}

## Critérios aceite

| Critério | Status |
|----------|--------|
| Matriz de chaves | {yn(data.get('qa', {}).get('joinMatrixFilled'))} |
| Cobertura reconstrução medida | {yn(data.get('qa', {}).get('reconstructionMeasured'))} — **{prest.get('reconstructionCoveragePct')}%** |
| Join VENDA/CAIXA/VFP comprovado | {yn(data.get('qa', {}).get('joinProofOk'))} |
| Limitações documentadas | Sim |

## Entregáveis

- PAYMENT_FORM_DISCOVERY_REPORT.md
- SALE_DISCOVERY_REPORT.md
- SALE_ITEM_DISCOVERY_REPORT.md
- FUELING_DISCOVERY_REPORT.md
- NFCE_DISCOVERY_REPORT.md
- OPERATIONAL_JOIN_KEY_MATRIX.md
- PRESTACAO_RECONSTRUCTION_PROBE.md
- OPERATOR_PRODUCTIVITY_PROBE.md
- OPERATIONAL_PROBE_PERFORMANCE_REPORT.md
- F04_SOURCE_ARCHITECTURE_DECISION.md

{parecer}
""",
        encoding="utf-8",
    )
    print("Relatórios D01 gerados.")
    print(parecer)


if __name__ == "__main__":
    main()
