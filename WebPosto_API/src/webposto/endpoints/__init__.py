from .abastecimento import AbastecimentoEndpoints
from .clientes import ClientesEndpoints
from .produtos import ProdutosEndpoints
from .financeiro import FinanceiroEndpoints
from .combustivel import CombustivelEndpoints
from .relatorios import RelatoriosEndpoints
from .integracoes import IntegracoesEndpoints

__all__ = [
    "AbastecimentoEndpoints",
    "ClientesEndpoints",
    "ProdutosEndpoints",
    "FinanceiroEndpoints",
    "CombustivelEndpoints",
    "RelatoriosEndpoints",
    "IntegracoesEndpoints",
]
