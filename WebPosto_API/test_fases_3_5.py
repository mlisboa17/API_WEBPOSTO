#!/usr/bin/env python3
"""Teste FASES 3-5: Carregamento e análise preflight."""

import asyncio
from pathlib import Path
from src.operational.product_registration.service import ProductRegistrationService


async def test():
    xlsx_path = Path(
        r"C:\Users\mlisb\Documents\Codex\2026-08-11\logos-webposto-codex-alterar-produto-safe\outputs\019ff247-8453-7c90-93f1-1458b660ffc2\CADASTRO_PRODUTOS_WEBPOSTO_VALIDADO.xlsx"
    )
    service = ProductRegistrationService(xlsx_path=xlsx_path)

    # FASE 3
    print("[TESTE] FASE 3: Carregando planilha...")
    metadata = await service.load_and_validate_spreadsheet()
    print(f"  Total: {metadata['total_rows']} produtos")
    print(f"  Hash: {metadata['file_hash'][:16]}...")

    # FASE 5
    print("\n[TESTE] FASE 5: Analisando...")
    analyses = await service.analyze_all_products()

    by_status = {}
    for a in analyses:
        if a.status not in by_status:
            by_status[a.status] = 0
        by_status[a.status] += 1

    print("  Status:")
    for status, count in sorted(by_status.items()):
        print(f"    {status}: {count}")

    # FASE 6
    print("\n[TESTE] FASE 6: Resumo preflight")
    service.print_preflight_summary()

    print("\n[TESTE] Sucesso - FASES 3-6 concluidas!")


if __name__ == "__main__":
    asyncio.run(test())
