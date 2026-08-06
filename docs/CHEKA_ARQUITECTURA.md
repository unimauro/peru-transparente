# cheka.app — Arquitectura del "Palantir cívico"

> Documento de arquitectura para revisión. **No toca infraestructura todavía.**
> Autor: build multiagente · Fecha: 2026-08-06 · Estado: propuesta

## 1. Idea en una frase

**Perú Transparente** es el *dataset abierto y la vitrina pública* (estática, gratis, imposible de tumbar).
**cheka.app** es la *herramienta de investigación* encima de ese dato: un lienzo de grafo para
seguir el dinero y las relaciones de poder — Palantir, pero cívico, abierto y con frenos éticos.

Mismo motor de datos, dos caras:

| | Perú Transparente | cheka.app |
|---|---|---|
| Rol | Consultar, buscar, compartir | Investigar, cruzar, guardar hallazgos |
| Público | Cualquiera, sin login | Periodistas, investigadores, ciudadanía (con cuenta para lo sensible) |
| Hosting | GitHub Pages (estático) | VPS Hostinger (Docker + Caddy) |
| Dato | JSON estático shardeado | Postgres (canónico) + Neo4j (grafo) + búsqueda |

## 2. Por qué hace falta un backend (y por qué no antes)

Lo estático nos ha llevado lejísimo y hay que **conservarlo** para la cara pública: 213k personas,
contratos, sanciones, DJ — todo se sirve como JSON shardeado por letra, cero servidores, cero costo.

Pero el "Palantir cívico" pide cosas que un sitio estático hace mal:

- **Grafo vivo navegable a profundidad**: persona ↔ entidad ↔ contrato ↔ proveedor ↔ sanción ↔
  DJ ↔ grupo económico. Expandir un nodo, encontrar caminos entre dos personas, detectar
  triángulos (funcionario que adjudica a un proveedor ligado a un familiar). Eso es **Neo4j**.
- **Entity resolution por DNI** cruzando 5+ fuentes: no cabe en shards; es cómputo por lotes.
- **Búsqueda semántica/fuzzy** sobre cientos de miles de nombres con homónimos.
- **Consultas sensibles con autenticación**: lo que expone DNI o cruces "quién-conoce-a-quién"
  no puede ser anónimo y público — responsabilidad legal (Ley 29733) y ética.

**Y ya está andamiado en el repo**: `backend/` (FastAPI), `docker-compose.yml` (Postgres pgvector +
Neo4j 5 + Redis + api), `db/` (esquemas), y el frontend ya trae `liveApi` en `lib/api.ts` listo para
hablarle vía `VITE_API_URL`. Este documento no inventa; conecta lo que ya existe.

## 3. Topología propuesta

```
                    ┌─────────────────────────────┐
   Público  ─────▶  │  GitHub Pages (estático)    │   unimauro.github.io/peru-transparente
   (sin login)      │  SPA + JSON shardeado        │   ← se queda igual, es la vitrina
                    └──────────────┬──────────────┘
                                   │  VITE_API_URL (opcional)
                                   ▼
                    ┌─────────────────────────────┐
   cheka.app  ────▶ │  VPS Hostinger · Docker      │   pt.tunky.net  (o api.cheka.app)
   (con cuenta)     │  ┌────────────────────────┐  │   Caddy → TLS automático
                    │  │ FastAPI (api:8000)     │  │
                    │  │  · /public/*  (abierto)│  │
                    │  │  · /q/*  (con token)   │  │   ← auth para lo sensible
                    │  ├────────────────────────┤  │
                    │  │ Postgres pgvector      │  │   canónico + embeddings búsqueda
                    │  │ Neo4j 5 community      │  │   grafo de poder
                    │  │ Redis                  │  │   cache + rate-limit
                    │  └────────────────────────┘  │
                    └──────────────▲──────────────┘
                                   │  ingest autenticado (POST /ingest, token)
                    ┌──────────────┴──────────────┐
   Laptop (IP PE) ─▶│ scrapers/*.py + actualizar.sh│   recolección desde IP residencial peruana
                    └─────────────────────────────┘   (el Estado bloquea datacenter)
```

Regla de oro del VPS (ver `reference_vps_hostinger`): Docker en **puerto libre nuevo**, bloque
Caddy propio, DNS A propio, **sin tocar** recuperamas/SFTP/correo/puerto 3000 ni los demás sitios.

## 4. Capa de datos

Tres representaciones del mismo dato, cada una para lo que sabe hacer:

1. **Postgres (pgvector)** — fuente canónica. Tablas `persona`, `entidad`, `cargo`, `contrato`,
   `sancion`, `dj`, `orden_servicio`, más `persona_identidad` (la tabla que resuelve el DNI).
   `pgvector` guarda embeddings de nombres para búsqueda fuzzy/semántica.
2. **Neo4j** — proyección en grafo para navegación y caminos. Nodos: `Persona`, `Entidad`,
   `Proveedor`, `Contrato`, `Sancion`, `GrupoEconomico`. Aristas: `TRABAJA_EN`, `ADJUDICA`,
   `PROVEE_A`, `SANCIONADO_POR`, `DECLARA`, `FAMILIAR_DE`, `MISMO_DNI`.
3. **JSON estático** — se sigue generando con los `build_*.py` para la vitrina pública. El backend
   *no reemplaza* esto; lo complementa. Si el VPS se cae, la cara pública sigue viva.

El pipeline **no cambia de lugar**: los scrapers corren en la laptop (IP peruana). Nuevo paso: tras
generar los CSV/JSON, `actualizar.sh` hace `POST /ingest` autenticado al VPS para refrescar
Postgres+Neo4j. Así el VPS nunca scrapea (evita el geobloqueo) y la laptop nunca expone puertos.

## 5. Entity resolution por DNI (el corazón — tarea #4)

Hoy el cruce entre fuentes es **por nombre normalizado** → homónimos (Perú tiene miles de QUISPE).
El salto de calidad es anclar en **DNI**. Fuentes que sí traen DNI:

- **Órdenes de servicio (OCDS)**: el RUC de persona natural embebe el DNI (`ruc[2:10]`). ✅ ya lo tenemos.
- **RNSSC (sanciones)**: trae DNI en el 100%. ✅ ya lo tenemos (crudo local, no publicado).
- **Bienes y Rentas (Ley 27482, Contraloría)**: el PDF de la Sección Segunda trae **DNI + patrimonio**
  (verificado: Boluarte 06256217, Otárola 09396443). Es la pieza que faltaba para las autoridades.

Estrategia:
1. Tabla `persona_identidad(dni, nombre_norm, fuente, confianza)`. Cada fuente con DNI puebla un
   ancla `(nombre_norm → dni)`.
2. La planilla (sin DNI) se une a un ancla **solo si** hay coincidencia de nombre **y** un segundo
   factor (misma entidad, o mismo período) → sube la confianza y baja el falso positivo por homónimo.
3. En el grafo, `MISMO_DNI` fusiona nodos; sin DNI, se mantiene la marca **"coincidencia por nombre,
   homónimo posible"** — nunca se afirma identidad sin ancla.

Esto alimenta el nodo `Persona` unificado del que cuelga toda su vida pública: cargos, sueldos,
contratos, sanciones, declaraciones — la vista "expediente" de cheka.app.

## 6. Autenticación y niveles de acceso

No todo es igual de sensible. Tres anillos:

- **Anillo 0 — público, sin login** (`/public/*`): lo mismo que ya es estático (agregados, KPIs,
  fichas con DNI enmascarado). Sirve a Perú Transparente y a la landing de cheka.
- **Anillo 1 — cuenta gratuita** (`/q/*` con token): grafo navegable, búsqueda avanzada, guardar
  investigaciones, exportar. Login propio (Google OAuth + JWT, patrón `reference_saas_patrones_lanzamiento`).
- **Anillo 2 — verificado** (periodista/investigador acreditado): cruces que exponen DNI completo o
  vínculos familiares. Auditado (`audit_log`: quién consultó qué), rate-limit, y aviso legal.

Base legal: la data es pública (Ley 27482 art.15, Ley 31227, OCDS), pero el **tratamiento y cruce**
cae bajo Ley 29733. Por eso: DNI enmascarado por defecto, DNI completo solo tras login+auditoría,
y páginas legales (términos, privacidad, "cómo verificar antes de afirmar").

## 7. Superficie de API (borrador)

```
GET  /public/kpis                      → agregados (abierto)
GET  /public/persona/:nombre           → ficha pública, DNI enmascarado (abierto)
POST /q/search        {q, tipo}        → búsqueda fuzzy/semántica (token)
GET  /q/graph/:nodeId?depth=2          → vecindario en Neo4j (token)
GET  /q/path?a=&b=                     → camino entre dos nodos (token)
GET  /q/persona/:dni/expediente        → vida pública unificada (Anillo 2, auditado)
POST /ingest          {tabla, filas}   → refresco desde la laptop (token de servicio)
```

El frontend ya espera exactamente esto: `liveApi.neighborhood()`, `liveApi.path()` en `lib/api.ts`.

## 8. Hoja de ruta por fases

- **Fase 0 — este doc.** Arquitectura acordada. ✅
- **Fase 1 — cerebro mínimo en el VPS.** Levantar `docker-compose` en `pt.tunky.net` (Caddy+token),
  cargar Postgres desde los CSV que ya generamos, exponer `/public/*` y `/q/search`. Sin grafo aún.
- **Fase 2 — grafo.** Proyectar a Neo4j, encender `/q/graph` y `/q/path`, y el lienzo de cheka.app.
- **Fase 3 — entity resolution por DNI.** Scraper de Bienes y Rentas (Sistema A, Ley 27482) + tabla
  `persona_identidad` + fusión `MISMO_DNI`. Convierte "coincidencia por nombre" en identidad anclada.
- **Fase 4 — cheka.app como producto.** Cuentas, investigaciones guardadas, exportes, copiloto IA
  (vía `ai.tunky.net`), y el cruce con `observatorio-poder-economico` (grupos económicos).

## 9. Riesgos y frenos (honestidad primero)

- **VPS compartido**: no romper otros sitios. Puerto nuevo + Caddy propio + DNS propio, nada más.
- **Geobloqueo**: el VPS NO scrapea; la laptop recolecta y hace `POST /ingest`. Igual que hoy.
- **Homónimos**: sin DNI no se afirma identidad. La UI marca siempre "coincidencia por nombre".
- **PII / Ley 29733**: DNI enmascarado por defecto; DNI completo solo tras login + auditoría.
- **Anti-overclaiming**: "concentración", "también en planilla", "posible sanción" son **señales**,
  no acusaciones. Todo trazable a la fuente. cheka.app muestra evidencia, no veredictos.
- **Costo/ops**: Docker en el VPS que ya pagas; Neo4j community y Postgres caben de sobra para este
  volumen. Backup diario en bind-mount (nunca `docker compose down -v`).

## 10. Decisiones tomadas (2026-08-06) + recon del VPS

**Subdominios acordados** (empezamos en tunky; migramos a `cheka.app` cuando haya presupuesto):
- **`cheka.tunky.net`** → el portal de investigación.
- **`apicheck.tunky.net`** → el API (el "cerebro").

**Recon del VPS (217.15.168.100, `srv646391.hstgr.cloud`):**
- Corren ~30 contenedores tuyos (convención: cada app en `127.0.0.1:34xx` detrás de Caddy). **No tocar ninguno.**
- **RAM: 7.8 Gi total, ~3.7 Gi disponible.** Ajustado. Neo4j es glotón → **Fase 1 sin Neo4j**
  (solo Postgres + API, ~0.7 Gi). El grafo entra en Fase 2 cuando optimicemos memoria o se justifique.
- **Puerto libre elegido: `127.0.0.1:3421`** para el API (Postgres/Redis quedan internos a la red Docker, sin puerto de host).
- **Caddy**: un `Caddyfile` con un bloque por sitio. Se **agrega** un bloque nuevo (aditivo, reversible), no se edita nada.
- **DNS de tunky.net está en Hostinger** (`ns1/ns2.dns-parking.com`) → las A se crean en el panel de Hostinger.
  Es el **único paso que depende de ti**: dos registros A `apicheck` y `cheka` → `217.15.168.100`.

**Auth Fase 1**: solo **token de servicio** para `/ingest` (la laptop empuja datos). Login de usuarios en Fase 2.

**Kit de deploy listo** en `deploy/cheka/` (compose de producción, bloque Caddy, `.env.example`, README con los
pasos exactos). Fase 1 se ejecuta en un comando **apenas estén las 2 DNS**; no toca ningún otro sitio del VPS.
