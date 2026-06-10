# Flujo del pipeline — Perú Transparente

Cómo fluye el dato desde las fuentes oficiales hasta el sitio. **Estático-primero**: los
scrapers producen CSV → unos scripts los convierten en JSON → el frontend (React) los lee
sin backend. Todo versionado en git y desplegado en GitHub Pages.

```mermaid
flowchart TD
    subgraph F["1 · FUENTES OFICIALES"]
        PTE["PTE · transparencia.gob.pe<br/>(planilla por entidad/régimen/página)"]
        GOB["gob.pe<br/>(directorio de autoridades)"]
        OCDS["OECE / OCDS<br/>(contrataciones)"]
        AIR["AIRHSP · MEF<br/>(planilla agregada, sin nombres)"]
    end

    subgraph S["2 · SCRAPERS (Python)"]
        sc_cat["descargar_catalogo.py<br/>→ entidades.csv (2 308)"]
        sc_fun["scrape_funcionarios.py<br/>→ funcionarios.csv (foto 2026)"]
        sc_his["scrape_historico.py<br/>→ funcionarios_historico.csv (2015-2024)"]
        sc_aut["scrape_autoridades.py<br/>→ autoridades.csv (5 637)"]
        sc_air["procesar_airhsp.py<br/>→ airhsp_*.csv"]
    end

    subgraph P["3 · PROCESAMIENTO (Python)"]
        merge["merge_funcionarios.py<br/>(consolida shards)"]
        dedup["deduplicar.py<br/>(quita planilla padre/hijo)"]
        bsd["build_site_data.py<br/>(KPIs, entidades, organigrama ROF, regiones, meta)"]
        bper["build_personas.py<br/>(índice + trayectoria, shards por letra)"]
        bred["build_redes.py<br/>(grafo institucional)"]
        bsal["build_salarios.py<br/>(dashboard salarial)"]
        bog["build_og_sections.py<br/>(OG + stubs por sección)"]
    end

    subgraph D["4 · DATOS ESTÁTICOS (frontend/public/data)"]
        json["national_kpis · entidades · meta<br/>funcionarios_sample · entidad/&lt;id&gt;<br/>personas/&lt;letra&gt; · personas_red<br/>redes_entidades · regiones · autoridades<br/>airhsp · salarios · jerarquia_estado"]
    end

    subgraph W["5 · FRONTEND + DEPLOY"]
        spa["React + Vite (SPA)"]
        pages["GitHub Pages (CI deploy-pages.yml)"]
    end

    PTE --> sc_cat & sc_fun & sc_his
    GOB --> sc_aut
    AIR --> sc_air
    OCDS -.-> P

    sc_fun --> merge --> dedup --> bsd
    sc_his --> bper
    sc_cat --> bsd
    sc_aut --> bsd
    sc_air --> bsd
    dedup --> bper & bsal
    bper --> bred
    bsd & bper & bred & bsal & bog --> json
    json --> spa --> pages

    classDef src fill:#1b2430,stroke:#56627a,color:#cdd8e6
    classDef py fill:#16331f,stroke:#22c55e,color:#e6edf6
    classDef out fill:#0d1f3a,stroke:#4f8cff,color:#e6edf6
    class PTE,GOB,OCDS,AIR src
    class sc_cat,sc_fun,sc_his,sc_aut,sc_air,merge,dedup,bsd,bper,bred,bsal,bog py
    class json,spa,pages out
```

## Orden de ejecución (de cero a sitio)

| # | Comando | Produce |
|---|---|---|
| 1 | `python scripts/descargar_catalogo.py` | `data/entidades.csv` (universo 2 308, ordenado por prioridad) |
| 2 | `python scripts/scrape_funcionarios.py --ids-file data/entidades.csv --year 2026 --resume` | `data/funcionarios.csv` (planilla actual, nominal) |
| 3 | `python scripts/scrape_autoridades.py --resume` | `data/autoridades.csv` (rectores, ministros… de gob.pe) |
| 4 | `python scripts/scrape_historico.py --ids-file data/_con_datos.csv --years 2024,2021,2018,2015` | `data/funcionarios_historico.csv` (trayectorias) |
| 5 | `python scripts/procesar_airhsp.py` | `data/airhsp_*.csv` (cobertura total agregada del MEF) |
| 6 | `python scripts/merge_funcionarios.py` | consolida shards de workers en `funcionarios.csv` |
| 7 | `python scripts/deduplicar.py` | quita planillas duplicadas (entidad hijo = planilla del padre) |
| 8 | `python scripts/build_site_data.py` | KPIs, entidades, **organigrama por órganos (ROF)**, regiones, autoridades, airhsp, meta |
| 9 | `python scripts/build_personas.py` | índice de personas + **trayectoria** (shards por letra) |
| 10 | `python scripts/build_redes.py` | grafo institucional (entidades unidas por personas) |
| 11 | `python scripts/build_salarios.py` | `salarios.json` (distribución, top, por régimen) |
| 12 | `python scripts/build_og_sections.py` | imágenes OG + stubs HTML por sección |
| 13 | `cd frontend && npm run build` | `dist/` (SPA) |
| 14 | `git push` → CI `deploy-pages.yml` | publica en GitHub Pages |

## Ideas clave del diseño
- **Idempotencia y resumible:** cada scraper tiene checkpoint (`.checkpoint.json`); re-ejecutar continúa donde quedó.
- **Dedup honesto:** algunas entidades del PTE devuelven la planilla de su "padre" → se detectan por huella y se marcan "planilla compartida".
- **Estático-primero:** el 100% del sitio se sirve como JSON desde Pages (sin servidor). El CSV completo se versiona comprimido (`.gz`).
- **Anti-overclaiming:** todo dato lleva su fuente; las inferencias (vínculos por nombre) se marcan como hipótesis, no afirmaciones.

## Hacia la base de datos (siguiente fase)
El esquema y el cargador ya están listos en [`db/supabase/schema.sql`](../db/supabase/schema.sql) y
[`scripts/load_supabase.py`](../scripts/load_supabase.py): con la cadena de conexión, se cargan
`entidades` + `funcionarios` + `autoridades` y queda la función `buscar_persona()` (full-text + fuzzy).
Eso reemplaza los JSON grandes (~256 MB hoy) por consultas en vivo.
```
fuentes → scrapers (CSV) → [Postgres/Supabase] → API → frontend
                                ↑ aquí entra la BD, sustituyendo los JSON estáticos pesados
```
