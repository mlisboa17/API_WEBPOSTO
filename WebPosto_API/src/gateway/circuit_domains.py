"""F08.0 — Domínios de circuit breaker para reset administrativo."""
from __future__ import annotations

FINANCIAL_ENDPOINT_KEYS = frozenset(
    {
        "despesas_financeiro_rede",
        "financeiro",
        "titulo_receber",
        "movimento_conta",
        "transferencia_bancaria",
        "empresas",
        "conta",
        "caixa",
        "caixa_apresentado",
        "caixa_rede",
        "caixa_apresentado_rede",
    }
)

FUEL_ENDPOINT_KEYS = frozenset(
    {
        "abastecimento",
        "analise_vendas_combustivel",
        "produto_combustivel",
        "tanque",
        "lmc_rede",
        "estoque_periodo",
        "produto_estoque",
    }
)

FISCAL_ENDPOINT_KEYS = frozenset(
    {
        "nfce",
        "venda",
        "venda_item",
        "venda_item_rede",
        "venda_forma_pagamento",
        "venda_forma_pagamento_rede",
    }
)

SALES_ENDPOINT_KEYS = frozenset(
    {
        "venda",
        "venda_item",
        "venda_item_rede",
        "venda_forma_pagamento",
        "venda_forma_pagamento_rede",
    }
)

STOCK_ENDPOINT_KEYS = frozenset(
    {
        "produto_estoque",
        "produto",
        "tanque",
        "estoque_periodo",
    }
)

CIRCUIT_SCOPES = {
    "financial": FINANCIAL_ENDPOINT_KEYS,
    "fuel": FUEL_ENDPOINT_KEYS,
    "fiscal": FISCAL_ENDPOINT_KEYS,
    "sales": SALES_ENDPOINT_KEYS,
    "stock": STOCK_ENDPOINT_KEYS,
    "global": FINANCIAL_ENDPOINT_KEYS | FUEL_ENDPOINT_KEYS | FISCAL_ENDPOINT_KEYS | SALES_ENDPOINT_KEYS | STOCK_ENDPOINT_KEYS,
}
