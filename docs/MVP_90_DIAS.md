# MVP — 90 días

**Objetivo:** una plataforma pública, en GitHub Pages, que ya sea útil — con datos reales, trazables y exportables — sobre **entidades, empresas estatales (FONAFE) y contrataciones (OSCE/OECE)**, más un grafo navegable básico. Se eligen estas fuentes porque tienen **API o HTML estable** y alto valor.

## Alcance (lo que SÍ entra)
1. **Catálogo de entidades** (desde Datos Abiertos + FONAFE): nombre, sigla, sector, tipo, nivel, portal, portal de transparencia.
2. **Empresas del Estado (FONAFE)**: directorio y gerencias (persona ↔ empresa con vigencia).
3. **Contrataciones (OCDS OSCE/OECE)**: contratos, proveedores, monto, fecha, entidad contratante.
4. **Perfiles**: entidad y funcionario/director (con historial básico).
5. **Grafo básico** (Cytoscape): persona ↔ empresa ↔ contrato ↔ proveedor.
6. **Dashboard Ejecutivo Nacional** (ECharts): totales de entidades, empresas, contratos, monto.
7. **Export**: CSV/JSON por cada vista + API REST v1 de solo lectura.
8. **Trazabilidad**: cada dato muestra fuente, URL y fecha de captura.

## Fuera de alcance (post-MVP)
- Declaraciones juradas (Contraloría), remuneraciones detalladas (PTE), presupuestos (SIAF), IA de conflictos de interés, GraphQL, alertas.

## Plan semana a semana

| Semana | Hito |
|---|---|
| 1 | Repo, CI/CD, Docker Compose, esquemas Postgres/Neo4j, contrato de ingesta. |
| 2–3 | Connector **OCDS OSCE/OECE** (contratos + proveedores) con backfill. |
| 4 | Connector **FONAFE** (empresas + directorios) + **Datos Abiertos** (entidades). |
| 5 | Entity Resolution v1 + carga canónica + provenance. |
| 6 | Proyección a Neo4j + script de build estático (`data/public/*.json`). |
| 7 | API FastAPI v1 (entidades, empresas, contratos, búsqueda) + tests. |
| 8 | Frontend: layout, directorio de entidades, perfil de entidad. |
| 9 | Frontend: perfil de funcionario/director + grafo Cytoscape básico. |
| 10 | Dashboard Ejecutivo Nacional (ECharts) + export CSV/JSON. |
| 11 | Pulido UI/UX, accesibilidad, responsive, SEO, página de metodología. |
| 12 | Hardening, documentación, datos de cobertura, **lanzamiento público**. |

## Criterios de aceptación
- [ ] El sitio carga en GitHub Pages sin backend para listados y perfiles (JSON estático).
- [ ] Todo dato visible tiene fuente + URL + fecha de captura.
- [ ] Export CSV/JSON funcional en cada vista.
- [ ] Scrapers re-ejecutables (idempotentes) vía GitHub Actions cron.
- [ ] ≥ 5,000 contratos y ≥ 35 empresas FONAFE cargados con procedencia.
