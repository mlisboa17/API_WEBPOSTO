"""
Endpoints de Relatórios (grupo: Integração Relatórios).
"""

from datetime import date
from typing import Dict, List, Optional


class RelatoriosEndpoints:
    """
    Endpoints de relatórios gerenciais.

    Endpoints cobertos:
        GET /INTEGRACAO/RELATORIO/VENDA_PRODUTO
        GET /INTEGRACAO/RELATORIO/VENDA_COMBUSTIVEL
        GET /INTEGRACAO/RELATORIO/RESUMO_VENDAS
        GET /INTEGRACAO/RELATORIO/ESTOQUE
        (+ outros conforme especificação)
    """

    def __init__(self, http):
        self._http = http

    def vendas_produto(
        self,
        data_inicial: date,
        data_final: date,
        filial: Optional[List[int]] = None,
        produto: Optional[List[int]] = None,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """
        Relatório de vendas por produto.

        Args:
            data_inicial: Data de início
            data_final: Data de fim
            filial: Lista de filiais (opcional)
            produto: Lista de códigos de produto (opcional)
        """
        params = {
            "dataInicial": data_inicial.isoformat(),
            "dataFinal": data_final.isoformat(),
            "filial": filial,
            "produto": produto,
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina,
        }
        return self._http.get("/INTEGRACAO/RELATORIO/VENDA_PRODUTO", params)

    def vendas_combustivel(
        self,
        data_inicial: date,
        data_final: date,
        filial: Optional[List[int]] = None,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Relatório de vendas de combustível."""
        params = {
            "dataInicial": data_inicial.isoformat(),
            "dataFinal": data_final.isoformat(),
            "filial": filial,
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina,
        }
        return self._http.get("/INTEGRACAO/RELATORIO/VENDA_COMBUSTIVEL", params)

    def resumo_vendas(
        self,
        data_inicial: date,
        data_final: date,
        filial: Optional[List[int]] = None,
    ) -> Dict:
        """Resumo de vendas consolidado."""
        params = {
            "dataInicial": data_inicial.isoformat(),
            "dataFinal": data_final.isoformat(),
            "filial": filial,
        }
        return self._http.get("/INTEGRACAO/RELATORIO/RESUMO_VENDAS", params)

    def estoque(
        self,
        filial: Optional[List[int]] = None,
        produto: Optional[List[int]] = None,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Relatório de estoque atual."""
        params = {
            "filial": filial,
            "produto": produto,
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina,
        }
        return self._http.get("/INTEGRACAO/RELATORIO/ESTOQUE", params)
