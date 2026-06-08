"""
Operações CRUD para webPosto API.
Gerenciamento de Financeiro e Caixa com auditoria.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from .schemas import (
    FinanceiroCreate,
    FinanceiroUpdate,
    CaixaCreate,
    CaixaUpdate,
    StatusTitulo,
)
from src.infrastructure.webposto.client import WebPostoClient


# ===============================================
# FINANCEIRO CRUD
# ===============================================


class FinanceiroCRUD:
    """CRUD para títulos financeiros."""

    @staticmethod
    async def listar(
        session: AsyncSession,
        pagina: int = 1,
        limite: int = 50,
        tipo: Optional[str] = None,
        status: Optional[str] = None,
        ordenar_por: str = "data_vencimento",
        ordenacao: str = "asc",
    ) -> tuple[int, list]:
        """Listar todos os títulos com paginação."""
        try:
            offset = (pagina - 1) * limite

            # Tentar carregar dados REAIS da API webPosto
            try:
                client = WebPostoClient()
                dados_webposto = await client.get_financeiro(skip=offset, limit=limite)
                await client.close()

                if dados_webposto:
                    # Transformar dados reais para o formato esperado
                    titulos_reais = [
                        {
                            "id": str(t.get("id", uuid.uuid4())),
                            "tipo": (
                                "RECEBER" if t.get("tipo") == "A Receber" else "PAGAR"
                            ),
                            "valor": float(t.get("valor", 0)),
                            "data_vencimento": t.get("data_vencimento", datetime.now()),
                            "descricao": t.get("descricao", ""),
                            "cliente_fornecedor": t.get("cliente_fornecedor", ""),
                            "categoria": t.get("categoria", ""),
                            "pago": t.get("pago", False),
                            "dias_vencido": t.get("dias_vencido", 0),
                            "status": t.get("status", StatusTitulo.PENDENTE),
                            "webposto_id": str(t.get("webposto_id", "")),
                            "data_criacao": t.get("data_criacao", datetime.now()),
                            "data_pagamento": t.get("data_pagamento"),
                            "data_atualizacao": t.get(
                                "data_atualizacao", datetime.now()
                            ),
                            "modificado_por": t.get("modificado_por"),
                        }
                        for t in dados_webposto
                    ]

                    total = len(titulos_reais)
                    return total, titulos_reais
            except Exception as e:
                raise Exception(
                    f"API WebPosto indisponível para títulos (sem dados fictícios): {e}"
                ) from e

            raise Exception(
                "Nenhum título retornado pela API WebPosto (sem dados fictícios)."
            )

        except Exception as e:
            raise Exception(f"Erro ao listar financeiro: {str(e)}")

    @staticmethod
    async def obter_por_id(session: AsyncSession, titulo_id: str) -> dict:
        """Obter um título específico."""
        try:
            # Mock
            titulo = {
                "id": titulo_id,
                "tipo": "RECEBER",
                "valor": 5000.00,
                "data_vencimento": datetime.now() + timedelta(days=30),
                "descricao": "Venda de produtos",
                "cliente_fornecedor": "Cliente ABC",
                "categoria": "Vendas",
                "pago": False,
                "dias_vencido": -30,
                "status": StatusTitulo.PENDENTE,
                "webposto_id": "WP000001",
                "data_criacao": datetime.now() - timedelta(days=5),
                "data_pagamento": None,
                "data_atualizacao": datetime.now(),
                "modificado_por": None,
            }
            return titulo
        except Exception as e:
            raise Exception(f"Erro ao obter título: {str(e)}")

    @staticmethod
    async def criar(
        session: AsyncSession,
        dados: FinanceiroCreate,
        usuario: str,
        ip_origem: Optional[str] = None,
    ) -> dict:
        """Criar novo título."""
        try:
            titulo_id = f"TIT{str(uuid.uuid4())[:8].upper()}"

            novo_titulo = {
                "id": titulo_id,
                "tipo": dados.tipo,
                "valor": dados.valor,
                "data_vencimento": dados.data_vencimento,
                "descricao": dados.descricao,
                "cliente_fornecedor": dados.cliente_fornecedor,
                "categoria": dados.categoria,
                "pago": False,
                "dias_vencido": (dados.data_vencimento - datetime.now()).days,
                "status": StatusTitulo.PENDENTE,
                "webposto_id": None,
                "data_criacao": datetime.now(),
                "data_pagamento": None,
                "data_atualizacao": datetime.now(),
                "modificado_por": usuario,
            }

            # Registrar auditoria
            await AuditoriaCRUD.registrar(
                session,
                tabela="financeiro",
                record_id=titulo_id,
                operacao="CREATE",
                usuario=usuario,
                valores_antes=None,
                valores_depois=novo_titulo,
                ip_origem=ip_origem,
                motivo="Criação de novo título",
            )

            return novo_titulo

        except ValidationError as e:
            raise ValueError(f"Validação falhou: {str(e)}")
        except Exception as e:
            raise Exception(f"Erro ao criar título: {str(e)}")

    @staticmethod
    async def atualizar(
        session: AsyncSession,
        titulo_id: str,
        dados: FinanceiroUpdate,
        usuario: str,
        ip_origem: Optional[str] = None,
        motivo: Optional[str] = None,
    ) -> dict:
        """Atualizar título existente."""
        try:
            # Obter valores antigos
            titulo_atual = await FinanceiroCRUD.obter_por_id(session, titulo_id)

            # Aplicar atualizações
            valores_atualizacao = dados.model_dump(exclude_unset=True)
            titulo_atualizado = {**titulo_atual, **valores_atualizacao}
            titulo_atualizado["data_atualizacao"] = datetime.now()
            titulo_atualizado["modificado_por"] = usuario

            # Recalcular dias vencido
            dias_vencido = (titulo_atualizado["data_vencimento"] - datetime.now()).days
            titulo_atualizado["dias_vencido"] = dias_vencido

            # Determinar status
            if titulo_atualizado["pago"]:
                titulo_atualizado["status"] = StatusTitulo.PAGO
            elif dias_vencido < 0:
                titulo_atualizado["status"] = StatusTitulo.VENCIDO
            else:
                titulo_atualizado["status"] = StatusTitulo.PENDENTE

            # Registrar auditoria
            await AuditoriaCRUD.registrar(
                session,
                tabela="financeiro",
                record_id=titulo_id,
                operacao="UPDATE",
                usuario=usuario,
                valores_antes=titulo_atual,
                valores_depois=titulo_atualizado,
                ip_origem=ip_origem,
                motivo=motivo or "Atualização de título",
            )

            return titulo_atualizado

        except Exception as e:
            raise Exception(f"Erro ao atualizar título: {str(e)}")

    @staticmethod
    async def deletar(
        session: AsyncSession,
        titulo_id: str,
        usuario: str,
        ip_origem: Optional[str] = None,
        motivo: Optional[str] = None,
    ) -> dict:
        """Deletar título (soft delete com auditoria)."""
        try:
            titulo_atual = await FinanceiroCRUD.obter_por_id(session, titulo_id)

            # Marcar como cancelado ao invés de deletar
            titulo_cancelado = titulo_atual.copy()
            titulo_cancelado["status"] = StatusTitulo.CANCELADO
            titulo_cancelado["data_atualizacao"] = datetime.now()
            titulo_cancelado["modificado_por"] = usuario

            # Registrar auditoria
            await AuditoriaCRUD.registrar(
                session,
                tabela="financeiro",
                record_id=titulo_id,
                operacao="DELETE",
                usuario=usuario,
                valores_antes=titulo_atual,
                valores_depois=None,
                ip_origem=ip_origem,
                motivo=motivo or "Deleção de título",
            )

            return {
                "id": titulo_id,
                "status": "cancelado",
                "mensagem": "Título cancelado com sucesso",
            }

        except Exception as e:
            raise Exception(f"Erro ao deletar título: {str(e)}")


# ===============================================
# CAIXA CRUD
# ===============================================


class CaixaCRUD:
    """CRUD para movimentos de caixa."""

    @staticmethod
    async def listar(
        session: AsyncSession,
        pagina: int = 1,
        limite: int = 50,
        numero_caixa: Optional[int] = None,
        tipo_movimento: Optional[str] = None,
        data: Optional[str] = None,
    ) -> tuple[int, list]:
        """Listar movimentos de caixa com paginação."""
        try:
            offset = (pagina - 1) * limite

            # Tentar carregar dados REAIS da API webPosto
            try:
                client = WebPostoClient()
                dados_webposto = await client.get_caixa(skip=offset, limit=limite)
                await client.close()

                if dados_webposto:
                    # Transformar dados reais para o formato esperado
                    movimentos_reais = [
                        {
                            "id": str(m.get("id", uuid.uuid4())),
                            "numero_caixa": m.get("numero_caixa", 1),
                            "descricao": m.get("descricao", ""),
                            "tipo_movimento": m.get("tipo_movimento", ""),
                            "valor": float(m.get("valor", 0)),
                            "saldo": float(m.get("saldo", 0)),
                            "data_movimento": m.get("data_movimento", datetime.now()),
                            "referencia": m.get("referencia", ""),
                            "operador": m.get("operador", ""),
                            "webposto_id": str(m.get("webposto_id", "")),
                            "data_criacao": m.get("data_criacao", datetime.now()),
                            "data_atualizacao": m.get(
                                "data_atualizacao", datetime.now()
                            ),
                            "modificado_por": m.get("modificado_por"),
                        }
                        for m in dados_webposto
                    ]

                    total = len(movimentos_reais)
                    return total, movimentos_reais
            except Exception as e:
                raise Exception(
                    f"API WebPosto indisponível para caixa (sem dados fictícios): {e}"
                ) from e

            raise Exception(
                "Nenhum movimento de caixa retornado pela API WebPosto (sem dados fictícios)."
            )

        except Exception as e:
            raise Exception(f"Erro ao listar caixa: {str(e)}")

    @staticmethod
    async def obter_por_id(session: AsyncSession, movimento_id: str) -> dict:
        """Obter movimento específico."""
        try:
            movimento = {
                "id": movimento_id,
                "numero_caixa": 1,
                "descricao": "Abertura de Caixa",
                "tipo_movimento": "ABERTURA",
                "valor": 5000.00,
                "saldo": 5000.00,
                "data_movimento": datetime.now(),
                "referencia": "OPEN001",
                "operador": "Gerente",
                "webposto_id": "WPC000001",
                "data_criacao": datetime.now(),
                "data_atualizacao": datetime.now(),
                "modificado_por": None,
            }
            return movimento
        except Exception as e:
            raise Exception(f"Erro ao obter movimento: {str(e)}")

    @staticmethod
    async def criar(
        session: AsyncSession,
        dados: CaixaCreate,
        usuario: str,
        ip_origem: Optional[str] = None,
    ) -> dict:
        """Criar novo movimento de caixa."""
        try:
            movimento_id = f"CAIXA{str(uuid.uuid4())[:8].upper()}"

            novo_movimento = {
                "id": movimento_id,
                "numero_caixa": dados.numero_caixa,
                "descricao": dados.descricao,
                "tipo_movimento": dados.tipo_movimento,
                "valor": dados.valor,
                "saldo": dados.valor,  # Será calculado em produção
                "data_movimento": datetime.now(),
                "referencia": dados.referencia,
                "operador": dados.operador or usuario,
                "webposto_id": None,
                "data_criacao": datetime.now(),
                "data_atualizacao": datetime.now(),
                "modificado_por": usuario,
            }

            await AuditoriaCRUD.registrar(
                session,
                tabela="caixa",
                record_id=movimento_id,
                operacao="CREATE",
                usuario=usuario,
                valores_antes=None,
                valores_depois=novo_movimento,
                ip_origem=ip_origem,
                motivo="Criação de movimento de caixa",
            )

            return novo_movimento

        except Exception as e:
            raise Exception(f"Erro ao criar movimento: {str(e)}")

    @staticmethod
    async def atualizar(
        session: AsyncSession,
        movimento_id: str,
        dados: CaixaUpdate,
        usuario: str,
        ip_origem: Optional[str] = None,
        motivo: Optional[str] = None,
    ) -> dict:
        """Atualizar movimento de caixa."""
        try:
            movimento_atual = await CaixaCRUD.obter_por_id(session, movimento_id)

            valores_atualizacao = dados.model_dump(exclude_unset=True)
            movimento_atualizado = {**movimento_atual, **valores_atualizacao}
            movimento_atualizado["data_atualizacao"] = datetime.now()
            movimento_atualizado["modificado_por"] = usuario

            await AuditoriaCRUD.registrar(
                session,
                tabela="caixa",
                record_id=movimento_id,
                operacao="UPDATE",
                usuario=usuario,
                valores_antes=movimento_atual,
                valores_depois=movimento_atualizado,
                ip_origem=ip_origem,
                motivo=motivo or "Atualização de movimento",
            )

            return movimento_atualizado

        except Exception as e:
            raise Exception(f"Erro ao atualizar movimento: {str(e)}")

    @staticmethod
    async def deletar(
        session: AsyncSession,
        movimento_id: str,
        usuario: str,
        ip_origem: Optional[str] = None,
        motivo: Optional[str] = None,
    ) -> dict:
        """Deletar movimento de caixa."""
        try:
            movimento_atual = await CaixaCRUD.obter_por_id(session, movimento_id)

            await AuditoriaCRUD.registrar(
                session,
                tabela="caixa",
                record_id=movimento_id,
                operacao="DELETE",
                usuario=usuario,
                valores_antes=movimento_atual,
                valores_depois=None,
                ip_origem=ip_origem,
                motivo=motivo or "Deleção de movimento",
            )

            return {
                "id": movimento_id,
                "status": "deletado",
                "mensagem": "Movimento deletado com sucesso",
            }

        except Exception as e:
            raise Exception(f"Erro ao deletar movimento: {str(e)}")


# ===============================================
# AUDITORIA
# ===============================================


class AuditoriaCRUD:
    """Sistema de auditoria para todas as operações."""

    @staticmethod
    async def registrar(
        session: AsyncSession,
        tabela: str,
        record_id: str,
        operacao: str,
        usuario: str,
        valores_antes: Optional[dict],
        valores_depois: Optional[dict],
        ip_origem: Optional[str] = None,
        motivo: Optional[str] = None,
    ) -> str:
        """Registrar operação em auditoria."""
        try:
            auditoria_id = f"AUD{str(uuid.uuid4())[:8].upper()}"

            registro_auditoria = {
                "id": auditoria_id,
                "tabela": tabela,
                "record_id": record_id,
                "operacao": operacao,
                "usuario": usuario,
                "valores_antes": valores_antes,
                "valores_depois": valores_depois,
                "data_operacao": datetime.now(),
                "ip_origem": ip_origem,
                "motivo": motivo,
            }

            # Em produção, seria inserido no banco de dados
            # Por enquanto, apenas retorna ID
            print(f"[AUDITORIA] {operacao} em {tabela} (ID: {record_id}) por {usuario}")

            return auditoria_id

        except Exception as e:
            print(f"Erro ao registrar auditoria: {str(e)}")
            raise

    @staticmethod
    async def listar(
        session: AsyncSession,
        tabela: Optional[str] = None,
        usuario: Optional[str] = None,
        operacao: Optional[str] = None,
        pagina: int = 1,
        limite: int = 50,
    ) -> tuple[int, list]:
        """Listar registros de auditoria com filtros."""
        try:
            offset = (pagina - 1) * limite

            raise Exception(
                "Auditoria interna (Mongo) não configurada — sem dados fictícios."
            )

        except Exception as e:
            raise Exception(f"Erro ao listar auditoria: {str(e)}")
