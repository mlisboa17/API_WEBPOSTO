"""
Metadados de filtros disponíveis no cockpit e na API Quality.
"""

from __future__ import annotations

from typing import Any

from src.domain.adelaide.fuel_catalog import FUEL_CATALOG


def build_filtros_meta() -> dict[str, Any]:
    combustiveis = [
        {"codigo": cod, "nome": nome, "combustivel": True}
        for cod, nome in sorted(FUEL_CATALOG.items(), key=lambda x: x[1])
    ]
    return {
        "combustiveis_catalogo": combustiveis,
        "filtros_abastecimento": {
            "dataInicial": "YYYY-MM-DD (obrigatório na API)",
            "dataFinal": "YYYY-MM-DD (obrigatório na API)",
            "filial": "lista de códigos de filial (opcional)",
            "bico": "número do bico (opcional)",
            "pagina": "paginação (opcional)",
            "tamanhoPagina": "tamanho da página (opcional)",
        },
        "filtros_cockpit": {
            "periodo": ["hoje", "7d", "mensal"],
            "data_inicial": "sobrescreve preset de período",
            "data_final": "sobrescreve preset de período",
            "tipo_produto": ["todos", "combustivel", "codigo:<id>"],
            "filial": "CSV ex: 1,2",
            "excluir_afericao": "boolean, default true",
            "grupo": "filtro catálogo PRODUTO (grupoCodigo)",
            "descricao": "filtro catálogo PRODUTO (nome)",
        },
        "filtros_produto": {
            "pagina": "1-based",
            "tamanhoPagina": "limite por página",
            "nome": "busca por descrição",
            "grupoCodigo": "código do grupo (único)",
            "grupos": "CSV de códigos de grupo",
            "situacao": ["todos", "ativos", "inativos"],
            "tipo_produto": ["todos", "combustivel", "C", "P", "S", "U", "I", "O", "K", "8"],
            "subgrupo": "subGrupo1Codigo | subGrupo2Codigo | subGrupo3Codigo (Quality)",
        },
        "filtros_caixa": {
            "dataInicial": "YYYY-MM-DD",
            "dataFinal": "YYYY-MM-DD",
        },
    }
