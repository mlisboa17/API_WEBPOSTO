"""
Endpoints gerais de integração (demais endpoints não categorizados).
"""

from datetime import date
from typing import Dict, List, Optional


class IntegracoesEndpoints:
    """
    Endpoints gerais: vendas, notas fiscais, pedidos compras, usuários, etc.

    Endpoints cobertos:
        GET  /INTEGRACAO/VENDA
        GET  /INTEGRACAO/VENDA_REDE
        GET  /INTEGRACAO/NOTA_FISCAL_ENTRADA
        GET  /INTEGRACAO/NOTA_FISCAL_SAIDA
        GET  /INTEGRACAO/PEDIDO_COMPRAS
        POST /INTEGRACAO/PEDIDO_COMPRAS
        GET  /INTEGRACAO/USUARIO
        GET  /INTEGRACAO/USUARIO_EMPRESA_REDE
        GET  /INTEGRACAO/FILIAL
        GET  /INTEGRACAO/ADMINISTRADORA
        GET  /INTEGRACAO/ADIANTAMENTO_FORNECEDOR
        GET  /INTEGRACAO/VEICULO
        GET  /INTEGRACAO/PRAZO_TABELA_PRECO
        POST /INTEGRACAO/PRAZO_TABELA_PRECO/{id}/ITEM
        POST /INTEGRACAO/AUTORIZA_PAGAMENTO_ABASTECIMENTO
        POST /INTEGRACAO/PERSISTIR_CARTAO_DTO
        POST /INTEGRACAO/PEDIDO_COMBUSTIVEL/PEDIDO/{id}/FATURAR  (ver combustivel.py)
    """

    def __init__(self, http):
        self._http = http

    # ── VENDAS ────────────────────────────────────────────────────────────────

    def listar_vendas(
        self,
        data_inicial: date,
        data_final: date,
        filial: Optional[List[int]] = None,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
        ultimo_codigo: Optional[int] = None,
    ) -> List[Dict]:
        """Lista vendas no período."""
        params = {
            "dataInicial": data_inicial.isoformat(),
            "dataFinal": data_final.isoformat(),
            "filial": filial,
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina,
        }
        if ultimo_codigo is not None:
            params["ultimoCodigo"] = ultimo_codigo
        return self._http.get("/INTEGRACAO/VENDA", params)

    def listar_vendas_rede(
        self,
        data_inicial: date,
        data_final: date,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Lista vendas em rede (multi-filial)."""
        params = {
            "dataInicial": data_inicial.isoformat(),
            "dataFinal": data_final.isoformat(),
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina,
        }
        return self._http.get("/INTEGRACAO/VENDA_REDE", params)

    # ── GRUPOS DE PRODUTO ─────────────────────────────────────────────────────

    def listar_grupos_produto(
        self,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Lista grupos de produto (código + nome, ex.: COMBUSTIVEIS)."""
        params = {"pagina": pagina, "tamanhoPagina": tamanho_pagina}
        return self._http.get("/INTEGRACAO/GRUPO", params)

    def listar_grupos_produto_meta(
        self,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Metadados de grupos (collection oficial Postman — GRUPO_META)."""
        params = {"pagina": pagina, "tamanhoPagina": tamanho_pagina}
        return self._http.get("/INTEGRACAO/GRUPO_META", params)

    # ── NOTAS FISCAIS ─────────────────────────────────────────────────────────

    def listar_nf_entrada(
        self,
        data_inicial: date,
        data_final: date,
        filial: Optional[List[int]] = None,
        distribuidora: Optional[str] = None,
        modelo_documento: Optional[str] = None,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Lista notas fiscais de entrada."""
        params = {
            "dataInicial": data_inicial.isoformat(),
            "dataFinal": data_final.isoformat(),
            "filial": filial,
            "distribuidora": distribuidora,
            "modeloDocumentoFiscal": modelo_documento,
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina,
        }
        return self._http.get("/INTEGRACAO/NOTA_FISCAL_ENTRADA", params)

    def listar_nf_saida(
        self,
        data_inicial: date,
        data_final: date,
        filial: Optional[List[int]] = None,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Lista notas fiscais de saída."""
        params = {
            "dataInicial": data_inicial.isoformat(),
            "dataFinal": data_final.isoformat(),
            "filial": filial,
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina,
        }
        return self._http.get("/INTEGRACAO/NOTA_FISCAL_SAIDA", params)

    # ── PEDIDOS DE COMPRA ────────────────────────────────────────────────────

    def listar_pedidos_compra(
        self,
        data_inicial: Optional[date] = None,
        data_final: Optional[date] = None,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Lista pedidos de compra."""
        params = {
            "dataInicial": data_inicial.isoformat() if data_inicial else None,
            "dataFinal": data_final.isoformat() if data_final else None,
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina,
        }
        return self._http.get("/INTEGRACAO/PEDIDO_COMPRAS", params)

    def criar_pedido_compra(self, body: Dict) -> Dict:
        """Cria pedido de compra."""
        return self._http.post("/INTEGRACAO/PEDIDO_COMPRAS", body)

    # ── USUÁRIOS / FILIAIS ────────────────────────────────────────────────────

    def listar_usuarios(
        self,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Lista usuários cadastrados."""
        params = {"pagina": pagina, "tamanhoPagina": tamanho_pagina}
        return self._http.get("/INTEGRACAO/USUARIO", params)

    def listar_filiais(
        self,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Lista filiais."""
        params = {"pagina": pagina, "tamanhoPagina": tamanho_pagina}
        return self._http.get("/INTEGRACAO/FILIAL", params)

    def listar_administradoras(
        self,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Lista administradoras de cartão."""
        params = {"pagina": pagina, "tamanhoPagina": tamanho_pagina}
        return self._http.get("/INTEGRACAO/ADMINISTRADORA", params)

    def listar_veiculos(
        self,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Lista veículos cadastrados."""
        params = {"pagina": pagina, "tamanhoPagina": tamanho_pagina}
        return self._http.get("/INTEGRACAO/VEICULO", params)

    def listar_adiantamento_fornecedor(
        self,
        data_inicial: date,
        data_final: date,
        filial: Optional[List[int]] = None,
    ) -> List[Dict]:
        """Lista adiantamentos a fornecedores."""
        params = {
            "dataInicial": data_inicial.isoformat(),
            "dataFinal": data_final.isoformat(),
            "filial": filial,
        }
        return self._http.get("/INTEGRACAO/ADIANTAMENTO_FORNECEDOR", params)

    # ── TABELA DE PREÇO / PRAZO ───────────────────────────────────────────────

    def listar_prazo_tabela_preco(
        self,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Lista prazos de tabela de preços."""
        params = {"pagina": pagina, "tamanhoPagina": tamanho_pagina}
        return self._http.get("/INTEGRACAO/PRAZO_TABELA_PRECO", params)

    def criar_item_prazo_tabela_preco(self, tabela_id: int, body: Dict) -> None:
        """Cria item em uma tabela de prazo de preço."""
        self._http.post(f"/INTEGRACAO/PRAZO_TABELA_PRECO/{tabela_id}/ITEM", body)

    # ── CARTÃO / PAGAMENTO ────────────────────────────────────────────────────

    def autorizar_pagamento_abastecimento(self, body: Dict) -> Dict:
        """Autoriza pagamento de abastecimento."""
        return self._http.post("/INTEGRACAO/AUTORIZA_PAGAMENTO_ABASTECIMENTO", body)

    def persistir_cartao(self, body: Dict) -> Dict:
        """Persiste dados de cartão."""
        return self._http.post("/INTEGRACAO/PERSISTIR_CARTAO_DTO", body)
