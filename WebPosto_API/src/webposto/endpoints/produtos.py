"""
Endpoints de Produtos e Estoque.
"""

from typing import Dict, List, Optional


class ProdutosEndpoints:
    """
    Endpoints de produtos, preços e estoque.

    Endpoints cobertos:
        GET  /INTEGRACAO/PRODUTO
        POST /INTEGRACAO/PRODUTO
        PUT  /INTEGRACAO/ALTERAR_PRODUTO/{id}
        POST /INTEGRACAO/REAJUSTAR_PRODUTO
        POST /INTEGRACAO/TROCA_PRECO_PRODUTO
        POST /INTEGRACAO/ALTERACAO_PRECO_COMBUSTIVEL  (legado)
        POST /INTEGRACAO/TROCA_PRECO_COMBUSTIVEL
        POST /INTEGRACAO/PRODUTO_INVENTARIO
        GET  /INTEGRACAO/LISTA_DE_ITENS  (legado — use PRODUTO; muitas chaves retornam 401)
        GET  /INTEGRACAO/PRODUTO_INVENTARIO_ITENS
        GET  /INTEGRACAO/RETORNO_CADASTRO_PRODUTO
        POST /INTEGRACAO/PRODUTO_COMISSAO
        GET  /INTEGRACAO/INTEGRACAO_PRODUTO_CADASTRO
        GET  /INTEGRACAO/INTEGRACAO_PRODUTO_TRIBUTO_ICMS
        GET  /INTEGRACAO/INTEGRACAO_PRODUTO_TRIBUTO_PIS_CONFINS
        POST /INTEGRACAO/AJUSTE_ESTOQUE_PRODUTO
    """

    def __init__(self, http):
        self._http = http

    def listar(
        self,
        codigo: Optional[int] = None,
        nome: Optional[str] = None,
        grupo_codigo: Optional[int] = None,
        ativo: Optional[bool] = None,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
        empresa_codigo: Optional[int] = None,
    ) -> List[Dict]:
        """Lista produtos (GET /INTEGRACAO/PRODUTO)."""
        params = {
            "codigo": codigo,
            "nome": nome,
            "grupoCodigo": grupo_codigo,
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina,
        }
        if ativo is not None:
            params["ativo"] = ativo
            if empresa_codigo is not None:
                params["empresaCodigo"] = empresa_codigo
            elif hasattr(self._http.config, "empresa_codigo") and self._http.config.empresa_codigo is not None:
                params["empresaCodigo"] = self._http.config.empresa_codigo
        return self._http.get("/INTEGRACAO/PRODUTO", params)

    def listar_empresa(
        self,
        produto_codigo: Optional[int] = None,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Preços por empresa: venda A, custo, ativo (GET /INTEGRACAO/PRODUTO_EMPRESA)."""
        params = {
            "produtoCodigo": produto_codigo,
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina,
        }
        return self._http.get("/INTEGRACAO/PRODUTO_EMPRESA", params)

    def incluir(self, body: Dict) -> Dict:
        """Cadastra produto (POST /INTEGRACAO/INCLUIR_PRODUTO)."""
        return self._http.post("/INTEGRACAO/INCLUIR_PRODUTO", body)

    def criar(self, body: Dict) -> Dict:
        """Cadastra um novo produto (POST /INTEGRACAO/PRODUTO)."""
        return self._http.post("/INTEGRACAO/PRODUTO", body)

    def atualizar(self, produto_id: int, body: Dict) -> None:
        """Atualiza produto por ID."""
        self._http.put(f"/INTEGRACAO/ALTERAR_PRODUTO/{produto_id}", body)

    def reajustar(self, body: Dict) -> None:
        """
        Reajusta preço de produto (não combustível).

        Args:
            body: Dados do reajuste (percentual, lista de produtos, etc.)
        """
        self._http.post("/INTEGRACAO/REAJUSTAR_PRODUTO", body)

    def trocar_preco(self, body: Dict) -> None:
        """Troca preço de produto com valor exato."""
        self._http.post("/INTEGRACAO/TROCA_PRECO_PRODUTO", body)

    def trocar_precos_produtos_v1(
        self,
        body: Dict,
        *,
        empresa_codigo: Optional[int] = None,
    ) -> Dict:
        """
        Troca oficial de preços (OpenAPI):
        POST /INTEGRACAO/V1/TROCA_PRECOS_PRODUTOS
        Body: ParametrosTrocaPreco (sem centroCusto).
        """
        params: Dict = {}
        if empresa_codigo is not None:
            params["empresaCodigo"] = int(empresa_codigo)
        return self._http.post(
            "/INTEGRACAO/V1/TROCA_PRECOS_PRODUTOS",
            body,
            params=params or None,
        )

    def trocar_preco_combustivel(self, body: Dict) -> None:
        """Troca preço de combustível."""
        self._http.post("/INTEGRACAO/TROCA_PRECO_COMBUSTIVEL", body)

    def inventario(self, body: Dict) -> None:
        """Registra inventário de produto."""
        self._http.post("/INTEGRACAO/PRODUTO_INVENTARIO", body)

    def listar_itens(
        self,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
        nome: Optional[str] = None,
        grupo_codigo: Optional[int] = None,
        ativo: Optional[bool] = None,
    ) -> List[Dict]:
        """Lista itens do catálogo via GET /INTEGRACAO/PRODUTO (rota liberada na CHAVE)."""
        return self.listar(
            nome=nome,
            grupo_codigo=grupo_codigo,
            ativo=ativo,
            pagina=pagina,
            tamanho_pagina=tamanho_pagina,
        )

    def listar_inventario_itens(
        self,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Lista itens do inventário."""
        params = {"pagina": pagina, "tamanhoPagina": tamanho_pagina}
        return self._http.get("/INTEGRACAO/PRODUTO_INVENTARIO_ITENS", params)

    def ajuste_estoque(self, body: Dict) -> None:
        """Registra ajuste de estoque de produto."""
        self._http.post("/INTEGRACAO/AJUSTE_ESTOQUE_PRODUTO", body)

    def comissao(self, body: Dict) -> None:
        """Configura comissão de produto."""
        self._http.post("/INTEGRACAO/PRODUTO_COMISSAO", body)

    def tributos_icms(
        self,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Lista tributos ICMS de produtos."""
        params = {"pagina": pagina, "tamanhoPagina": tamanho_pagina}
        return self._http.get("/INTEGRACAO/INTEGRACAO_PRODUTO_TRIBUTO_ICMS", params)

    def tributos_pis_confins(
        self,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Lista tributos PIS/CONFINS de produtos."""
        params = {"pagina": pagina, "tamanhoPagina": tamanho_pagina}
        return self._http.get(
            "/INTEGRACAO/INTEGRACAO_PRODUTO_TRIBUTO_PIS_CONFINS", params
        )
