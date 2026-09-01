"""Endpoints del HISTÓRICO temporal (esquema `historico` en Postgres).

Lectura de la serie que vive en el VPS: sueldos por persona/entidad/periodo, designaciones
de El Peruano y cambios de puesto en el tiempo. Solo lectura, solo datos públicos.
Ver esquema en db/postgres/04_historico.sql y la carga en scripts/load_historico.py.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter(prefix="/historico", tags=["historico"])


@router.get("/estado")
async def estado(db: AsyncSession = Depends(get_db)):
    """Salud del histórico: cuánto hay cargado y cuándo fue la última carga ('cómo va')."""
    resumen = (await db.execute(text("""
        SELECT (SELECT count(*) FROM historico.planilla)                     AS planilla_filas,
               (SELECT count(DISTINCT persona_norm) FROM historico.planilla) AS personas,
               (SELECT min(anio) FROM historico.planilla WHERE anio > 0)     AS anio_min,
               (SELECT max(anio) FROM historico.planilla WHERE anio > 0)     AS anio_max,
               (SELECT count(*) FROM historico.designacion)                  AS designaciones
    """))).mappings().first()
    cargas = (await db.execute(text("""
        SELECT fuente, archivo, filas_leidas, filas_carga, inicio, fin, estado
        FROM historico.carga ORDER BY id DESC LIMIT 5
    """))).mappings().all()
    return {"resumen": dict(resumen), "ultimas_cargas": [dict(c) for c in cargas]}


@router.get("/personas")
async def buscar_personas(
    q: str | None = Query(None, description="nombre o parte del nombre"),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Busca personas por nombre; devuelve su registro más reciente en planilla."""
    rows = (await db.execute(text("""
        SELECT DISTINCT ON (persona_norm)
               persona_norm, persona, id_entidad, entidad, cargo, regimen, total, anio, mes
        FROM historico.planilla
        WHERE (CAST(:q AS text) IS NULL
               OR persona_norm ILIKE '%'||historico.norm(CAST(:q AS text))||'%')
        ORDER BY persona_norm, anio DESC, mes DESC
        LIMIT :limit
    """), {"q": q, "limit": limit})).mappings().all()
    return {"items": [dict(r) for r in rows]}


@router.get("/persona")
async def trayectoria(
    nombre: str = Query(..., description="nombre exacto o normalizado"),
    db: AsyncSession = Depends(get_db),
):
    """Trayectoria de una persona: sueldos por periodo y cambios de cargo/entidad."""
    serie = (await db.execute(text("""
        SELECT anio, mes, id_entidad, entidad, regimen, cargo, dependencia, total
        FROM historico.planilla
        WHERE persona_norm = historico.norm(CAST(:nombre AS text))
        ORDER BY anio, mes
    """), {"nombre": nombre})).mappings().all()
    cambios = (await db.execute(text("""
        SELECT periodo, entidad_prev, entidad_actual, cargo_prev, cargo_actual,
               total_prev, total_actual, cambio_cargo, cambio_entidad
        FROM historico.v_cambio_puesto
        WHERE persona_norm = historico.norm(CAST(:nombre AS text))
        ORDER BY periodo
    """), {"nombre": nombre})).mappings().all()
    return {
        "nombre": nombre,
        "periodos": [dict(r) for r in serie],
        "cambios_puesto": [dict(c) for c in cambios],
    }


@router.get("/designaciones")
async def designaciones(
    desde: str | None = Query(None, description="fecha aaaa-mm-dd (inclusive)"),
    q: str | None = Query(None, description="cargo o entidad"),
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Designaciones/nombramientos de El Peruano, con fecha y norma."""
    rows = (await db.execute(text("""
        SELECT fecha, entidad, cargo, nombre, norma, fuente_url
        FROM historico.designacion
        WHERE (CAST(:desde AS date) IS NULL OR fecha >= CAST(:desde AS date))
          AND (CAST(:q AS text) IS NULL
               OR cargo_norm ILIKE '%'||historico.norm(CAST(:q AS text))||'%'
               OR entidad    ILIKE '%'||CAST(:q AS text)||'%')
        ORDER BY fecha DESC NULLS LAST
        LIMIT :limit
    """), {"desde": desde, "q": q, "limit": limit})).mappings().all()
    return {"items": [dict(r) for r in rows]}
