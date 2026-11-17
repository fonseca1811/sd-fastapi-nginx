"""Rotas e endpoints do recurso /registros."""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.core.database import get_db
from app.repositories.registro import RegistroRepository
from app.schemas.registro import RegistroCreate, RegistroResponse, RegistroUpdate

router = APIRouter(prefix="/registros", tags=["Registros"])


def get_repository(conn: Annotated[sqlite3.Connection, Depends(get_db)]) -> RegistroRepository:
    return RegistroRepository(conn)


Repo = Annotated[RegistroRepository, Depends(get_repository)]


@router.get("", response_model=list[RegistroResponse])
def listar_registros(
    repo: Repo,
    limite: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return repo.listar(limite, offset)


@router.get("/{registro_id}", response_model=RegistroResponse)
def buscar_registro(registro_id: int, repo: Repo):
    registro = repo.buscar_por_id(registro_id)
    if registro is None:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    return registro


@router.post("", response_model=RegistroResponse, status_code=status.HTTP_201_CREATED)
def criar_registro(dados: RegistroCreate, repo: Repo):
    return repo.criar(dados)


@router.put("/{registro_id}", response_model=RegistroResponse)
def atualizar_registro(registro_id: int, dados: RegistroUpdate, repo: Repo):
    registro = repo.atualizar(registro_id, dados)
    if registro is None:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    return registro


@router.delete("/{registro_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_registro(registro_id: int, repo: Repo):
    if not repo.remover(registro_id):
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
