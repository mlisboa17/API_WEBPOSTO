"""
Endpoints de Abastecimento.
"""

from datetime import date
from typing import Dict, List, Optional


class AbastecimentoEndpoints:
    """
    Endpoints relacionados a abastecimentos.

    Endpoints cobertos:
        GET /INTEGRACAO/ABASTECIMENTO
        GET /INTEGRACAO/ABASTECIMENTO_ENCERRANTE
        GET /INTEGRACAO/ABASTECIMENTO_DIVERGENCIA
        POST /INTEGRACAO/REAJUSTAR_ESTOQUE_PRODUTO_COMBUSTIVEL
        PUT /INTEGRACAO/REAJUSTAR_ESTOQUE_PRODUTO_COMBUSTIVEL
    """

    def __init__(self, http):
        self._http = http

    def listar(
        self,
        data_inicial: date,
        data_final: date,
        filial: Optional[List[int]] = None,
        bico: Optional[int] = None,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
        ultimo_codigo: Optional[str] = None,
    ) -> List[Dict]:
        """
        Lista abastecimentos no período informado.

        Args:
            data_inicial: Data de início (YYYY-MM-DD)
            data_final: Data de fim (YYYY-MM-DD)
            filial: Lista de códigos de filial (opcional)
            bico: Número do bico (opcional)
            pagina: Número da página para paginação (opcional)
            tamanho_pagina: Tamanho da página (opcional)

        Returns:
            Lista de abastecimentos
        """
        params = {
            "dataInicial": data_inicial.isoformat(),
            "dataFinal": data_final.isoformat(),
            "filial": filial,
            "bico": bico,
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina,
        }
        if ultimo_codigo not in (None, ""):
            params["ultimoCodigo"] = ultimo_codigo
        return self._http.get("/INTEGRACAO/ABASTECIMENTO", params)

    def listar_encerrante(
        self,
        data_inicial: date,
        data_final: date,
        filial: Optional[List[int]] = None,
    ) -> List[Dict]:
        """
        Lista encerrantes de abastecimento no período.

        Args:
            data_inicial: Data de início
            data_final: Data de fim
            filial: Lista de códigos de filial (opcional)
        """
        params = {
            "dataInicial": data_inicial.isoformat(),
            "dataFinal": data_final.isoformat(),
            "filial": filial,
        }
        return self._http.get("/INTEGRACAO/ABASTECIMENTO_ENCERRANTE", params)

    def listar_divergencia(
        self,
        data_inicial: date,
        data_final: date,
        filial: Optional[List[int]] = None,
    ) -> List[Dict]:
        """
        Lista divergências de abastecimento no período.
        """
        params = {
            "dataInicial": data_inicial.isoformat(),
            "dataFinal": data_final.isoformat(),
            "filial": filial,
        }
        return self._http.get("/INTEGRACAO/ABASTECIMENTO_DIVERGENCIA", params)

    def reajustar_estoque_combustivel(self, body: Dict) -> None:
        """
        Reajusta estoque de produto combustível.

        Args:
            body: Payload conforme schema ReajustarProdutoCombustivel
        """
        self._http.put("/INTEGRACAO/REAJUSTAR_ESTOQUE_PRODUTO_COMBUSTIVEL", body)
