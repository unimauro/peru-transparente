# Guía del repositorio — Perú Transparente

Monorepo de una plataforma de transparencia pública del Perú. Lee `README.md` y `docs/ARCHITECTURE.md` antes de cambios grandes.

## Estructura
- `backend/` — FastAPI (REST `/api/v1` + GraphQL). Tests con pytest, lint con ruff.
- `scrapers/` — connectors de ingesta (Scrapy/Playwright/API). Base: `peru_transparente/base.py`.
- `etl/` — build estático + DAGs Airflow.
- `db/postgres/` — esquemas canónico/staging/analytics. `db/neo4j/` — grafo.
- `frontend/` — React+TS+Vite+Tailwind. SPA en GitHub Pages (HashRouter, base `/peru-transparente/`).
- `data/` y `frontend/public/data/` — JSON estático servido al frontend.

## Principios no negociables
1. **Trazabilidad:** todo dato lleva procedencia (fuente, URL, fecha, confianza). Ver `meta.provenance`.
2. **Anti-overclaiming:** no afirmar irregularidades; inferencias IA = hipótesis con confianza (`POSSIBLE_*`).
3. **Estático-primero:** preferir JSON pre-renderizado; backend solo para grafo/búsqueda/exports.
4. **Solo datos públicos** (Ley 29733 / Ley 27806). Ver `docs/LEGAL.md`.

## Comandos
- Stack local: `docker compose up`
- Backend: `cd backend && pip install -e ".[dev]" && uvicorn app.main:app --reload`
- Frontend: `cd frontend && npm install && npm run dev`
- Pipeline: `python scripts/run_pipeline.py --source osce && python etl/build_static.py`

## Convenciones git
- Commits en español, imperativo. Sin co-autores. No mencionar herramientas de IA en materiales públicos.
