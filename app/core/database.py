"""Infraestrutura central: conexão com o SQLite e inicialização do banco."""

import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path

# O arquivo do banco fica na raiz do projeto (pode ser trocado pela variável DATABASE_PATH)
BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.getenv("DATABASE_PATH", BASE_DIR / "registros.db"))


def get_connection() -> sqlite3.Connection:
    """Abre uma conexão nova com o banco, retornando as linhas como dicionários."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def get_db() -> Iterator[sqlite3.Connection]:
    """Dependência do FastAPI: uma conexão por requisição, fechada ao final."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Cria as tabelas caso ainda não existam (executado na subida da aplicação)."""
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS registros (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo    TEXT    NOT NULL,
                descricao TEXT,
                criado_em TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        conn.commit()
    finally:
        conn.close()
