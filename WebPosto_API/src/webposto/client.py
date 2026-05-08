"""
Cliente principal WebPosto.

Uso rápido:
    from webposto import WebPostoClient, WebPostoConfig
    from datetime import date

    config = WebPostoConfig.from_env()  # lê WEBPOSTO_CHAVE do .env
    client = WebPostoClient(config)

    # Abastecimentos de hoje
    abastecimentos = client.abastecimento.listar(
        data_inicial=date.today(),
        data_final=date.today(),
    )

    # Títulos a receber em aberto
    titulos = client.financeiro.listar_titulos_receber(
        data_inicial=date(2025, 1, 1),
        data_final=date.today(),
        situacao="ABERTO",
    )
"""

import logging

from .config import WebPostoConfig
from .http import HTTPClient
from .endpoints.abastecimento import AbastecimentoEndpoints
from .endpoints.clientes import ClientesEndpoints
from .endpoints.produtos import ProdutosEndpoints
from .endpoints.financeiro import FinanceiroEndpoints
from .endpoints.combustivel import CombustivelEndpoints
from .endpoints.relatorios import RelatoriosEndpoints
from .endpoints.integracoes import IntegracoesEndpoints

logger = logging.getLogger(__name__)


class WebPostoClient:
    """
    Cliente WebPosto — ponto de entrada único para toda a API.

    Attributes:
        abastecimento: Endpoints de abastecimento e encerrantes
        clientes: Endpoints de clientes e frota
        produtos: Endpoints de produtos, preços e estoque
        financeiro: Endpoints financeiros (títulos, caixa, transferências)
        combustivel: Endpoints de pedido de combustível e LMC
        relatorios: Endpoints de relatórios gerenciais
        integracoes: Demais endpoints (vendas, NF, pedidos de compra, etc.)
    """

    def __init__(self, config: WebPostoConfig):
        """
        Inicializa o cliente.

        Args:
            config: Configuração com chave de integração e demais parâmetros.
                    Use WebPostoConfig.from_env() para carregar do .env.
        """
        if not config.chave:
            raise ValueError("config.chave não pode ser vazia")

        self._config = config
        self._http = HTTPClient(config)

        # Endpoints organizados por domínio
        self.abastecimento = AbastecimentoEndpoints(self._http)
        self.clientes = ClientesEndpoints(self._http)
        self.produtos = ProdutosEndpoints(self._http)
        self.financeiro = FinanceiroEndpoints(self._http)
        self.combustivel = CombustivelEndpoints(self._http)
        self.relatorios = RelatoriosEndpoints(self._http)
        self.integracoes = IntegracoesEndpoints(self._http)

        logger.info(
            "WebPostoClient inicializado | base_url=%s | empresa=%s",
            config.base_url,
            config.empresa_codigo or "não definida",
        )

    @classmethod
    def from_env(cls) -> "WebPostoClient":
        """Atalho para inicializar a partir de variáveis de ambiente."""
        return cls(WebPostoConfig.from_env())

    def healthcheck(self) -> bool:
        """
        Verifica se a API está acessível e a chave é válida.

        Returns:
            True se a conexão for bem-sucedida.

        Raises:
            AuthError: Se a chave de integração for inválida.
            ConnectionError: Se o servidor não estiver acessível.
        """
        try:
            # Usa endpoint leve para validar conexão e autenticação
            self._http.get("/INTEGRACAO/FILIAL", {"pagina": 0, "tamanhoPagina": 1})
            logger.info("Healthcheck OK")
            return True
        except Exception as e:
            logger.error("Healthcheck falhou: %s", e)
            raise
