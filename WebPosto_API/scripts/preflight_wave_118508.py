"""Mostra a fila que a onda executaria, sem tocar na API.

Le fiscal_profiles_118508.json e imprime, por perfil, o canario e os produtos que
seguiriam sob a mesma aprovacao. Nao envia nada.

Uso: python scripts/preflight_wave_118508.py --wave 1 --limit 20
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ROOT / "data" / "product_registration" / "fiscal_profiles_118508.json"


def load_executor():
    path = ROOT / "scripts" / "execute_wave_118508.py"
    spec = importlib.util.spec_from_file_location("execute_wave_118508", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser(description="Preflight da onda (read-only)")
    parser.add_argument("--wave", type=int, default=1)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--by-payload", action="store_true")
    args = parser.parse_args()

    executor = load_executor()
    payload = json.loads(PROFILES.read_text(encoding="utf-8"))
    gated_out: list[dict] = []
    queue = executor.build_queue(
        payload["profiles"],
        executor.WAVE_LEVELS[args.wave],
        args.limit,
        by_payload=args.by_payload,
        gate=executor.product_gate,
        rejected=gated_out,
    )

    profile_ids = {item["profile"]["profile_id"] for item in queue}
    print("=" * 78)
    print(f"PREFLIGHT ONDA {args.wave} — {len(queue)} produtos em {len(profile_ids)} perfis")
    print("=" * 78)
    if gated_out:
        print(f"removidos antes de ocupar vaga: {len(gated_out)}")
        for entry in gated_out:
            print(f"   {entry['ean']} | {entry['descricao'][:44]} | {entry['motivo']}")

    current = None
    for position, item in enumerate(queue, 1):
        profile, product = item["profile"], item["product"]
        body = product["body"]["preview"]
        if profile["profile_id"] != current:
            current = profile["profile_id"]
            evidence = profile["evidencias"]
            print()
            print(f"{profile['profile_id']}  [{profile['level']}]")
            print(f"   canario {profile['profile_canary_status']} | confianca "
                  f"{profile['confidence']} | risco {profile['fiscal_risk']} | "
                  f"revisao contabil {profile['requires_accountant_review']}")
            if args.by_payload:
                print(f"   perfis fiscais reunidos: {len(profile.get('perfis_fiscais') or [])}"
                      f" | NCMs distintos {len(profile['ncms'])}"
                      f" | CESTs distintos {len(profile['cests'])}")
            else:
                print(f"   NCM {profile['ncms']} | CEST {profile['cests']}")
            print(f"   entrada {profile['tratamento_observado']} | base "
                  f"{evidence.get('tax_basis_source')} | evidencia de entrada "
                  f"{evidence.get('entry_tax_evidence')} | autoridade "
                  f"{evidence.get('decision_authority')}")
            print(f"   ICMS ref {profile['referencia_icms']} | PIS/COFINS ref "
                  f"{profile['referencia_pis_cofins']} | CFOP {profile['cfop_entrada']} -> "
                  f"{profile['cfop_saida']} | monofasica {profile['tributacao_monofasica']}")
            if evidence.get("origem") == "ANALOGIA_NCM_CEST":
                print(f"   evidencia: {evidence['itens']} itens de mesmo NCM+CEST | "
                      f"{evidence['notasDistintas']} notas | "
                      f"{evidence['fornecedoresDistintos']} fornecedores | familia "
                      f"{evidence.get('familiaEvidencia')} | CST {evidence.get('distribuicaoCst')}")
                for sample in (evidence.get("amostra") or [])[:3]:
                    print(f"      {sample.get('descricao')} | CST {sample.get('cstIcms')} | "
                          f"NF-e {sample.get('nfe')}")
            else:
                print(f"   evidencia: {evidence.get('origem')}")
        marker = "CANARIO" if item["is_canary"] else "       "
        icms = body["tributoIcms"]
        print(f"   {position:>2} {marker} {product['ean']} | {product['descricao'][:42]:<42}"
              f" | venda {body['precoVenda']:>7} | custo {body['precoCusto']} "
              f"{product['custo']['source']} | saida CST {icms.get('cstSaida')} "
              f"{icms.get('percentualIcmsSaida')}% | hash {product['body']['hash'][:12]}")

    print()
    print("API WRITES: 0")


if __name__ == "__main__":
    main()
