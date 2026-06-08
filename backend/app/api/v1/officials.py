"""Endpoints de funcionarios (personas + historial de cargos)."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter(prefix="/officials", tags=["funcionarios"])


@router.get("")
async def list_officials(
    q: str | None = None,
    entity_id: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    sql = """
        SELECT DISTINCT p.id, p.full_name, pos.title AS current_position, e.name AS entity
        FROM core.person p
        JOIN core.appointment a ON a.person_id = p.id AND a.is_current
        JOIN core.position pos ON pos.id = a.position_id
        JOIN core.entity e ON e.id = a.entity_id
        WHERE (:q IS NULL OR p.normalized_name ILIKE '%'||upper(:q)||'%')
          AND (:entity_id IS NULL OR e.id = :entity_id)
        ORDER BY p.full_name
        LIMIT :limit OFFSET :offset
    """
    rows = (await db.execute(text(sql), {
        "q": q, "entity_id": entity_id, "limit": limit, "offset": offset
    })).mappings().all()
    return {"items": [dict(r) for r in rows]}


@router.get("/{person_id}")
async def get_official(person_id: str, db: AsyncSession = Depends(get_db)):
    """Perfil con historial de cargos (SCD2) y declaraciones."""
    person = (await db.execute(text(
        "SELECT id, full_name, doc_type FROM core.person WHERE id=:id"
    ), {"id": person_id})).mappings().first()
    if not person:
        raise HTTPException(404, "Funcionario no encontrado")

    history = (await db.execute(text("""
        SELECT a.start_date, a.end_date, a.status, a.remuneration_amount,
               a.appointment_resolution, a.appointment_res_url,
               pos.title AS position, e.name AS entity
        FROM core.appointment a
        JOIN core.position pos ON pos.id = a.position_id
        JOIN core.entity e ON e.id = a.entity_id
        WHERE a.person_id = :id
        ORDER BY a.start_date DESC
    """), {"id": person_id})).mappings().all()

    declarations = (await db.execute(text("""
        SELECT period, presented_at, assets_total, income_total, source_url
        FROM core.asset_declaration WHERE person_id = :id ORDER BY period DESC
    """), {"id": person_id})).mappings().all()

    return {
        **dict(person),
        "career_history": [dict(h) for h in history],
        "declarations": [dict(d) for d in declarations],
    }
