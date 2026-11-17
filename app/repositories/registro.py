"""Camada de acesso a dados (padrão Repository).

Todo o SQL do recurso "registros" fica isolado aqui; as rotas não conhecem o banco.
"""

import sqlite3

from app.schemas.registro import RegistroCreate, RegistroUpdate

# Colunas que podem ser alteradas via PUT (lista fixa = nada de SQL injection no SET)
CAMPOS_EDITAVEIS = ("titulo", "descricao")


class RegistroRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def listar(self, limite: int = 100, offset: int = 0) -> list[dict]:
        cursor = self.conn.execute(
            "SELECT id, titulo, descricao, criado_em FROM registros ORDER BY id LIMIT ? OFFSET ?",
            (limite, offset),
        )
        return [dict(linha) for linha in cursor.fetchall()]

    def buscar_por_id(self, registro_id: int) -> dict | None:
        linha = self.conn.execute(
            "SELECT id, titulo, descricao, criado_em FROM registros WHERE id = ?",
            (registro_id,),
        ).fetchone()
        return dict(linha) if linha else None

    def criar(self, dados: RegistroCreate) -> dict:
        cursor = self.conn.execute(
            "INSERT INTO registros (titulo, descricao) VALUES (?, ?)",
            (dados.titulo, dados.descricao),
        )
        self.conn.commit()
        return self.buscar_por_id(cursor.lastrowid)

    def atualizar(self, registro_id: int, dados: RegistroUpdate) -> dict | None:
        if self.buscar_por_id(registro_id) is None:
            return None

        alteracoes = {
            campo: valor
            for campo, valor in dados.model_dump(exclude_unset=True).items()
            if campo in CAMPOS_EDITAVEIS
        }
        if alteracoes:
            set_clause = ", ".join(f"{campo} = ?" for campo in alteracoes)
            self.conn.execute(
                f"UPDATE registros SET {set_clause} WHERE id = ?",
                (*alteracoes.values(), registro_id),
            )
            self.conn.commit()
        return self.buscar_por_id(registro_id)

    def remover(self, registro_id: int) -> bool:
        cursor = self.conn.execute("DELETE FROM registros WHERE id = ?", (registro_id,))
        self.conn.commit()
        return cursor.rowcount > 0
