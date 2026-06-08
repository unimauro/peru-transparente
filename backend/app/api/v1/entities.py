"""Endpoints de entidades públicas."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter(prefix="/entities", tags=["entidades"])


@router.get("")
async def list_entities(
    q: str | None = Query(None, description="Búsqueda por nombre/sigla"),
    sector: str | None = None,
    level: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Directorio paginado de entidades, con filtros por sector y nivel."""
    sql = """
        SELECT e.id, e.name, e.acronym, e.level, e.ubigeo, e.website,
               e.transparency_url, s.name AS sector
        FROM core.entity e
        LEFT JOIN core.sector s ON s.id = e.sector_id
        WHERE e.is_current
          AND (:q IS NULL OR e.name ILIKE '%'||:q||'%' OR e.acronym ILIKE '%'||:q||'%')
          AND (:sector IS NULL OR s.name = :sector)
          AND (:level IS NULL OR e.level = :level)
        ORDER BY e.name
        LIMIT :limit OFFSET :offset
    """
    rows = (await db.execute(text(sql), {
        "q": q, "sector": sector, "level": level, "limit": limit, "offset": offset
    })).mappings().all()
    return {"items": [dict(r) for r in rows], "limit": limit, "offset": offset}


@router.get("/{entity_id}")
async def get_entity(entity_id: str, db: AsyncSession = Depends(get_db)):
    """Perfil completo de una entidad con su procedencia."""
    sql = "SELECT * FROM core.entity WHERE id = :id"
    row = (await db.execute(text(sql), {"id": entity_id})).mappings().first()
    if not row:
        raise HTTPException(404, "Entidad no encontrada")
    prov = (await db.execute(text(
        "SELECT source, source_url, captured_at, updated_at, confidence, method "
        "FROM meta.provenance WHERE target_table='core.entity' AND target_id=:id"
    ), {"id": entity_id})).mappings().all()
    return {**dict(row), "provenance": [dict(p) for p in prov]}
