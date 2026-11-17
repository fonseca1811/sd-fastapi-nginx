"""Contratos de dados: modelos Pydantic usados para validar entrada e saída da API."""

from pydantic import BaseModel, ConfigDict, Field


class RegistroBase(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=120, examples=["Primeiro registro"])
    descricao: str | None = Field(None, max_length=500, examples=["Criado via Nginx"])


class RegistroCreate(RegistroBase):
    """Corpo da requisição de criação (POST)."""


class RegistroUpdate(BaseModel):
    """Corpo da requisição de atualização (PUT): todos os campos são opcionais."""

    titulo: str | None = Field(None, min_length=1, max_length=120)
    descricao: str | None = Field(None, max_length=500)


class RegistroResponse(RegistroBase):
    """Formato devolvido pela API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    criado_em: str
