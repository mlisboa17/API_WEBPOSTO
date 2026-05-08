from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, validator


class ClienteCreateDTO(BaseModel):
    """DTO: Criar novo cliente."""

    nome: str = Field(..., min_length=1, max_length=255)
    cnpj: str = Field(..., min_length=10, max_length=20)
    webposto_id: Optional[str] = None

    @validator("nome")
    def nome_nao_vazio(cls, v):
        if not v.strip():
            raise ValueError("Nome não pode ser vazio")
        return v.strip()

    @validator("cnpj")
    def cnpj_valido(cls, v):
        if len(v) < 10:
            raise ValueError("CNPJ inválido")
        return v.strip()


class ClienteUpdateDTO(BaseModel):
    """DTO: Atualizar cliente."""

    nome: Optional[str] = Field(None, min_length=1, max_length=255)
    cnpj: Optional[str] = Field(None, min_length=10, max_length=20)
    ativo: Optional[bool] = None

    @validator("nome")
    def nome_nao_vazio(cls, v):
        if v is not None and not v.strip():
            raise ValueError("Nome não pode ser vazio")
        return v.strip() if v else None

    @validator("cnpj")
    def cnpj_valido(cls, v):
        if v is not None and len(v) < 10:
            raise ValueError("CNPJ inválido")
        return v.strip() if v else None


class ClienteResponseDTO(BaseModel):
    """DTO: Resposta com dados do cliente."""

    id: str
    nome: str
    cnpj: str
    ativo: bool
    webposto_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
