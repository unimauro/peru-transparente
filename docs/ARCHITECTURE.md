# Arquitectura — Perú Transparente

## 1. Principios de diseño

1. **Datos como código.** El estado canónico se versiona. Snapshots reproducibles y auditables.
2. **Trazabilidad total.** Cada celda de dato lleva `source`, `source_url`, `captured_at`, `confidence`. Sin fuente, no entra.
3. **Estático primero.** El frontend consume JSON estático generado por el pipeline (servido por GitHub Pages + CDN). El backend dinámico es para grafo en vivo, búsqueda semántica y exportaciones grandes.
4. **Anti-overclaiming.** El sistema vincula y describe; no acusa. Las inferencias se etiquetan como hipótesis con confianza.
5. **Idempotencia e incrementalidad.** Re-ejecutar un scraper no duplica; solo aplica deltas.
6. **Modular y federable.** Cada fuente es un *connector* independiente y desplegable por separado.

## 2. Vista de capas

```
┌────────────────────────────────────────────────────────────────────────┐
│ L5  PRESENTACIÓN     React + TS + Vite + Tailwind  (GitHub Pages, SPA)    │
│     Viz: D3 · Cytoscape (grafo) · ECharts (dashboards) · MapLibre (mapas) │
├────────────────────────────────────────────────────────────────────────┤
│ L4  API              FastAPI:  REST (/api/v1)  +  GraphQL (/graphql)      │
│     Auth: OAuth/GitHub  ·  Rate-limit  ·  Cache (Redis)  ·  Export CSV/JSON│
├────────────────────────────────────────────────────────────────────────┤
│ L3  INTELIGENCIA     Entity Resolution · Link Detection · RAG/embeddings   │
│     Resúmenes (perfil funcionario/entidad) · Búsqueda semántica (pgvector) │
├────────────────────────────────────────────────────────────────────────┤
│ L2  ALMACENAMIENTO   PostgreSQL (canónico + pgvector)  ·  Neo4j (grafo)    │
│                      Redis (cache/colas)  ·  Object store (PDFs, DJ)       │
├────────────────────────────────────────────────────────────────────────┤
│ L1  PROCESAMIENTO    Airflow (orquestación) · normalización · dedupe       │
│                      validación (Great Expectations) · versionado SCD2     │
├────────────────────────────────────────────────────────────────────────┤
│ L0  INGESTA          Scrapy + Playwright (connectors) · clientes API OCDS  │
│                      detección de cambios · reintentos · logs estructurados │
└────────────────────────────────────────────────────────────────────────┘
```

## 3. Flujo de datos (end-to-end)

```
Fuente pública
   │  (1) Connector descarga HTML/PDF/API → RAW (inmutable, con hash + timestamp)
   ▼
RAW store (data/raw/<fuente>/<fecha>/…)   ──► detección de cambios (hash diff)
   │  (2) Parser → registros tipados (Pydantic) → STAGING
   ▼
STAGING (Postgres schema `staging`)
   │  (3) Validación (Great Expectations) → cuarentena si falla
   │  (4) Entity Resolution: ¿esta "persona/entidad" ya existe? (IA + reglas)
   ▼
CANONICAL (Postgres schema `core`, SCD2 historizado)
   │  (5) Proyección a grafo (CDC → Neo4j) + embeddings (pgvector)
   │  (6) Build estático: genera data/public/*.json (entidades, funcionarios, KPIs)
   ▼
SERVICIO: API dinámica  +  JSON estático en GitHub Pages/CDN
```

## 4. Componentes

### 4.1 Connectors (ingesta)
- Base común `BaseConnector` con: `fetch()`, `parse()`, `diff()`, `emit()`.
- Dos familias: **API** (OCDS/OECE, Datos Abiertos CKAN, SIAF) y **scraping** (PTE, Contraloría, FONAFE) con Scrapy + Playwright para JS pesado.
- Salida normalizada al *contrato de ingesta* (ver `db/postgres/02_staging.sql`).

### 4.2 ETL / Orquestación (Airflow)
- DAGs por fuente y frecuencia (diaria/semanal/mensual según volatilidad del dato).
- Tareas: `extract → validate → resolve_entities → upsert_canonical → project_graph → build_static`.
- Backfill histórico parametrizable por rango de fechas.

### 4.3 Almacenamiento
- **PostgreSQL** = verdad canónica. Esquemas `staging`, `core`, `meta` (procedencia), `analytics` (vistas materializadas para dashboards).
- **Neo4j** = grafo de poder, derivado de Postgres vía CDC. Nunca es fuente de verdad.
- **pgvector** = embeddings para búsqueda semántica y entity resolution.
- **Redis** = cache de respuestas API + colas ligeras.
- **Object store** (Cloudflare R2 / GitHub Releases) = PDFs de resoluciones y declaraciones juradas.

### 4.4 API (FastAPI)
- REST versionada `/api/v1/*` + GraphQL `/graphql` (Strawberry).
- Endpoints clave: entidades, funcionarios, designaciones, declaraciones, empresas, contratos, grafo (vecindario/rutas), búsqueda semántica, export.
- Auth opcional (OAuth/GitHub) solo para features avanzadas (guardar consultas, alertas); lectura pública sin login.

### 4.5 Capa de IA
- **Entity Resolution:** blocking + comparación (RapidFuzz) + verificación por embeddings + LLM como árbitro en casos dudosos.
- **Link Detection:** detecta personas repetidas, variaciones de nombre, co-ocurrencias entidad/contrato y *posibles* conflictos de interés (siempre como hipótesis).
- **Resúmenes:** perfiles de funcionario/entidad y resúmenes ejecutivos vía LLM con *grounding* estricto (solo datos presentes, citas a fuente).
- **Búsqueda semántica:** pgvector + reranking.
- Proveedores intercambiables (OpenAI / Gemini / Claude) tras una interfaz `LLMProvider`.

### 4.6 Frontend
- SPA React/Vite, ruteo hash-friendly para GitHub Pages.
- Consume JSON estático para listados/perfiles/dashboards; llama al backend solo para grafo en vivo y búsqueda semántica.
- Viz: **Cytoscape** (grafo de poder), **ECharts** (dashboards), **D3** (organigramas/árboles), **MapLibre** (mapas por región/distrito).

## 5. Decisiones arquitectónicas (ADR)
Ver `docs/adr/`. Resumen:
- **ADR-001** Postgres como fuente de verdad, Neo4j derivado.
- **ADR-002** Estático-primero para servir desde GitHub Pages.
- **ADR-003** SCD2 para historizar cargos/remuneraciones.
- **ADR-004** Provenance obligatorio a nivel de campo.
- **ADR-005** AGPL-3.0 para el código, CC BY 4.0 para datos.

## 6. Seguridad y privacidad
- Solo datos públicos; minimización de PII (sin DNI completo salvo lo que la fuente publica).
- Rate-limiting y WAF en el borde.
- Secret management vía variables de entorno / GitHub Secrets; nada de credenciales en el repo.
- Cumplimiento Ley 29733 y Ley 27806 (ver `docs/LEGAL.md`).
