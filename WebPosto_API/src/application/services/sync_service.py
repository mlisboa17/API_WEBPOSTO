from src.application.services.cliente_service import ClienteService
from src.infrastructure.event_bus.redis_event_bus import RedisEventBus
from src.infrastructure.webposto.client import WebPostoClient
from src.shared.logger import get_logger

logger = get_logger(__name__)


class SyncService:
    """Serviço de Sincronização com webPosto API."""

    def __init__(
        self,
        webposto_client: WebPostoClient,
        cliente_service: ClienteService,
        event_bus: RedisEventBus,
    ):
        self.webposto_client = webposto_client
        self.cliente_service = cliente_service
        self.event_bus = event_bus

    async def sync_clientes(self) -> dict:
        """Sincroniza clientes da API webPosto."""
        logger.info("Iniciando sincronização de clientes")

        try:
            # Busca clientes da API
            clientes_dados = await self.webposto_client.get_clientes()
            total_recebidos = len(clientes_dados)

            criados = 0
            atualizados = 0
            erros = 0

            for dado in clientes_dados:
                try:
                    webposto_id = dado.get("id")
                    cnpj = dado.get("cnpj")
                    nome = dado.get("nome")

                    if not webposto_id or not cnpj:
                        logger.warning(f"Dados incompletos do cliente: {dado}")
                        erros += 1
                        continue

                    # Verifica se já existe
                    cliente_existente = await self.cliente_service.obter_por_cnpj(cnpj)

                    if cliente_existente:
                        # Atualiza existente
                        await self.cliente_service.atualizar_cliente(
                            cliente_existente.id,
                            {"nome": nome, "cnpj": cnpj},
                        )
                        atualizados += 1
                    else:
                        # Cria novo
                        await self.cliente_service.criar_cliente(
                            {"nome": nome, "cnpj": cnpj, "webposto_id": webposto_id}
                        )
                        criados += 1

                except Exception as e:
                    logger.error(f"Erro ao sincronizar cliente {webposto_id}: {str(e)}")
                    erros += 1

            resultado = {
                "total_recebidos": total_recebidos,
                "criados": criados,
                "atualizados": atualizados,
                "erros": erros,
            }

            logger.info(f"Sincronização concluída: {resultado}")
            return resultado

        except Exception as e:
            logger.error(f"Erro na sincronização de clientes: {str(e)}")
            raise

    async def sync_abastecimentos(self) -> dict:
        """Sincroniza abastecimentos da API webPosto."""
        logger.info("Iniciando sincronização de abastecimentos")

        try:
            abastecimentos_dados = await self.webposto_client.get_abastecimentos()
            total = len(abastecimentos_dados)

            logger.info(f"Sincronização de abastecimentos: {total} registros recebidos")
            return {"total": total}

        except Exception as e:
            logger.error(f"Erro na sincronização de abastecimentos: {str(e)}")
            raise

    async def sync_financeiro(self) -> dict:
        """Sincroniza dados financeiros da API webPosto."""
        logger.info("Iniciando sincronização de financeiro")

        try:
            financeiro_dados = await self.webposto_client.get_financeiro()
            total = len(financeiro_dados)

            logger.info(f"Sincronização de financeiro: {total} registros recebidos")
            return {"total": total}

        except Exception as e:
            logger.error(f"Erro na sincronização de financeiro: {str(e)}")
            raise

    async def sync_caixa(self) -> dict:
        """Sincroniza movimentos de caixa da API webPosto."""
        logger.info("Iniciando sincronização de caixa")

        try:
            caixa_dados = await self.webposto_client.get_caixa()
            total = len(caixa_dados)

            logger.info(f"Sincronização de caixa: {total} registros recebidos")
            return {"total": total}

        except Exception as e:
            logger.error(f"Erro na sincronização de caixa: {str(e)}")
            raise

    async def full_sync(self) -> dict:
        """Sincroniza tudo: clientes, abastecimentos, financeiro, caixa."""
        logger.info("Iniciando sincronização completa")

        try:
            resultados = {
                "clientes": await self.sync_clientes(),
                "abastecimentos": await self.sync_abastecimentos(),
                "financeiro": await self.sync_financeiro(),
                "caixa": await self.sync_caixa(),
            }

            logger.info(f"Sincronização completa concluída: {resultados}")
            return resultados

        except Exception as e:
            logger.error(f"Erro na sincronização completa: {str(e)}")
            raise
