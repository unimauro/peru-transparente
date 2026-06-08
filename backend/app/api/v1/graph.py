"""Endpoints del grafo nacional de poder."""
from fastapi import APIRouter, Query

from app.graph import neo4j_client
from app.schemas.common import GraphResponse

router = APIRouter(prefix="/graph", tags=["grafo"])


@router.get("/neighborhood/{node_id}", response_model=GraphResponse)
async def neighborhood(node_id: str, depth: int = Query(2, ge=1, le=3), limit: int = Query(300, le=1000)):
    """Vecindario de un nodo (persona/entidad/empresa/contrato) para visualización."""
    return await neo4j_client.get_neighborhood(node_id, depth=depth, limit=limit)


@router.get("/path", response_model=GraphResponse)
async def path(a: str, b: str, max_len: int = Query(6, ge=1, le=8)):
    """Ruta de poder más corta entre dos nodos: ¿cómo se conectan?"""
    return await neo4j_client.shortest_path(a, b, max_len=max_len)
