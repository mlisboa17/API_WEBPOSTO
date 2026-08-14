#!/usr/bin/env python3
"""Execução completa FASES 3-10 com relatórios."""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

from src.operational.product_registration.service import ProductRegistrationService


async def main():
    load_dotenv()
    
    xlsx_path = Path(
        r"C:\Users\mlisb\Documents\Codex\2026-08-11\logos-webposto-codex-alterar-produto-safe\outputs\019ff247-8453-7c90-93f1-1458b660ffc2\CADASTRO_PRODUTOS_WEBPOSTO_VALIDADO.xlsx"
    )

    chave = os.getenv("WEBPOSTO_CHAVE")
    base_url = os.getenv("WEBPOSTO_BASE_URL", "https://web.qualityautomacao.com.br")

    service = ProductRegistrationService(
        xlsx_path=xlsx_path,
        base_url=base_url,
        chave=chave,
    )

    print("\n" + "=" * 80)
    print("FASES 3-10: CADASTRO AUTOMÁTICO DE PRODUTOS WEBPOSTO")
    print("=" * 80 + "\n")

    # FASE 3
    print("[FASE 3] Consolidando pipeline...")
    metadata = await service.load_and_validate_spreadsheet()
    print(f"  Planilha carregada: {metadata['total_rows']} produtos")
    print(f"  Hash SHA-256: {metadata['file_hash']}")

    # FASE 5
    print("\n[FASE 5] Pré-voo (read-only)...")
    analyses = await service.analyze_all_products()

    # FASE 6
    print("\n[FASE 6] Resumo preflight")
    service.print_preflight_summary()

    # FASE 10 (apenas preflight)
    print("\n[FASE 10] Gerando relatórios...")
    report_paths = await service.export_final_reports()

    print("\nRelatórios gerados:")
    for name, path in report_paths.items():
        print(f"  {name}: {path}")

    print("\n" + "=" * 80)
    print("PREFLIGHT CONCLUÍDO COM SUCESSO")
    print("=" * 80 + "\n")
    print(f"Execution ID: {service.execution_id}")
    print(f"Caminho para checkpoint: {service.checkpoint_dir / (service.execution_id or 'N/A')}")


if __name__ == "__main__":
    asyncio.run(main())
