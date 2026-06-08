"""Punto de entrada de la API de Perú Transparente."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import contracts, dashboards, entities, graph, officials
from app.core.config import get_settings
from app.graph import neo4j_client

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await neo4j_client.close()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API abierta de transparencia, datos públicos y grafo de poder del Perú.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
app.include_router(entities.router, prefix=API_PREFIX)
app.include_router(officials.router, prefix=API_PREFIX)
app.include_router(contracts.router, prefix=API_PREFIX)
app.include_router(dashboards.router, prefix=API_PREFIX)
app.include_router(graph.router, prefix=API_PREFIX)


@app.get("/health", tags=["sistema"])
async def health():
    return {"status": "ok", "service": settings.app_name, "env": settings.environment}
