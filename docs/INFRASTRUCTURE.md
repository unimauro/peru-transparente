# Infraestructura — Perú Transparente

## 1. Diagrama de despliegue (free / low-cost)

```
                              ┌────────────────────────────────────────────┐
   Usuarios ───────────────▶ │  GitHub Pages (SPA React)  +  jsDelivr CDN   │
                              │  data/public/*.json (entidades, KPIs, perfiles)│
                              └───────────────┬────────────────────────────┘
                                              │ fetch dinámico (grafo, búsqueda)
                                              ▼
                              ┌────────────────────────────────────────────┐
                              │  API FastAPI  (Fly.io / Render / Cloud Run) │
                              │  REST /api/v1  ·  GraphQL  ·  OAuth GitHub   │
                              └───┬───────────────┬───────────────┬─────────┘
                                  │               │               │
                     ┌────────────▼──┐   ┌────────▼───────┐  ┌────▼─────────┐
                     │ PostgreSQL    │   │ Neo4j AuraDB   │  │ Upstash Redis │
                     │ +pgvector     │   │ Free           │  │ (cache)       │
                     │ (Supabase/Neon)│  └────────────────┘  └──────────────┘
                     └───────▲───────┘
                             │ upsert canónico
              ┌──────────────┴───────────────┐
              │  Airflow / GitHub Actions cron│  ◀── orquesta scrapers + ETL + build estático
              └──────────────┬───────────────┘
                             │ raw + PDFs
                     ┌───────▼────────┐
                     │ Cloudflare R2 / │
                     │ GitHub Releases │  (almacén de PDFs, declaraciones, snapshots RAW)
                     └─────────────────┘
```

## 2. Estimación de costos

| Etapa | Servicios | Costo mensual aprox. |
|---|---|---|
| **MVP** | GitHub Pages + Actions + Supabase free + Neo4j Aura free + Upstash free | **US$ 0** |
| **Crecimiento** | Fly.io API (1x shared-cpu) + Supabase Pro + Neo4j Aura Pro | US$ 25–80 |
| **Nacional** | Cloud Run autoscale + Postgres dedicado + Neo4j cluster + R2 | US$ 150–400 |

La arquitectura *estático-primero* mantiene el costo casi nulo mientras el volumen de lectura crece, porque GitHub Pages + CDN absorben el tráfico.

## 3. Entornos
- **dev** — Docker Compose local (`docker compose up`).
- **staging** — rama `develop` → preview en Pages + API en Fly.io app `pt-staging`.
- **prod** — rama `main` → Pages producción + API `pt-prod`.

## 4. Observabilidad
- Logs estructurados (JSON) → stdout → Fly/Render log drains.
- Métricas de scrapers (registros nuevos/cambiados/fallidos) → tabla `meta.scrape_run` + badge en el sitio.
- Healthchecks: `/health` (API), `/health/db`, `/health/graph`.
- Alertas: GitHub Action falla → notificación; caída de fuente detectada → issue automático.

## 5. Seguridad
- Secretos en GitHub Secrets / variables de entorno del proveedor; nunca en el repo.
- Restricción de escritura a la BD canónica solo desde el pipeline.
- WAF / rate-limit en el borde de la API.
- Backups diarios de Postgres (pg_dump → R2) + dumps Neo4j semanales.
