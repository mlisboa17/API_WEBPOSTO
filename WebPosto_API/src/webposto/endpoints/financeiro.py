"""
Endpoints Financeiros.
"""

from datetime import date
from typing import Dict, List, Optional


class FinanceiroEndpoints:
    """
    Endpoints financeiros: títulos, movimentos, caixa, transferências.

    Endpoints cobertos:
        GET  /INTEGRACAO/TITULO_RECEBER
        POST /INTEGRACAO/TITULO_RECEBER
        GET  /INTEGRACAO/TITULO_PAGAR
        POST /INTEGRACAO/TITULO_PAGAR
        GET  /INTEGRACAO/MOVIMENTO_CONTA
        GET  /INTEGRACAO/FINANCEIRO_EXCLUSAO
        GET  /INTEGRACAO/FECHAMENTO_CAIXA
        GET  /INTEGRACAO/TRANSFERENCIA_BANCARIA
        POST /INTEGRACAO/TRANSFERENCIA_BANCARIA
        PUT  /INTEGRACAO/RECEBER_TITULO
        PUT  /INTEGRACAO/RECEBER_TITULO_CONVERTIDO
        PUT  /INTEGRACAO/RECEBER_CHEQUE
        PUT  /INTEGRACAO/RECEBER_CARTAO
        POST /INTEGRACAO/ADIANTAMENTO_FORNECEDOR  (GET também)
        POST /INTEGRACAO/INCLUIR_LANCAMENTO_CONTABIL
        POST /INTEGRACAO/INCLUIR_LOTE_CONTABIL
        POST /INTEGRACAO/INCLUIR_OFX
        GET  /INTEGRACAO/PLANO_DE_CONTAS
    """

    def __init__(self, http):
        self._http = http

    # ── TÍTULOS A RECEBER ─────────────────────────────────────────────────────

    def listar_titulos_receber(
        self,
        data_inicial: date,
        data_final: date,
        filial: Optional[List[int]] = None,
        situacao: Optional[str] = None,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """
        Lista títulos a receber.

        Args:
            data_inicial: Data de início
            data_final: Data de fim
            filial: Código(s) de filial
            situacao: AMBOS | ABERTO | RECEBIDO
            pagina: Número da página
            tamanho_pagina: Registros por página
        """
        params = {
            "dataInicial": data_inicial.isoformat(),
            "dataFinal": data_final.isoformat(),
            "filial": filial,
            "situacaoReceber": situacao,
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina,
        }
        return self._http.get("/INTEGRACAO/TITULO_RECEBER", params)

    def criar_titulo_receber(self, body: Dict) -> Dict:
        """Cria título a receber."""
        return self._http.post("/INTEGRACAO/TITULO_RECEBER", body)

    def receber_titulo(self, body: Dict) -> None:
        """Efetua o recebimento de um título."""
        self._http.put("/INTEGRACAO/RECEBER_TITULO", body)

    def receber_titulo_convertido(self, body: Dict) -> None:
        """Recebe título com conversão de moeda."""
        self._http.put("/INTEGRACAO/RECEBER_TITULO_CONVERTIDO", body)

    def receber_cheque(self, body: Dict, empresa_codigo: Optional[int] = None) -> None:
        """Recebe cheque."""
        params = {"empresaCodigo": empresa_codigo}
        self._http.put("/INTEGRACAO/RECEBER_CHEQUE", body, params)

    def receber_cartao(self, body: Dict) -> None:
        """Recebe pagamento por cartão."""
        self._http.put("/INTEGRACAO/RECEBER_CARTAO", body)

    # ── TÍTULOS A PAGAR ────────────────────────────────────────────────────────

    def listar_titulos_pagar(
        self,
        data_inicial: date,
        data_final: date,
        filial: Optional[List[int]] = None,
        situacao: Optional[str] = None,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Lista títulos a pagar."""
        params = {
            "dataInicial": data_inicial.isoformat(),
            "dataFinal": data_final.isoformat(),
            "filial": filial,
            "situacaoPagar": situacao,
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina,
        }
        return self._http.get("/INTEGRACAO/TITULO_PAGAR", params)

    def criar_titulo_pagar(self, body: Dict) -> Dict:
        """Cria título a pagar."""
        return self._http.post("/INTEGRACAO/TITULO_PAGAR", body)

    # ── MOVIMENTO DE CONTA ────────────────────────────────────────────────────

    def listar_movimentos_conta(
        self,
        data_inicial: date,
        data_final: date,
        filial: Optional[List[int]] = None,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Lista movimentos de conta bancária."""
        params = {
            "dataInicial": data_inicial.isoformat(),
            "dataFinal": data_final.isoformat(),
            "filial": filial,
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina,
        }
        return self._http.get("/INTEGRACAO/MOVIMENTO_CONTA", params)

    # ── FECHAMENTO DE CAIXA ───────────────────────────────────────────────────

    def listar_fechamento_caixa(
        self,
        data_inicial: date,
        data_final: date,
        filial: Optional[List[int]] = None,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Lista fechamentos de caixa."""
        params = {
            "dataInicial": data_inicial.isoformat(),
            "dataFinal": data_final.isoformat(),
            "filial": filial,
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina,
        }
        return self._http.get("/INTEGRACAO/FECHAMENTO_CAIXA", params)

    def listar_caixa_apresentado(
        self,
        data_inicial: date,
        data_final: date,
        filial: Optional[List[int]] = None,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Valores apurados × apresentados por forma de pagamento."""
        params = {
            "dataInicial": data_inicial.isoformat(),
            "dataFinal": data_final.isoformat(),
            "filial": filial,
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina,
        }
        return self._http.get("/INTEGRACAO/CAIXA_APRESENTADO", params)

    def listar_caixa(
        self,
        data_inicial: date,
        data_final: date,
        filial: Optional[List[int]] = None,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Movimentos de caixa no período."""
        params = {
            "dataInicial": data_inicial.isoformat(),
            "dataFinal": data_final.isoformat(),
            "filial": filial,
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina,
        }
        return self._http.get("/INTEGRACAO/CAIXA", params)

    # ── TRANSFERÊNCIA BANCÁRIA ────────────────────────────────────────────────

    def listar_transferencias(
        self,
        data_inicial: date,
        data_final: date,
        filial: Optional[List[int]] = None,
    ) -> List[Dict]:
        """Lista transferências bancárias."""
        params = {
            "dataInicial": data_inicial.isoformat(),
            "dataFinal": data_final.isoformat(),
            "filial": filial,
        }
        return self._http.get("/INTEGRACAO/TRANSFERENCIA_BANCARIA", params)

    def criar_transferencia(self, body: Dict) -> None:
        """Registra uma transferência bancária."""
        self._http.post("/INTEGRACAO/TRANSFERENCIA_BANCARIA", body)

    # ── LANÇAMENTO CONTÁBIL ───────────────────────────────────────────────────

    def incluir_lancamento_contabil(self, body: Dict) -> Dict:
        """Inclui lançamento contábil."""
        return self._http.post("/INTEGRACAO/INCLUIR_LANCAMENTO_CONTABIL", body)

    def incluir_lote_contabil(self, body: Dict) -> Dict:
        """Inclui lote contábil."""
        return self._http.post("/INTEGRACAO/INCLUIR_LOTE_CONTABIL", body)

    def incluir_ofx(self, body: Dict) -> None:
        """Importa arquivo OFX."""
        self._http.post("/INTEGRACAO/INCLUIR_OFX", body)

    def plano_de_contas(
        self,
        pagina: Optional[int] = None,
        tamanho_pagina: Optional[int] = None,
    ) -> List[Dict]:
        """Lista plano de contas."""
        params = {"pagina": pagina, "tamanhoPagina": tamanho_pagina}
        return self._http.get("/INTEGRACAO/PLANO_DE_CONTAS", params)

    def financeiro_exclusao(
        self,
        data_inicial: date,
        data_final: date,
        filial: Optional[List[int]] = None,
    ) -> List[Dict]:
        """
        Lista movimentos financeiros de exclusão.

        ATENÇÃO: Requer configuração específica no WebPosto.
        Verifique Filial > Fechamento de Caixa > 'Gerar débito em financeiro de conta Caixa'.
        """
        params = {
            "dataInicial": data_inicial.isoformat(),
            "dataFinal": data_final.isoformat(),
            "filial": filial,
        }
        return self._http.get("/INTEGRACAO/FINANCEIRO_EXCLUSAO", params)
