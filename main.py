"""Exemplo de uso do Logos Auditoria."""

import asyncio
import logging

from config import settings
from services import FinanceiroService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Fluxo de auditoria completo."""

    logger.info(
        "WebPosto base URL: %s", settings.WEBPOSTO_BASE_URL or "(não configurada)"
    )

    # IDs de exemplo (numéricos, conforme WebPosto)
    unidade_real = 1
    unidade_casa_caiada = 2
    unidade_vip = 3

    async with FinanceiroService() as client:
        try:
            # 1. Obter fechamento de caixa
            logger.info("=== FECHAMENTO DE CAIXA ===")
            fechamento = await client.get_fechamento_caixa(unidade_real)
            print(f"Unidade: {fechamento.unidade}")
            print(f"Faturamento Total: R$ {fechamento.faturamento_total:.2f}")
            print(f"Despesas: R$ {fechamento.despesas_total:.2f}")
            print(f"Saldo em Espécie: R$ {fechamento.saldo_especie:.2f}")
            print(f"Quebra Total: R$ {fechamento.quebra_total:.2f}\n")

            # 2. Movimentação por espécie
            logger.info("=== MOVIMENTAÇÃO POR ESPÉCIE ===")
            movimentacao = await client.get_movimentacao_especie(unidade_real)
            for mov in movimentacao:
                print(f"{mov.modalidade}:")
                print(f"  Sistema: R$ {mov.valor_sistematico:.2f}")
                print(f"  Informado: R$ {mov.valor_informado:.2f}")
                print(
                    f"  Diferença: R$ {mov.diferenca:.2f} ({mov.percentual_desvio:.1f}%)\n"
                )

            # 3. Gerar insights de auditoria
            logger.info("=== INSIGHTS DO AUDITOR ===")
            insights = await client.gerar_insights_auditoria(
                unidade_real, unidades_comparacao=[unidade_casa_caiada, unidade_vip]
            )

            for insight in insights:
                print(f"[{insight.severidade.upper()}] {insight.mensagem}")
                if insight.desvio_percentual:
                    print(f"         Desvio: {insight.desvio_percentual:.1f}%")

            print("\n✓ Auditoria concluída com sucesso")

        except Exception as e:
            logger.error(f"Erro na auditoria: {str(e)}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
