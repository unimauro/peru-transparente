# Cómo contribuir a Perú Transparente

¡Gracias por sumarte! Este es un proyecto cívico open source. Buscamos rigor técnico y respeto absoluto por la trazabilidad y el principio anti-overclaiming.

## Formas de contribuir
1. **Nuevos connectors** (la prioridad). Implementa una fuente de `docs/SCRAPING_STRATEGY.md` siguiendo `scrapers/peru_transparente/base.py`.
2. **Calidad de datos.** Mejorar entity resolution, validaciones, reglas.
3. **Frontend.** Dashboards, vistas, accesibilidad (ver `docs/UI_UX.md`).
4. **Correcciones de datos.** Reportar un dato erróneo con su fuente (issue/PR).

## Reglas de oro
- **Trazabilidad:** todo dato nuevo debe traer procedencia (fuente, URL, fecha, confianza). PRs sin provenance no se aceptan.
- **Anti-overclaiming:** nada de afirmar irregularidades. Inferencias = hipótesis etiquetadas con confianza.
- **Solo datos públicos.** Respetar Ley 29733 y `docs/LEGAL.md`.
- **Ética de scraping:** robots.txt, rate-limit, User-Agent honesto (`docs/SCRAPING_STRATEGY.md §3`).

## Flujo de trabajo
1. Fork + rama desde `develop` (`feat/connector-pte`, `fix/...`).
2. `docker compose up` para el stack local.
3. Backend: `ruff check` + `pytest`. Frontend: `npm run build`.
4. PR a `develop` con descripción y, si toca datos, ejemplo de salida con provenance.

## Estructura
Ver `README.md` §Monorepo. Cada subproyecto (`backend/`, `scrapers/`, `frontend/`) es instalable de forma independiente.

## Código de conducta
Trato respetuoso, foco en datos y evidencia. Cero tolerancia al uso de la plataforma para acoso o difamación.
