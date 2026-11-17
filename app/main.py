"""Ponto de entrada: cria a aplicação, registra middlewares e rotas."""

import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.api import api_router
from app.core.database import init_db

# Nome da instância (útil para ver o balanceamento de carga do Nginx funcionando)
INSTANCIA = os.getenv("INSTANCIA", f"pid-{os.getpid()}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # cria as tabelas na subida
    yield


app = FastAPI(
    title="API de Registros – Sistemas Distribuídos",
    description="FastAPI + Uvicorn atrás de um proxy reverso Nginx.",
    version="0.2.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def tempo_de_processamento(request: Request, call_next):
    """Mede o tempo de cada requisição e informa qual instância respondeu."""
    inicio = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{time.perf_counter() - inicio:.4f}"
    response.headers["X-Instancia"] = INSTANCIA
    return response


@app.get("/", tags=["Status"])
def raiz():
    return {"mensagem": "API no ar", "docs": "/docs"}


@app.get("/health", tags=["Status"])
def health():
    return {"status": "ok", "instancia": INSTANCIA}


@app.get("/info", tags=["Status"])
def info(request: Request):
    """Mostra como a requisição chegou: direto no Uvicorn ou passando pelo Nginx."""
    return {
        "instancia": INSTANCIA,
        "ip_cliente": request.client.host if request.client else None,
        "esquema": request.url.scheme,
        "x_real_ip": request.headers.get("x-real-ip"),
        "x_forwarded_for": request.headers.get("x-forwarded-for"),
        "x_forwarded_proto": request.headers.get("x-forwarded-proto"),
        "passou_pelo_nginx": request.headers.get("x-real-ip") is not None,
    }


app.include_router(api_router)
