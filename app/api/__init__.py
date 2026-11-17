"""Controladores modulares: junta os routers de cada recurso em um só."""

from fastapi import APIRouter

from app.api.routes import registros

api_router = APIRouter()
api_router.include_router(registros.router)
