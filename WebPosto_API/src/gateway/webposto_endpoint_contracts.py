"""
Contratos de Endpoints WebPosto
Define metadados e requisitos de cada endpoint da API WebPosto
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class WebPostoEndpointContract:
    """Contrato de um endpoint WebPosto"""
    
    path: str
    requires_date_range: bool = False
    requires_empresa_codigo: bool = False
    supports_pagination: bool = False
    payload_shape: Literal["array_root", "resultados", "data", "custom"] = "resultados"
    min_timeout_seconds: float = 10.0
    description: str = ""


# Endpoints que EXIGEM dataInicial e dataFinal
ENDPOINTS_REQUIRING_DATES = {
    "abastecimento",
    "financeiro",  # TITULO_PAGAR
    "titulo_receber",
    "movimento_conta",
    "transferencia_bancaria",
    "caixa",
    "caixa_apresentado",
    "caixa_rede",
    "caixa_apresentado_rede",
    "despesas_financeiro_rede",
    "venda",
    "venda_item",
    "venda_item_rede",
    "venda_forma_pagamento",
    "venda_forma_pagamento_rede",
    "cartao_rede",
    "nfce",
    "produto_estoque",
    "estoque_periodo",
    "lmc_rede",
}

# Endpoints que NÃO exigem datas (dados mestres/cadastrais)
ENDPOINTS_WITHOUT_DATES = {
    "empresas",
    "conta",
    "plano_de_contas",
    "produto",
    "produto_empresa",
    "produto_rede",
    "produto_empresa_rede",
    "produto_combustivel",
    "tanque",
    "funcionario",
    "analise_vendas_combustivel",  # Analítico, mas opcional
    "administradora_rede",
}

# Contratos detalhados por endpoint
WEBPOSTO_ENDPOINT_CONTRACTS: dict[str, WebPostoEndpointContract] = {
    "administradora_rede": WebPostoEndpointContract(
        path="/INTEGRACAO/CONSULTAR_ADMINISTRADORA_REDE",
        requires_date_range=False,
        supports_pagination=True,
        payload_shape="resultados",
        min_timeout_seconds=20.0,
        description="Cadastro de administradoras de cartão da rede",
    ),
    "cartao_rede": WebPostoEndpointContract(
        path="/INTEGRACAO/CONSULTAR_CARTAO_REDE",
        requires_date_range=True,
        supports_pagination=True,
        payload_shape="resultados",
        min_timeout_seconds=20.0,
        description="Movimentação detalhada de cartões da rede",
    ),
    "plano_de_contas": WebPostoEndpointContract(
        path="/INTEGRACAO/PLANO_DE_CONTAS",
        requires_date_range=False,
        supports_pagination=False,
        payload_shape="array_root",
        description="Cadastro oficial do plano de contas",
    ),
    # === ENDPOINTS FINANCEIROS (EXIGEM DATAS) ===
    "despesas_financeiro_rede": WebPostoEndpointContract(
        path="/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
        requires_date_range=True,
        requires_empresa_codigo=False,  # Endpoint de rede
        supports_pagination=False,
        payload_shape="array_root",
        min_timeout_seconds=20.0,
        description="Despesas financeiras consolidadas da rede",
    ),
    "financeiro": WebPostoEndpointContract(
        path="/INTEGRACAO/TITULO_PAGAR",
        requires_date_range=True,
        requires_empresa_codigo=False,
        supports_pagination=False,
        payload_shape="resultados",
        min_timeout_seconds=10.0,
        description="Títulos a pagar",
    ),
    "titulo_receber": WebPostoEndpointContract(
        path="/INTEGRACAO/TITULO_RECEBER",
        requires_date_range=True,
        requires_empresa_codigo=False,
        supports_pagination=False,
        payload_shape="resultados",
        min_timeout_seconds=10.0,
        description="Títulos a receber",
    ),
    "movimento_conta": WebPostoEndpointContract(
        path="/INTEGRACAO/MOVIMENTO_CONTA",
        requires_date_range=True,
        requires_empresa_codigo=False,
        supports_pagination=False,
        payload_shape="resultados",
        min_timeout_seconds=10.0,
        description="Movimentos de conta bancária",
    ),
    "transferencia_bancaria": WebPostoEndpointContract(
        path="/INTEGRACAO/TRANSFERENCIA_BANCARIA",
        requires_date_range=True,
        requires_empresa_codigo=False,
        supports_pagination=False,
        payload_shape="resultados",
        min_timeout_seconds=10.0,
        description="Transferências bancárias",
    ),
    
    # === ENDPOINTS DE CAIXA (EXIGEM DATAS) ===
    "caixa": WebPostoEndpointContract(
        path="/INTEGRACAO/CAIXA",
        requires_date_range=True,
        requires_empresa_codigo=False,
        supports_pagination=False,
        payload_shape="resultados",
        min_timeout_seconds=10.0,
        description="Fechamentos de caixa",
    ),
    "caixa_apresentado": WebPostoEndpointContract(
        path="/INTEGRACAO/CAIXA_APRESENTADO",
        requires_date_range=True,
        requires_empresa_codigo=False,
        supports_pagination=False,
        payload_shape="resultados",
        min_timeout_seconds=10.0,
        description="Caixas apresentados",
    ),
    "caixa_rede": WebPostoEndpointContract(
        path="/INTEGRACAO/CONSULTAR_CAIXA_REDE",
        requires_date_range=True,
        requires_empresa_codigo=False,
        supports_pagination=True,
        payload_shape="resultados",
        min_timeout_seconds=10.0,
        description="Caixas da rede consolidados",
    ),
    "caixa_apresentado_rede": WebPostoEndpointContract(
        path="/INTEGRACAO/CONSULTAR_CAIXA_APRESENTADO_REDE",
        requires_date_range=True,
        requires_empresa_codigo=False,
        supports_pagination=True,
        payload_shape="resultados",
        min_timeout_seconds=10.0,
        description="Caixas apresentados da rede",
    ),
    
    # === ENDPOINTS DE VENDAS (EXIGEM DATAS) ===
    "venda": WebPostoEndpointContract(
        path="/INTEGRACAO/VENDA",
        requires_date_range=True,
        requires_empresa_codigo=False,
        supports_pagination=False,
        payload_shape="resultados",
        min_timeout_seconds=20.0,
        description="Vendas",
    ),
    "venda_item": WebPostoEndpointContract(
        path="/INTEGRACAO/VENDA_ITEM",
        requires_date_range=True,
        requires_empresa_codigo=False,
        supports_pagination=True,
        payload_shape="resultados",
        min_timeout_seconds=20.0,
        description="Itens de venda",
    ),
    "venda_item_rede": WebPostoEndpointContract(
        path="/INTEGRACAO/CONSULTAR_VENDA_ITEM_REDE",
        requires_date_range=True,
        requires_empresa_codigo=False,
        supports_pagination=True,
        payload_shape="resultados",
        min_timeout_seconds=20.0,
        description="Itens de venda da rede",
    ),
    "venda_forma_pagamento": WebPostoEndpointContract(
        path="/INTEGRACAO/VENDA_FORMA_PAGAMENTO",
        requires_date_range=True,
        requires_empresa_codigo=False,
        supports_pagination=True,
        payload_shape="resultados",
        min_timeout_seconds=20.0,
        description="Formas de pagamento das vendas",
    ),
    "venda_forma_pagamento_rede": WebPostoEndpointContract(
        path="/INTEGRACAO/CONSULTAR_VENDA_FORMA_PAGAMENTO_REDE",
        requires_date_range=True,
        requires_empresa_codigo=False,
        supports_pagination=True,
        payload_shape="resultados",
        min_timeout_seconds=20.0,
        description="Formas de pagamento da rede",
    ),
    
    # === ENDPOINTS FISCAIS (EXIGEM DATAS) ===
    "nfce": WebPostoEndpointContract(
        path="/INTEGRACAO/NFCE",
        requires_date_range=True,
        requires_empresa_codigo=False,
        supports_pagination=False,
        payload_shape="resultados",
        min_timeout_seconds=20.0,
        description="Notas fiscais eletrônicas",
    ),
    "lmc_rede": WebPostoEndpointContract(
        path="/INTEGRACAO/CONSULTAR_LMC_REDE",
        requires_date_range=True,
        requires_empresa_codigo=False,
        supports_pagination=False,
        payload_shape="resultados",
        min_timeout_seconds=20.0,
        description="Leitura de medição de combustível (LMC)",
    ),
    
    # === ENDPOINTS DE ESTOQUE (EXIGEM DATAS) ===
    "abastecimento": WebPostoEndpointContract(
        path="/INTEGRACAO/ABASTECIMENTO",
        requires_date_range=True,
        requires_empresa_codigo=False,
        supports_pagination=False,
        payload_shape="resultados",
        min_timeout_seconds=10.0,
        description="Abastecimentos",
    ),
    "produto_estoque": WebPostoEndpointContract(
        path="/INTEGRACAO/PRODUTO_ESTOQUE",
        requires_date_range=True,
        requires_empresa_codigo=False,
        supports_pagination=False,
        payload_shape="resultados",
        min_timeout_seconds=20.0,
        description="Estoque de produtos",
    ),
    "estoque_periodo": WebPostoEndpointContract(
        path="/INTEGRACAO/ESTOQUE_PERIODO",
        requires_date_range=True,
        requires_empresa_codigo=False,
        supports_pagination=False,
        payload_shape="resultados",
        min_timeout_seconds=20.0,
        description="Movimento de estoque por período",
    ),
    
    # === ENDPOINTS MESTRES (NÃO EXIGEM DATAS) ===
    "empresas": WebPostoEndpointContract(
        path="/INTEGRACAO/EMPRESAS",
        requires_date_range=False,
        requires_empresa_codigo=False,
        supports_pagination=False,
        payload_shape="resultados",
        min_timeout_seconds=10.0,
        description="Lista de empresas",
    ),
    "conta": WebPostoEndpointContract(
        path="/INTEGRACAO/CONTA",
        requires_date_range=False,
        requires_empresa_codigo=False,
        supports_pagination=False,
        payload_shape="resultados",
        min_timeout_seconds=10.0,
        description="Contas bancárias",
    ),
    "produto": WebPostoEndpointContract(
        path="/INTEGRACAO/PRODUTO",
        requires_date_range=False,
        requires_empresa_codigo=False,
        supports_pagination=False,
        payload_shape="resultados",
        min_timeout_seconds=10.0,
        description="Produtos",
    ),
    "produto_empresa": WebPostoEndpointContract(
        path="/INTEGRACAO/PRODUTO_EMPRESA",
        requires_date_range=False,
        requires_empresa_codigo=False,
        supports_pagination=False,
        payload_shape="resultados",
        min_timeout_seconds=10.0,
        description="Produtos por empresa",
    ),
    "produto_rede": WebPostoEndpointContract(
        path="/INTEGRACAO/PRODUTO_REDE",
        requires_date_range=False,
        requires_empresa_codigo=False,
        supports_pagination=False,
        payload_shape="resultados",
        min_timeout_seconds=10.0,
        description="Produtos da rede",
    ),
    "produto_empresa_rede": WebPostoEndpointContract(
        path="/INTEGRACAO/PRODUTO_EMPRESA_REDE",
        requires_date_range=False,
        requires_empresa_codigo=False,
        supports_pagination=False,
        payload_shape="resultados",
        min_timeout_seconds=10.0,
        description="Produtos por empresa (rede)",
    ),
    "produto_combustivel": WebPostoEndpointContract(
        path="/INTEGRACAO/PRODUTO_COMBUSTIVEL",
        requires_date_range=False,
        requires_empresa_codigo=False,
        supports_pagination=False,
        payload_shape="resultados",
        min_timeout_seconds=10.0,
        description="Produtos combustíveis",
    ),
    "tanque": WebPostoEndpointContract(
        path="/INTEGRACAO/TANQUE",
        requires_date_range=False,
        requires_empresa_codigo=False,
        supports_pagination=False,
        payload_shape="resultados",
        min_timeout_seconds=10.0,
        description="Tanques de combustível",
    ),
    "funcionario": WebPostoEndpointContract(
        path="/INTEGRACAO/FUNCIONARIO",
        requires_date_range=False,
        requires_empresa_codigo=False,
        supports_pagination=False,
        payload_shape="resultados",
        min_timeout_seconds=20.0,
        description="Funcionários",
    ),
    
    # === ENDPOINT ANALÍTICO (OPCIONAL DATAS) ===
    "analise_vendas_combustivel": WebPostoEndpointContract(
        path="/INTEGRACAO/CONSULTAR_ANALISE_VENDAS_COMBUSTIVEL",
        requires_date_range=False,  # Opcional, mas pode causar timeout
        requires_empresa_codigo=False,
        supports_pagination=False,
        payload_shape="custom",
        min_timeout_seconds=20.0,
        description="Análise de vendas de combustível (pode retornar payload grande)",
    ),
}


def get_endpoint_contract(endpoint_key: str) -> WebPostoEndpointContract | None:
    """Retorna o contrato de um endpoint"""
    return WEBPOSTO_ENDPOINT_CONTRACTS.get(endpoint_key)


def endpoint_requires_dates(endpoint_key: str) -> bool:
    """Verifica se um endpoint exige dataInicial e dataFinal"""
    contract = get_endpoint_contract(endpoint_key)
    return contract.requires_date_range if contract else False


def get_endpoints_by_date_requirement() -> tuple[set[str], set[str]]:
    """Retorna dois sets: (endpoints que exigem datas, endpoints que não exigem)"""
    requires = set()
    not_requires = set()
    
    for key, contract in WEBPOSTO_ENDPOINT_CONTRACTS.items():
        if contract.requires_date_range:
            requires.add(key)
        else:
            not_requires.add(key)
    
    return requires, not_requires
