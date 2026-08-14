"""Reavalia o custo dos produtos ja cadastrados sob a politica de custo corrigida.

A inclusao do ICMS-ST cobrado na entrada pode revelar custo subestimado em cadastros
anteriores. Este script apenas mede e reporta: nenhuma alteracao e enviada a API.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.operational.product_registration.dfe_cost_resolver import (  # noqa: E402
    build_authorized_index,
    cost_from_index,
)

CHECKPOINT = ROOT / "data" / "product_registration" / "execution" / "checkpoint_118508.json"
OUT = ROOT / "data" / "product_registration" / "microbatch_02_118508" / "cost_impact_audit.json"


def main() -> None:
    checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    index = build_authorized_index(118508)
    findings = []

    print(f"{'EAN':<15} {'cadastrado':>11} {'recalculado':>12} {'delta':>9}  ICMS-ST  produto")
    for ean, info in checkpoint.items():
        evidence = cost_from_index(ean, index)
        recalculated = float(evidence.preco_custo) if evidence.preco_custo is not None else None
        registered = info.get("precoCusto") or info.get("preco_custo")
        st = float(evidence.icms_st_cobrado or 0)
        delta = (
            round(recalculated - float(registered), 4)
            if recalculated is not None and registered
            else None
        )
        findings.append(
            {
                "ean": ean,
                "produtoCodigo": info.get("produtoCodigo"),
                "descricao": info.get("descricao"),
                "precoCustoCadastrado": registered,
                "precoCustoRecalculado": recalculated,
                "delta": delta,
                "icmsStCobradoNaNota": st,
                "unidadeAtomica": evidence.unidade_atomica,
                "statusCusto": evidence.status,
                "subestimado": bool(delta and delta > 0.0001),
            }
        )
        print(
            f"{ean:<15} {str(registered):>11} {str(recalculated):>12} {str(delta):>9}"
            f"  {st:>7}  {info.get('produtoCodigo')}"
        )

    understated = [f for f in findings if f["subestimado"]]
    print()
    print(f"cadastros com custo subestimado: {len(understated)} de {len(findings)}")
    for item in understated:
        print(
            f"   {item['ean']} produto {item['produtoCodigo']}: "
            f"{item['precoCustoCadastrado']} -> {item['precoCustoRecalculado']} "
            f"(ICMS-ST {item['icmsStCobradoNaNota']})"
        )
    print()
    print("Nenhuma escrita executada: correcao de cadastro existente exigiria PUT, que e proibido.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "title": "AUDITORIA DE IMPACTO DA POLITICA DE CUSTO — 118508",
                "policyChange": "ICMS-ST cobrado na entrada passa a compor o custo",
                "apiWrites": 0,
                "understatedCount": len(understated),
                "findings": findings,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
