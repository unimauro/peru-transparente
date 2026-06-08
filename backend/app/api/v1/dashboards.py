"""Endpoints de dashboards (leen vistas materializadas de analytics)."""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


@router.get("/national")
async def national(db: AsyncSession = Depends(get_db)):
    """KPIs del Dashboard Ejecutivo Nacional."""
    row = (await db.execute(text("SELECT * FROM analytics.national_kpis"))).mappings().first()
    return dict(row) if row else {}


@router.get("/officials-by-sector")
async def officials_by_sector(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(text("SELECT * FROM analytics.officials_by_sector"))).mappings().all()
    return {"items": [dict(r) for r in rows]}


@router.get("/salary-by-entity")
async def salary_by_entity(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(text(
        "SELECT * FROM analytics.salary_by_entity ORDER BY median_salary DESC NULLS LAST LIMIT 100"
    ))).mappings().all()
    return {"items": [dict(r) for r in rows]}


@router.get("/recent-appointments")
async def recent_appointments(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(text("SELECT * FROM analytics.recent_appointments LIMIT 100"))).mappings().all()
    return {"items": [dict(r) for r in rows]}
