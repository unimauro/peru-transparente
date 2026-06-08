"""Endpoints de contrataciones (OSCE/OECE) y empresas del Estado."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter(tags=["contrataciones"])


@router.get("/contracts")
async def list_contracts(
    entity_id: str | None = None,
    supplier_id: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    sql = """
        SELECT c.id, c.ocid, c.title, c.amount, c.currency, c.sign_date,
               e.name AS entity, sup.name AS supplier
        FROM core.contract c
        LEFT JOIN core.entity e ON e.id = c.entity_id
        LEFT JOIN core.supplier sup ON sup.id = c.supplier_id
        WHERE (:entity_id IS NULL OR c.entity_id = :entity_id)
          AND (:supplier_id IS NULL OR c.supplier_id = :supplier_id)
        ORDER BY c.sign_date DESC NULLS LAST
        LIMIT :limit OFFSET :offset
    """
    rows = (await db.execute(text(sql), {
        "entity_id": entity_id, "supplier_id": supplier_id, "limit": limit, "offset": offset
    })).mappings().all()
    return {"items": [dict(r) for r in rows]}


@router.get("/companies")
async def list_companies(db: AsyncSession = Depends(get_db)):
    """Empresas del Estado (FONAFE) con sus directorios."""
    rows = (await db.execute(text("""
        SELECT c.id, c.name, c.ruc, c.fonafe_classification, s.name AS sector
        FROM core.company c LEFT JOIN core.sector s ON s.id = c.sector_id
        ORDER BY c.name
    """))).mappings().all()
    return {"items": [dict(r) for r in rows]}
