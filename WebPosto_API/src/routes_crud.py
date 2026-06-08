"""
Rotas CRUD para webPosto API.
Endpoints para criar, ler, atualizar e deletar dados.
"""

from fastapi import APIRouter, HTTPException, Query, Request
from typing import Optional

from .schemas import (
    FinanceiroCreate,
    FinanceiroUpdate,
    CaixaCreate,
    CaixaUpdate,
    ListaResponse,
    APIResponse,
)
from .crud import FinanceiroCRUD, CaixaCRUD, AuditoriaCRUD

router = APIRouter(prefix="/api/v1", tags=["CRUD"])


# ===============================================
# HELPER FUNCTIONS
# ===============================================


def get_client_ip(request: Request) -> str:
    """Extrair IP do cliente."""
    return request.client.host if request.client else "desconhecido"


def get_usuario(request: Request) -> str:
    """Extrair usuário do request (header ou padrão)."""
    return request.headers.get("X-Usuario", "sistema")


# ===============================================
# FINANCEIRO ENDPOINTS
# ===============================================


@router.get("/financeiro", response_model=ListaResponse)
async def listar_financeiro(
    request: Request,
    pagina: int = Query(1, ge=1),
    limite: int = Query(50, ge=1, le=500),
    tipo: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    ordenar_por: str = Query("data_vencimento"),
):
    """
    Listar todos os títulos com paginação e filtros.

    **Parâmetros:**
    - `pagina`: Número da página (padrão: 1)
    - `limite`: Registros por página (padrão: 50, máx: 500)
    - `tipo`: Filtrar por RECEBER ou PAGAR
    - `status`: Filtrar por pendente, pago, vencido, cancelado
    - `ordenar_por`: Campo para ordenação

    **Exemplo:**
    ```bash
    GET /api/v1/financeiro?pagina=1&limite=50&tipo=RECEBER&status=pendente
    ```
    """
    try:
        total, dados = await FinanceiroCRUD.listar(
            None, pagina, limite, tipo, status, ordenar_por
        )

        total_paginas = (total + limite - 1) // limite

        return ListaResponse(
            status="success",
            total=total,
            pagina=pagina,
            limite=limite,
            total_paginas=total_paginas,
            dados=dados,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/financeiro/{titulo_id}", response_model=APIResponse)
async def obter_financeiro(titulo_id: str):
    """
    Obter um título específico.

    **Exemplo:**
    ```bash
    GET /api/v1/financeiro/TIT001
    ```
    """
    try:
        titulo = await FinanceiroCRUD.obter_por_id(None, titulo_id)
        return APIResponse(
            status="success", mensagem="Título obtido com sucesso", dados=titulo
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/financeiro", response_model=APIResponse)
async def criar_financeiro(request: Request, dados: FinanceiroCreate):
    """
    Criar novo título financeiro.

    **Body:**
    ```json
    {
      "tipo": "RECEBER",
      "valor": 1500.00,
      "data_vencimento": "2026-05-14T00:00:00Z",
      "descricao": "Venda de produtos",
      "cliente_fornecedor": "Cliente ABC",
      "categoria": "Vendas"
    }
    ```

    **Headers Opcionais:**
    - `X-Usuario`: Usuário que está criando (padrão: "sistema")
    - `X-Motivo`: Razão da criação
    """
    try:
        usuario = get_usuario(request)
        ip = get_client_ip(request)
        motivo = request.headers.get("X-Motivo", "Criação via API")

        titulo = await FinanceiroCRUD.criar(None, dados, usuario, ip)

        return APIResponse(
            status="success", mensagem="Título criado com sucesso", dados=titulo
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/financeiro/{titulo_id}", response_model=APIResponse)
async def atualizar_financeiro(
    request: Request, titulo_id: str, dados: FinanceiroUpdate
):
    """
    Atualizar título existente.

    **Body (parcial):**
    ```json
    {
      "valor": 2000.00,
      "pago": true,
      "data_pagamento": "2026-04-14T10:30:00Z"
    }
    ```

    **Headers Opcionais:**
    - `X-Usuario`: Usuário que está atualizando
    - `X-Motivo`: Razão da atualização
    """
    try:
        usuario = get_usuario(request)
        ip = get_client_ip(request)
        motivo = request.headers.get("X-Motivo")

        titulo = await FinanceiroCRUD.atualizar(
            None, titulo_id, dados, usuario, ip, motivo
        )

        return APIResponse(
            status="success", mensagem="Título atualizado com sucesso", dados=titulo
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/financeiro/{titulo_id}", response_model=APIResponse)
async def deletar_financeiro(request: Request, titulo_id: str):
    """
    Deletar título (soft delete + cancelamento).

    **Headers Opcionais:**
    - `X-Usuario`: Usuário que está deletando
    - `X-Motivo`: Razão da deleção
    """
    try:
        usuario = get_usuario(request)
        ip = get_client_ip(request)
        motivo = request.headers.get("X-Motivo", "Deleção via API")

        resultado = await FinanceiroCRUD.deletar(None, titulo_id, usuario, ip, motivo)

        return APIResponse(
            status="success", mensagem="Título deletado com sucesso", dados=resultado
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===============================================
# CAIXA ENDPOINTS
# ===============================================


@router.get("/caixa", response_model=ListaResponse)
async def listar_caixa(
    request: Request,
    pagina: int = Query(1, ge=1),
    limite: int = Query(50, ge=1, le=500),
    numero_caixa: Optional[int] = Query(None),
    tipo_movimento: Optional[str] = Query(None),
    data: Optional[str] = Query(None),
):
    """
    Listar movimentos de caixa com paginação.

    **Parâmetros:**
    - `pagina`: Número da página (padrão: 1)
    - `limite`: Registros por página (padrão: 50, máx: 500)
    - `numero_caixa`: Filtrar por caixa específica
    - `tipo_movimento`: Filtrar por ABERTURA, VENDA, SAQUE, FECHAMENTO, etc.
    - `data`: Filtrar por data (YYYY-MM-DD)

    **Exemplo:**
    ```bash
    GET /api/v1/caixa?numero_caixa=1&tipo_movimento=VENDA
    ```
    """
    try:
        total, dados = await CaixaCRUD.listar(
            None, pagina, limite, numero_caixa, tipo_movimento, data
        )

        total_paginas = (total + limite - 1) // limite

        return ListaResponse(
            status="success",
            total=total,
            pagina=pagina,
            limite=limite,
            total_paginas=total_paginas,
            dados=dados,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/caixa/{movimento_id}", response_model=APIResponse)
async def obter_caixa(movimento_id: str):
    """
    Obter movimento de caixa específico.

    **Exemplo:**
    ```bash
    GET /api/v1/caixa/CAIXA001
    ```
    """
    try:
        movimento = await CaixaCRUD.obter_por_id(None, movimento_id)
        return APIResponse(
            status="success", mensagem="Movimento obtido com sucesso", dados=movimento
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/caixa", response_model=APIResponse)
async def criar_caixa(request: Request, dados: CaixaCreate):
    """
    Criar novo movimento de caixa.

    **Body:**
    ```json
    {
      "numero_caixa": 1,
      "descricao": "Venda Pista",
      "tipo_movimento": "VENDA",
      "valor": 250.50,
      "referencia": "VND-001",
      "operador": "João Silva"
    }
    ```

    **Headers Opcionais:**
    - `X-Usuario`: Usuário que está criando
    - `X-Motivo`: Razão da criação
    """
    try:
        usuario = get_usuario(request)
        ip = get_client_ip(request)

        movimento = await CaixaCRUD.criar(None, dados, usuario, ip)

        return APIResponse(
            status="success", mensagem="Movimento criado com sucesso", dados=movimento
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/caixa/{movimento_id}", response_model=APIResponse)
async def atualizar_caixa(request: Request, movimento_id: str, dados: CaixaUpdate):
    """
    Atualizar movimento de caixa.

    **Body (parcial):**
    ```json
    {
      "valor": 300.00,
      "operador": "João Silva"
    }
    ```

    **Headers Opcionais:**
    - `X-Usuario`: Usuário que está atualizando
    - `X-Motivo`: Razão da atualização
    """
    try:
        usuario = get_usuario(request)
        ip = get_client_ip(request)
        motivo = request.headers.get("X-Motivo")

        movimento = await CaixaCRUD.atualizar(
            None, movimento_id, dados, usuario, ip, motivo
        )

        return APIResponse(
            status="success",
            mensagem="Movimento atualizado com sucesso",
            dados=movimento,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/caixa/{movimento_id}", response_model=APIResponse)
async def deletar_caixa(request: Request, movimento_id: str):
    """
    Deletar movimento de caixa.

    **Headers Opcionais:**
    - `X-Usuario`: Usuário que está deletando
    - `X-Motivo`: Razão da deleção
    """
    try:
        usuario = get_usuario(request)
        ip = get_client_ip(request)
        motivo = request.headers.get("X-Motivo", "Deleção via API")

        resultado = await CaixaCRUD.deletar(None, movimento_id, usuario, ip, motivo)

        return APIResponse(
            status="success", mensagem="Movimento deletado com sucesso", dados=resultado
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===============================================
# AUDITORIA ENDPOINTS
# ===============================================


@router.get("/auditoria", response_model=ListaResponse)
async def listar_auditoria(
    request: Request,
    pagina: int = Query(1, ge=1),
    limite: int = Query(50, ge=1, le=500),
    tabela: Optional[str] = Query(None),
    usuario: Optional[str] = Query(None),
    operacao: Optional[str] = Query(None),
):
    """
    Listar log de auditoria de todas as operações.

    **Parâmetros:**
    - `tabela`: Filtrar por financeiro ou caixa
    - `usuario`: Filtrar por usuário que fez a operação
    - `operacao`: Filtrar por CREATE, UPDATE ou DELETE

    **Exemplo:**
    ```bash
    GET /api/v1/auditoria?tabela=financeiro&operacao=UPDATE
    ```
    """
    try:
        total, dados = await AuditoriaCRUD.listar(
            None, tabela, usuario, operacao, pagina, limite
        )

        total_paginas = (total + limite - 1) // limite

        return ListaResponse(
            status="success",
            total=total,
            pagina=pagina,
            limite=limite,
            total_paginas=total_paginas,
            dados=dados,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
