# Escalabilidad nacional — 100k+ funcionarios, millones de registros

## 1. Metas de volumen
- **Funcionarios:** 100,000+ activos + cientos de miles históricos.
- **Entidades:** ~3,000 (nacional + ~25 GR + ~1,900 municipalidades + OPD/empresas).
- **Contratos (OCDS):** millones desde 2017.
- **Declaraciones juradas:** cientos de miles.
- **Aristas del grafo:** decenas de millones.

## 2. Estrategias por capa

### Ingesta
- Connectors paralelizables e independientes; particionado por fuente y por rango temporal.
- Incremental por defecto: solo deltas, no full-scan diario.
- Backfill histórico por lotes acotados (evita golpear las fuentes).

### PostgreSQL (canónico)
- **Particionado** de tablas grandes (`contract`, `appointment`, `provenance`) por año/fuente.
- Índices selectivos (RUC, OCID, normalized_name, ubigeo) + índices parciales para `is_current`.
- **Vistas materializadas** en `analytics` para KPIs de dashboards (refresco incremental).
- `COPY` masivo en cargas; `UNLOGGED` en staging.
- pgvector con índice HNSW para búsqueda semántica a escala.

### Neo4j (grafo)
- Cargas por lote con `apoc.periodic.iterate`.
- Consultas acotadas (`LIMIT`, profundidad ≤ 2–3 saltos) en la API en vivo.
- Pre-cálculo de centralidades/comunidades offline (GDS) → propiedades de nodo cacheadas.

### Servir (estático-primero)
- El 90% de las vistas se sirven como **JSON estático** generado por el pipeline (GitHub Pages + CDN). El tráfico de lectura no toca la BD.
- Paginación y *facets* pre-computados por dashboard.
- Backend dinámico solo para: grafo en vivo, búsqueda semántica, exportaciones grandes.

### Cache
- Redis (Upstash) para respuestas API calientes y resultados de grafo.
- Cache-Control / ETag en JSON estático (inmutable + hash en el nombre).

## 3. Particionado de datos por territorio
- Indexado por **ubigeo** (INEI) → permite servir/escalar por región y municipalidad de forma independiente.
- Datasets estáticos por región para que los GR/municipios se puedan consumir aislados.

## 4. Rendimiento del frontend
- Virtualización de listas largas; carga diferida de JSON por sección.
- Grafo: renderizado incremental, expansión bajo demanda (no cargar millones de nodos de golpe).
- Mapas: teselas vectoriales (MapLibre) + agregación por nivel de zoom.

## 5. Plan de crecimiento de costos
Ver `INFRASTRUCTURE.md` §2: de US$ 0 (MVP, todo free-tier) a US$ 150–400/mes en escala nacional, manteniendo lectura barata por la arquitectura estático-primero.

## 6. Camino crítico para 100k funcionarios
1. PTE connector robusto (mayor fuente de funcionarios) con paralelismo por entidad.
2. Entity Resolution eficiente (blocking) para no comparar todos contra todos.
3. Particionado + materialized views antes de pasar de ~1M filas.
4. Migrar API de free-tier a contenedor con autoscale cuando p95 > umbral.
