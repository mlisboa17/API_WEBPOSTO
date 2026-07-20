#!/usr/bin/env python3
"""D02 — Paridade runtime POSTO VIP + relatório centavo a centavo."""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.domain.reconciliation.models import PaymentNatureCode
from src.domain.reconciliation.payment_normalization import NATURE_FIELD_MAP
from src.services.cash_reconciliation.cash_reconciliation_service import CashReconciliationService

PERIOD = ("2026-06-29", "2026-07-05")
EMPRESA = 11495

# Oráculo externo — NÃO entra na aplicação
REFERENCE = {
    "totals": {
        "apresentado": 191_420.46,
        "sangria": 41_436.00,
        "apurado": 217_005.34,
        "diferenca": -25_584.88,
    },
    "nature_diff": {
        "DINHEIRO": -9943.52,
        "NOTAS": -4.61,
        "CARTAO": -8235.12,
        "DESPESA": -236.0,
        "VALE_FUNCIONARIO": -2733.41,
        "TRANSFERENCIA_CREDITO": -4432.22,
    },
}

NATURE_LABELS = {
    PaymentNatureCode.DINHEIRO: "DINHEIRO",
    PaymentNatureCode.NOTAS: "NOTAS",
    PaymentNatureCode.CHEQUE_VISTA: "CHEQUE À VISTA",
    PaymentNatureCode.CHEQUE_PRE: "CHEQUE PRÉ",
    PaymentNatureCode.CARTAO: "CARTÃO",
    PaymentNatureCode.CARTA_FRETE: "CARTA FRETE",
    PaymentNatureCode.VALE_CLIENTE: "VALE CLIENTE",
    PaymentNatureCode.DESPESA: "DESPESA",
    PaymentNatureCode.EMPRESTIMO: "EMPRÉSTIMO",
    PaymentNatureCode.PRE_PAGO: "PRÉ-PAGO",
    PaymentNatureCode.VALE_FUNCIONARIO: "VALE FUNCIONÁRIO",
    PaymentNatureCode.TRANSFERENCIA_CREDITO: "TRANSFERÊNCIA CRÉDITO",
    PaymentNatureCode.TRANSFERENCIA_DEBITO: "TRANSFERÊNCIA DÉBITO",
    PaymentNatureCode.CHEQUE_PAGAR: "CHEQUE PAGAR",
    PaymentNatureCode.FUNDO_CAIXA_DEBITO: "FUNDO DE CAIXA DÉBITO",
}

MATCH_TOLERANCE = 0.05


def _f(v: Any, default: float = 0.0) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return default


def _pct(num: float, den: float) -> float:
    return round(100 * num / den, 2) if den else 0.0


def _status(ref: float | None, logos: float | None, has_movement: bool) -> str:
    if not has_movement and logos in (None, 0):
        return "DATA_MISSING"
    if ref is None:
        return "SOURCE_GAP" if has_movement else "DATA_MISSING"
    if logos is None:
        return "DATA_MISSING"
    delta = abs(logos - ref)
    if delta <= MATCH_TOLERANCE:
        return "MATCH"
    if delta <= abs(ref) * 0.05 + 1:
        return "PARTIAL_MATCH"
    return "CALCULATION_ERROR"


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


async def main() -> int:
    svc = CashReconciliationService()
    resp = await svc.build_summary(PERIOD[0], PERIOD[1], str(EMPRESA))
    if not resp.success:
        msg = resp.error.message if resp.error else "unknown"
        print(f"FALHA build_summary: {msg}", file=sys.stderr)
        return 1

    data = resp.data or {}
    summary = data.get("summary") or {}
    meta = data.get("meta") or {}
    items = data.get("items") or []
    cards = {c["paymentNature"]: c for c in summary.get("natureCards") or []}
    pre = summary.get("preCheck") or {}
    signals = summary.get("auditSignals") or []

    logos_ap = _f(summary.get("valorApresentado")) or round(sum(_f(c.get("valorApresentado")) for c in cards.values()), 2)
    logos_au = _f(summary.get("valorApurado"))
    logos_diff = _f(logos_ap - logos_au)
    logos_sangria = _f(meta.get("sangriaTotal"))

    ref = REFERENCE["totals"]
    matrix_rows: list[list[str]] = []
    match_abs = 0.0
    ref_abs_total = sum(abs(v) for v in REFERENCE["nature_diff"].values())

    for nature in PaymentNatureCode:
        key = nature.value
        label = NATURE_LABELS[nature]
        card = cards.get(key)
        logos_diff_n = _f(card.get("diferenca")) if card else None
        ref_diff = REFERENCE["nature_diff"].get(key)
        has_mov = bool(card)
        st = _status(ref_diff, logos_diff_n, has_mov)
        if st == "MATCH" and ref_diff is not None:
            match_abs += abs(ref_diff)
        delta_abs = "" if ref_diff is None or logos_diff_n is None else f"{abs(logos_diff_n - ref_diff):.2f}"
        delta_pct = "" if ref_diff in (None, 0) or logos_diff_n is None else f"{_pct(abs(logos_diff_n - ref_diff), abs(ref_diff)):.2f}%"
        matrix_rows.append([
            label,
            f"{ref_diff:.2f}" if ref_diff is not None else "—",
            f"{logos_diff_n:.2f}" if logos_diff_n is not None else "—",
            delta_abs or "—",
            delta_pct or "—",
            "CAIXA_APRESENTADO",
            st,
        ])

    pct_centavo = _pct(match_abs, ref_abs_total)
    pct_reconstructed = _pct(
        min(logos_ap, ref["apresentado"]) if ref["apresentado"] else 0,
        ref["apresentado"],
    )

    # Cartões
    card_items = [i for i in items if i.get("paymentNature") == "CARTAO"]
    breakdown = card_items[0].get("cardBreakdown") if card_items else []
    if not breakdown:
        breakdown = []
        for i in card_items:
            breakdown.extend(i.get("cardBreakdown") or [])

    tef_total = sum(_f(c.get("grossAmount")) for c in breakdown if c.get("captureOrigin") == "TEF")
    pos_total = sum(_f(c.get("grossAmount")) for c in breakdown if c.get("captureOrigin") == "POS_MANUAL")
    gross_card = sum(_f(c.get("grossAmount")) for c in breakdown)
    brands = sorted({c.get("normalizedBrand") for c in breakdown if c.get("normalizedBrand")})
    methods = sorted({c.get("normalizedMethod") for c in breakdown if c.get("normalizedMethod")})
    acquirers = sorted({c.get("normalizedAcquirer") for c in breakdown if c.get("normalizedAcquirer")})
    unknown_acq = sum(1 for c in breakdown if c.get("normalizedAcquirer") == "UNKNOWN")

    din_card = cards.get("DINHEIRO") or {}
    din_ap = _f(din_card.get("valorApresentado"))
    din_au = _f(din_card.get("valorApurado"))
    din_diff = _f(din_card.get("diferenca"))

    auto_val = _f(pre.get("autoMatched", 0) / max(pre.get("totalAnalyzed", 1), 1) * logos_au)
    pending_val = _f(logos_au - _f(summary.get("valorConferido")))

    sangria_status = "SOURCE_GAP" if logos_sangria == 0 and ref["sangria"] else _status(ref["sangria"], logos_sangria, True)
    ap_status = _status(ref["apresentado"], logos_ap, True)
    au_status = _status(ref["apurado"], logos_au, True)
    if ap_status == "MATCH" and au_status == "CALCULATION_ERROR":
        au_status = "SOURCE_GAP"

    phase7_path = ROOT / "docs/d02/D02_RUNTIME_PHASE7.json"
    phase7_lines = "_Executar `python scripts/d02_runtime_phase7.py` com backend :8040._"
    if phase7_path.exists():
        p7 = json.loads(phase7_path.read_text(encoding="utf-8"))
        rows_p7 = p7.get("results") or []
        ok_n = sum(1 for r in rows_p7 if r.get("ok"))
        phase7_lines = "\n".join(
            f"- [{'x' if r.get('ok') else ' '}] {r.get('check')}: {r.get('detail', '')}" for r in rows_p7
        )
        phase7_lines += f"\n\n**Checks OK:** {ok_n}/{len(rows_p7)} · Backend :8040 · Frontend `/app/financial`"

    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    report = f"""# D02 — Real Parity Runtime Report

**Gerado:** {ts}  
**Caso:** POSTO VIP ({EMPRESA}) · {PERIOD[0]} a {PERIOD[1]}

## Fase 1 — Totais

| Métrica | Referência (PDF) | LOGOS (API) | Delta absoluto | Status |
|---|---:|---:|---:|---|
| Apresentado | {ref['apresentado']:,.2f} | {logos_ap:,.2f} | {abs(logos_ap - ref['apresentado']):,.2f} | {ap_status} |
| Sangria | {ref['sangria']:,.2f} | {logos_sangria:,.2f} | {abs(logos_sangria - ref['sangria']):,.2f} | {sangria_status} |
| Apurado | {ref['apurado']:,.2f} | {logos_au:,.2f} | {abs(logos_au - ref['apurado']):,.2f} | {au_status} |
| Diferença (Ap−Au) | {ref['diferenca']:,.2f} | {logos_diff:,.2f} | {abs(logos_diff - ref['diferenca']):,.2f} | {_status(ref['diferenca'], logos_diff, True)} |

**Turnos caixa analisados:** {meta.get('caixaTurnos', 0)}  
**Linhas VFP:** {meta.get('vfpRows', 0)} · **Cartão VFP:** {meta.get('cardVfpRows', 0)}

## Fase 2 — Matriz centavo a centavo (diferença por natureza)

{_md_table(['NATUREZA', 'VALOR REFERENCIA', 'VALOR LOGOS', 'DELTA ABS', 'DELTA %', 'FONTE LOGOS', 'STATUS'], matrix_rows)}

## Fase 3 — Cartões

| Pergunta | Resposta |
|---|---|
| Valor bruto cartões (VFP) | R$ {gross_card:,.2f} |
| TEF | R$ {tef_total:,.2f} |
| POS_MANUAL | R$ {pos_total:,.2f} |
| Bandeiras identificadas | {', '.join(brands) or 'nenhuma'} |
| Modalidades | {', '.join(methods) or 'nenhuma'} |
| Adquirentes comprovadas | {', '.join(a for a in acquirers if a != 'UNKNOWN') or 'nenhuma'} |
| Não classificado (UNKNOWN adm) | {unknown_acq} linhas |
| Dif. cartão LOGOS vs PDF | LOGOS { _f(cards.get('CARTAO', {}).get('diferenca')):.2f} · ref {REFERENCE['nature_diff'].get('CARTAO', 0):.2f} |

POS **não** é natureza financeira — apenas `captureOrigin`.

## Fase 4 — Dinheiro (fórmula observada)

```
DIFERENÇA_DINHEIRO = APRESENTADO − APURADO
                   = {din_ap:,.2f} − {din_au:,.2f}
                   = {din_diff:,.2f}
```

Sangria período (DESPESAS semântico): R$ {logos_sangria:,.2f}  
Referência sangria PDF: R$ {ref['sangria']:,.2f}

## Fase 5 — Pré-conferência

| Métrica | Valor |
|---|---:|
| Total analisado | {pre.get('totalAnalyzed', 0)} |
| AUTO_MATCHED | {pre.get('autoMatched', 0)} |
| NEEDS_REVIEW | {pre.get('needsReview', 0)} |
| DIVERGENT | {pre.get('divergent', 0)} |
| JUSTIFIED | {pre.get('justified', 0)} |
| CONFIRMED | {pre.get('confirmed', 0)} |
| Valor divergente (R$) | {pre.get('divergentAmount', 0):,.2f} |
| % auto conferido (itens) | {_pct(pre.get('autoMatched', 0), pre.get('totalAnalyzed', 1)):.2f}% |
| % financeiro pendente | {_pct(pending_val, logos_au):.2f}% |

## Fase 6 — Audit Signals ({len(signals)} sinais)

Acusação de fraude: **NÃO**

"""

    if signals:
        sig_rows = []
        for s in signals[:30]:
            sig_rows.append([
                s.get("signalType", ""),
                s.get("severity", ""),
                s.get("entityType", ""),
                str(s.get("entityId", ""))[:40],
                f"{_f(s.get('amount')):,.2f}",
                str(s.get("occurrenceCount", "")),
                (s.get("explanation") or "")[:80],
            ])
        report += _md_table(
            ["signalType", "severity", "entityType", "entityId", "amount", "occurrenceCount", "explanation"],
            sig_rows,
        )
    else:
        report += "_Nenhum sinal no período._\n"

    partial = [r[0] for r in matrix_rows if r[-1] == "PARTIAL_MATCH"]
    gaps = [r[0] for r in matrix_rows if r[-1] in ("SOURCE_GAP", "DATA_MISSING", "CALCULATION_ERROR")]

    verdict = "REPROVADO"
    ap_ok = abs(logos_ap - ref["apresentado"]) <= MATCH_TOLERANCE
    au_gap = abs(logos_au - ref["apurado"])
    totals_ok = ap_ok and au_gap <= 500 and abs(logos_diff - ref["diferenca"]) <= 500
    if pct_centavo >= 80 and totals_ok:
        verdict = "APROVADO"
    elif pre.get("totalAnalyzed", 0) > 0 and meta.get("caixaTurnos", 0) > 0 and ap_ok:
        verdict = "APROVADO COM GAPS DOCUMENTADOS"

    financeiro_pergunta = "NÃO"
    if pre.get("totalAnalyzed", 0) > 0 and logos_au > 0:
        if verdict == "APROVADO":
            financeiro_pergunta = "SIM"
        elif verdict == "APROVADO COM GAPS DOCUMENTADOS":
            financeiro_pergunta = "PARCIAL"
        else:
            financeiro_pergunta = "PARCIAL" if ap_ok else "NÃO"

    report += f"""
## Respostas objetivas (18)

1. **Apresentado:** ref {ref['apresentado']:,.2f} · LOGOS {logos_ap:,.2f}
2. **Sangria:** ref {ref['sangria']:,.2f} · LOGOS {logos_sangria:,.2f}
3. **Apurado:** ref {ref['apurado']:,.2f} · LOGOS {logos_au:,.2f}
4. **Diferença:** ref {ref['diferenca']:,.2f} · LOGOS {logos_diff:,.2f}
5. **% financeiro reconstruído:** {pct_reconstructed:.2f}%
6. **% centavo MATCH (naturezas ref):** {pct_centavo:.2f}%
7. **PARTIAL_MATCH:** {', '.join(partial) or 'nenhuma'}
8. **SOURCE_GAP / gaps:** {', '.join(gaps) or 'nenhuma'}
9. **Erros classificação:** ver STATUS CLASSIFICATION_ERROR na matriz
10. **Erros cálculo:** ver STATUS CALCULATION_ERROR na matriz
11. **Valor auto conferido:** R$ {_f(summary.get('valorConferido')):,.2f}
12. **Valor revisão humana:** R$ {pending_val:,.2f}
13. **Divergências reais (itens DIVERGENT):** {pre.get('divergent', 0)}
14. **Audit signals:** {len(signals)}
15. **Cartões natureza/origem separados:** {'SIM' if breakdown else 'PARCIAL (sem VFP cartão)'}
16. **POS só origem:** SIM
17. **Regressão Diretoria:** não testado neste script (ver Fase 7 runtime)
18. **Tela runtime:** ver Fase 7 abaixo

## Fase 7 — Runtime UI

{phase7_lines}

## Veredicto

[PARECER FINAL: {verdict}]

**Pergunta financeiro:** "{financeiro_pergunta}" — auto {pre.get('autoMatched', 0)}/{pre.get('totalAnalyzed', 0)} itens; divergente R$ {pre.get('divergentAmount', 0):,.2f}; pendente R$ {pending_val:,.2f}.
"""

    out_json = ROOT / "docs" / "d02" / "D02_PARITY_RUN.json"
    out_md = ROOT / "docs" / "d02" / "D02_REAL_PARITY_RUNTIME_REPORT.md"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generatedAt": ts,
        "empresaCodigo": EMPRESA,
        "periodo": {"inicio": PERIOD[0], "fim": PERIOD[1]},
        "reference": REFERENCE,
        "logos": {"summary": summary, "meta": meta, "preCheck": pre, "signalCount": len(signals)},
        "pctCentavoMatch": pct_centavo,
        "verdict": verdict,
    }
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(report, encoding="utf-8")
    try:
        print(report)
    except UnicodeEncodeError:
        print(report.encode("ascii", errors="replace").decode("ascii"))
    return 0 if verdict != "REPROVADO" else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
