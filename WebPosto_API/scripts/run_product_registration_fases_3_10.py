#!/usr/bin/env python3
"""
FASES 3-10: Cadastro Automático de Produtos WebPosto — Empresa 118508

Executa sequencialmente:
- FASE 3: Consolidar Pipeline (ler XLSX)
- FASE 5: Pré-Voo Read-Only (análise)
- FASE 6: Apresentar Resumo
- FASES 7-9: Executar READY_TO_CREATE
- FASE 10: Relatório Final
"""

import asyncio
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
)

# Adicionar src ao path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.operational.product_registration.service import ProductRegistrationService


async def main():
    """Executa pipeline completo FASES 3-10."""
    
    # Caminhos
    xlsx_path = Path(
        r"C:\Users\mlisb\Documents\Codex\2026-08-11\logos-webposto-codex-alterar-produto-safe\outputs\019ff247-8453-7c90-93f1-1458b660ffc2\CADASTRO_PRODUTOS_WEBPOSTO_VALIDADO.xlsx"
    )
    
    if not xlsx_path.exists():
        print(f"ERRO: Planilha não encontrada: {xlsx_path}")
        return

    # Credenciais (da variável de ambiente ou arquivo .env)
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    chave = os.getenv("WEBPOSTO_CHAVE")
    base_url = os.getenv("WEBPOSTO_BASE_URL", "https://web.qualityautomacao.com.br")

    # Criar serviço
    service = ProductRegistrationService(
        xlsx_path=xlsx_path,
        base_url=base_url,
        chave=chave,
    )

    # Executar pipeline
    try:
        result = await service.run_full_pipeline()
        
        print("\n" + "=" * 80)
        print("PIPELINE CONCLUÍDO COM SUCESSO")
        print("=" * 80)
        print(f"\nExecution ID: {result['execution_id']}")
        print(f"\nCriados e Verificados: {len(result['execution_result'].get('created_verified', []))}")
        print(f"Criados mas não verificados: {len(result['execution_result'].get('created_not_verified', []))}")
        print(f"Rejeitados: {len(result['execution_result'].get('rejected', []))}")
        print(f"Erro: {len(result['execution_result'].get('result_unknown', []))}")
        
        print(f"\nRelatórios gerados:")
        for name, path in result['report_paths'].items():
            print(f"  {name}: {path}")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"\nERRO CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
