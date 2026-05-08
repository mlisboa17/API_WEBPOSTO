"""
Endpoints de Pedido de Combustível.
"""

from datetime import date
from typing import Dict, List, Optional


class CombustivelEndpoints:
    """
    Endpoints de pedidos de combustível (grupo: Integração Pedido Combustível).

    Endpoints cobertos:
        POST /INTEGRACAO/PEDIDO_COMBUSTIVEL/PEDIDO
        GET  /INTEGRACAO/PEDIDO_COMBUSTIVEL/PEDIDO
        POST /INTEGRACAO/PEDIDO_COMBUSTIVEL/PEDIDO/{id}/FATURAR
        POST /INTEGRACAO/PEDIDO_COMBUSTIVEL/CLIENTE
        PUT  /INTEGRACAO/PEDIDO_COMBUSTIVEL/PEDIDO/{id}/RECEBER_TITULO_EM_CARTAO
        GET  /INTEGRACAO/APRIX_CUSTO
        GET  /INTEGRACAO/LMC
        GET  /INTEGRACAO/DISTRIBUIDORA
    """

    def __init__(self, http):
        self._http = http

    # ── PEDIDO DE COMBUSTÍVEL ─────────────────────────────────────────────────

    def criar_pedido(self, body: Dict) -> Dict:
        """
        Cria um pedido de combustível.

        Args:
            body: Dados do pedido conforme schema IntegracaoPedidoCombustivel
        """
        return self._http.post("/INTEGRACAO/PEDIDO_COMBUSTIVEL/PEDIDO", body)

    def listar_pedidos(
        self,
        data_inicial: Optional[date] = None,
        data_final: Optional[date] = None,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Lista pedidos de combustível."""
        params = {
            "dataInicial": data_inicial.isoformat() if data_inicial else None,
            "dataFinal": data_final.isoformat() if data_final else None,
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina,
        }
        return self._http.get("/INTEGRACAO/PEDIDO_COMBUSTIVEL/PEDIDO", params)

    def faturar_pedido(self, pedido_id: int, body: Optional[Dict] = None) -> None:
        """
        Fatura um pedido de combustível.

        Args:
            pedido_id: ID do pedido
            body: Dados de faturamento (opcional)
        """
        self._http.post(
            f"/INTEGRACAO/PEDIDO_COMBUSTIVEL/PEDIDO/{pedido_id}/FATURAR", body
        )

    def receber_titulo_cartao(self, pedido_id: int, body: Dict) -> None:
        """
        Recebe título de pedido de combustível em cartão.

        Args:
            pedido_id: ID do pedido
            body: Dados do cartão
        """
        self._http.put(
            f"/INTEGRACAO/PEDIDO_COMBUSTIVEL/PEDIDO/{pedido_id}/RECEBER_TITULO_EM_CARTAO",
            body,
        )

    def vincular_cliente_pedido(self, body: Dict) -> None:
        """Vincula cliente a pedido de combustível."""
        self._http.post("/INTEGRACAO/PEDIDO_COMBUSTIVEL/CLIENTE", body)

    # ── APRIX / LMC ───────────────────────────────────────────────────────────

    def listar_aprix_custo(
        self,
        data_inicial: Optional[date] = None,
        data_final: Optional[date] = None,
        filial: Optional[List[int]] = None,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Lista APRIX de custo de combustível."""
        params = {
            "dataInicial": data_inicial.isoformat() if data_inicial else None,
            "dataFinal": data_final.isoformat() if data_final else None,
            "filial": filial,
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina,
        }
        return self._http.get("/INTEGRACAO/APRIX_CUSTO", params)

    def listar_lmc(
        self,
        data_inicial: date,
        data_final: date,
        filial: Optional[List[int]] = None,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """
        Lista LMC (Livro de Movimentação de Combustíveis).

        Args:
            data_inicial: Data de início
            data_final: Data de fim
            filial: Código(s) de filial
        """
        params = {
            "dataInicial": data_inicial.isoformat(),
            "dataFinal": data_final.isoformat(),
            "filial": filial,
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina,
        }
        return self._http.get("/INTEGRACAO/LMC", params)

    def listar_distribuidoras(
        self,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Lista distribuidoras de combustível."""
        params = {"pagina": pagina, "tamanhoPagina": tamanho_pagina}
        return self._http.get("/INTEGRACAO/DISTRIBUIDORA", params)
