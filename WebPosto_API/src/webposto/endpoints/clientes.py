"""
Endpoints de Clientes e Frota.
"""

from typing import Dict, List, Optional


class ClientesEndpoints:
    """
    Endpoints de clientes, frota e grupos de clientes.

    Endpoints cobertos:
        GET  /INTEGRACAO/CLIENTE
        POST /INTEGRACAO/CLIENTE
        PUT  /INTEGRACAO/CLIENTE/{id}
        GET  /INTEGRACAO/CLIENTE_FROTA
        PUT  /INTEGRACAO/CLIENTE_FROTA_VEICULO/{clienteCodigo}/{clienteVeiculoCodigo}
        GET  /INTEGRACAO/GRUPO_CLIENTE
        POST /INTEGRACAO/GRUPO_CLIENTE
        PUT  /INTEGRACAO/GRUPO_CLIENTE/{id}
        POST /INTEGRACAO/VINCULAR_CLIENTE_UNIDADE_NEGOCIO
        POST /INTEGRACAO/INTEGRACAO_CLIENTE_PRAZO
        GET  /INTEGRACAO/INTEGRACAO_LISTA_CLIENTE_PRAZO
        GET  /INTEGRACAO/RETORNO_CADASTRO_CLIENTE
        POST /INTEGRACAO/CENTRO_CUSTO_CLIENTE
        GET  /INTEGRACAO/INTEGRACAO_CLIENTE_CADASTRO
    """

    def __init__(self, http):
        self._http = http

    # ── CLIENTES ─────────────────────────────────────────────────────────────

    def listar(
        self,
        codigo: Optional[int] = None,
        cpf_cnpj: Optional[str] = None,
        nome: Optional[str] = None,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Lista clientes com filtros opcionais."""
        params = {
            "codigo": codigo,
            "cpfCnpj": cpf_cnpj,
            "nome": nome,
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina,
        }
        return self._http.get("/INTEGRACAO/CLIENTE", params)

    def criar(self, body: Dict) -> Dict:
        """
        Cadastra um novo cliente.

        Args:
            body: Dados do cliente conforme schema de integração
        """
        return self._http.post("/INTEGRACAO/CLIENTE", body)

    def atualizar(self, cliente_id: int, body: Dict) -> None:
        """
        Atualiza um cliente existente.

        Args:
            cliente_id: Código do cliente
            body: Dados atualizados
        """
        self._http.put(f"/INTEGRACAO/CLIENTE/{cliente_id}", body)

    # ── FROTA ─────────────────────────────────────────────────────────────────

    def listar_frota(
        self,
        cliente_codigo: Optional[int] = None,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Lista veículos de frota."""
        params = {
            "clienteCodigo": cliente_codigo,
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina,
        }
        return self._http.get("/INTEGRACAO/CLIENTE_FROTA", params)

    def atualizar_veiculo_frota(
        self,
        cliente_codigo: int,
        cliente_veiculo_codigo: int,
        body: Dict,
    ) -> None:
        """Atualiza dados de um veículo de frota."""
        self._http.put(
            f"/INTEGRACAO/CLIENTE_FROTA_VEICULO/{cliente_codigo}/{cliente_veiculo_codigo}",
            body,
        )

    # ── GRUPO DE CLIENTES ─────────────────────────────────────────────────────

    def listar_grupos(
        self,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Lista grupos de clientes."""
        params = {"pagina": pagina, "tamanhoPagina": tamanho_pagina}
        return self._http.get("/INTEGRACAO/GRUPO_CLIENTE", params)

    def criar_grupo(self, body: Dict) -> Dict:
        """Cria um novo grupo de clientes."""
        return self._http.post("/INTEGRACAO/GRUPO_CLIENTE", body)

    def atualizar_grupo(self, grupo_id: int, body: Dict) -> None:
        """Atualiza um grupo de clientes."""
        self._http.put(f"/INTEGRACAO/GRUPO_CLIENTE/{grupo_id}", body)

    # ── PRAZO / UNIDADE NEGÓCIO ───────────────────────────────────────────────

    def vincular_unidade_negocio(self, body: Dict) -> None:
        """Vincula cliente a uma unidade de negócio."""
        self._http.post("/INTEGRACAO/VINCULAR_CLIENTE_UNIDADE_NEGOCIO", body)

    def integrar_prazo(self, body: Dict) -> None:
        """Integra condição de prazo do cliente."""
        self._http.post("/INTEGRACAO/INTEGRACAO_CLIENTE_PRAZO", body)

    def listar_prazos(
        self,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Lista clientes com prazo configurado."""
        params = {"pagina": pagina, "tamanhoPagina": tamanho_pagina}
        return self._http.get("/INTEGRACAO/INTEGRACAO_LISTA_CLIENTE_PRAZO", params)

    def retorno_cadastro(self, body: Dict) -> Dict:
        """Retorno de cadastro de cliente (para integrações externas)."""
        return self._http.get("/INTEGRACAO/RETORNO_CADASTRO_CLIENTE", body)

    def centro_custo(self, body: Dict) -> None:
        """Associa centro de custo a um cliente."""
        self._http.post("/INTEGRACAO/CENTRO_CUSTO_CLIENTE", body)
