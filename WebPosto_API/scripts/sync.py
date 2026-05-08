"""
Script de sincronização de dados do WebPosto.
Exemplo de uso: python -m scripts.sync

Adapte conforme as necessidades do Grupo Lisboa.
"""

import json
import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

# Adiciona o src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

load_dotenv()

from webposto import WebPostoClient

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("webposto.sync")


def main():
    logger.info("Iniciando sincronização WebPosto...")

    client = WebPostoClient.from_env()

    # Healthcheck
    client.healthcheck()
    logger.info("Conexão com WebPosto OK")

    hoje = date.today()
    ontem = hoje - timedelta(days=1)

    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)

    # ── ABASTECIMENTOS ──────────────────────────────────────────────────────
    logger.info("Buscando abastecimentos de %s...", ontem)
    abastecimentos = client.abastecimento.listar(
        data_inicial=ontem,
        data_final=hoje,
    )
    logger.info(
        "  → %d abastecimentos encontrados",
        len(abastecimentos) if isinstance(abastecimentos, list) else 1,
    )

    with open(output_dir / f"abastecimentos_{ontem}.json", "w", encoding="utf-8") as f:
        json.dump(abastecimentos, f, ensure_ascii=False, indent=2)

    # ── TÍTULOS A RECEBER ──────────────────────────────────────────────────
    logger.info("Buscando títulos a receber em aberto...")
    titulos = client.financeiro.listar_titulos_receber(
        data_inicial=date(hoje.year, 1, 1),
        data_final=hoje,
        situacao="ABERTO",
    )
    logger.info("  → títulos a receber carregados")

    with open(output_dir / f"titulos_receber_{hoje}.json", "w", encoding="utf-8") as f:
        json.dump(titulos, f, ensure_ascii=False, indent=2)

    # ── FECHAMENTO DE CAIXA ────────────────────────────────────────────────
    logger.info("Buscando fechamento de caixa de %s...", ontem)
    caixa = client.financeiro.listar_fechamento_caixa(
        data_inicial=ontem,
        data_final=ontem,
    )
    logger.info("  → fechamentos de caixa carregados")

    with open(
        output_dir / f"fechamento_caixa_{ontem}.json", "w", encoding="utf-8"
    ) as f:
        json.dump(caixa, f, ensure_ascii=False, indent=2)

    logger.info("Sincronização concluída. Dados salvos em: %s", output_dir.resolve())


if __name__ == "__main__":
    main()
