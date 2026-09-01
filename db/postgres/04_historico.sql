-- Perú Transparente — esquema HISTÓRICO (serie temporal para el VPS)
--
-- Objetivo (pedido): guardar y consultar de forma indexada el histórico grande que hoy
-- vive solo en la laptop (planilla ~589MB), las designaciones de El Peruano y la evolución
-- de personas/cargos/sueldos en el tiempo. Es un esquema pragmático alimentado DIRECTO
-- desde los CSV con COPY (rápido para cientos de MB); no fuerza la resolución de entidades
-- por UUID del esquema `core` (eso es un proyecto aparte). Convive con core/staging/analytics.
--
-- Se auto-ejecuta al inicializar el contenedor (montado en /docker-entrypoint-initdb.d).
-- Para aplicarlo a mano contra el VPS:  psql "$DATABASE_URL" -f db/postgres/04_historico.sql

CREATE EXTENSION IF NOT EXISTS unaccent;   -- normalización de nombres/cargos
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- búsqueda fuzzy (ILIKE %...%) indexada

CREATE SCHEMA IF NOT EXISTS historico;

-- Normalizador determinista (envoltura IMMUTABLE de unaccent, para usar en índices).
-- Equivale al na() de Python: sin tildes, MAYÚSCULAS, espacios colapsados.
CREATE OR REPLACE FUNCTION historico.norm(txt text)
RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT btrim(regexp_replace(upper(unaccent(coalesce(txt, ''))), '\s+', ' ', 'g'))
$$;

-- ───────────────────────── Planilla mensual (hecho grande) ─────────────────────────
-- Grano: entidad × año × mes × persona × cargo. Origen: funcionarios_historico.csv (dump
-- histórico completo) + funcionarios.csv (mes actual). Se recarga completo (truncate+COPY).
CREATE TABLE IF NOT EXISTS historico.planilla (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_entidad    text    NOT NULL,
    entidad       text    NOT NULL DEFAULT '',
    anio          smallint NOT NULL,
    mes           smallint NOT NULL DEFAULT 0,     -- 0 = mes no informado en la fuente
    regimen       text    NOT NULL DEFAULT '',
    persona       text    NOT NULL,                -- apellidos_nombres tal cual (display)
    persona_norm  text    NOT NULL,                -- historico.norm(persona) para join/búsqueda
    cargo         text    NOT NULL DEFAULT '',
    cargo_norm    text    NOT NULL DEFAULT '',
    dependencia   text    NOT NULL DEFAULT '',
    remuneracion  numeric(12,2),
    honorarios    numeric(12,2),
    incentivo     numeric(12,2),
    aguinaldo     numeric(12,2),
    otros         numeric(12,2),
    total         numeric(12,2),
    fuente_url    text,
    captured_at   timestamptz
);

CREATE INDEX IF NOT EXISTS idx_planilla_persona   ON historico.planilla (persona_norm);
CREATE INDEX IF NOT EXISTS idx_planilla_entidad   ON historico.planilla (id_entidad, anio, mes);
CREATE INDEX IF NOT EXISTS idx_planilla_periodo   ON historico.planilla (anio, mes);
CREATE INDEX IF NOT EXISTS idx_planilla_persona_trgm ON historico.planilla USING gin (persona_norm gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_planilla_cargo_trgm   ON historico.planilla USING gin (cargo_norm  gin_trgm_ops);

COMMENT ON TABLE historico.planilla IS
  'Planilla mensual del Estado (PTE). Serie temporal indexada: sueldos por persona/entidad/periodo.';

-- ───────────────────────── Designaciones El Peruano (incremental) ─────────────────────────
-- Origen: data/designaciones.csv (scrape diario). fuente_url = dispositivo único → upsert.
CREATE TABLE IF NOT EXISTS historico.designacion (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fecha        date,
    entidad      text NOT NULL DEFAULT '',
    cargo        text NOT NULL DEFAULT '',
    cargo_norm   text NOT NULL DEFAULT '',
    nombre       text NOT NULL DEFAULT '',
    nombre_norm  text NOT NULL DEFAULT '',
    norma        text NOT NULL DEFAULT '',
    sumilla      text NOT NULL DEFAULT '',
    fuente_url   text UNIQUE,                       -- dispositivo El Peruano (idempotencia)
    captured_at  timestamptz
);
CREATE INDEX IF NOT EXISTS idx_desig_fecha   ON historico.designacion (fecha);
CREATE INDEX IF NOT EXISTS idx_desig_entidad ON historico.designacion (entidad);
CREATE INDEX IF NOT EXISTS idx_desig_cargo_trgm ON historico.designacion USING gin (cargo_norm gin_trgm_ops);

COMMENT ON TABLE historico.designacion IS
  'Designaciones/nombramientos publicados en El Peruano (Normas Legales), con fecha y norma.';

-- ───────────────────────── Bitácora de cargas (procedencia / "cómo va") ─────────────────────────
CREATE TABLE IF NOT EXISTS historico.carga (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fuente       text NOT NULL,                     -- 'planilla' | 'designaciones'
    archivo      text,
    filas_leidas integer,
    filas_carga  integer,
    inicio       timestamptz NOT NULL DEFAULT now(),
    fin          timestamptz,
    estado       text NOT NULL DEFAULT 'ok'
);

-- ───────────────────────── Vistas analíticas ─────────────────────────
-- Trayectoria de una persona: sus periodos ordenados, con entidad, cargo y sueldo.
CREATE OR REPLACE VIEW historico.v_trayectoria AS
SELECT persona_norm, persona, id_entidad, entidad, anio, mes,
       regimen, cargo, dependencia, total,
       make_date(anio, GREATEST(mes, 1), 1) AS periodo
FROM historico.planilla;

-- Cambios de puesto: mes en que a una persona le cambia cargo o entidad respecto al anterior.
-- (Señal de rotación/ascenso/traslado; sin imputar irregularidad — principio anti-overclaiming.)
CREATE OR REPLACE VIEW historico.v_cambio_puesto AS
WITH s AS (
    SELECT DISTINCT persona_norm, persona, id_entidad, entidad, cargo, cargo_norm, total,
           anio * 12 + mes AS ym,
           make_date(anio, GREATEST(mes, 1), 1) AS periodo
    FROM historico.planilla
), o AS (
    SELECT s.*,
           LAG(cargo_norm) OVER w  AS cargo_prev,
           LAG(id_entidad) OVER w  AS entidad_prev_id,
           LAG(entidad)    OVER w  AS entidad_prev,
           LAG(total)      OVER w  AS total_prev,
           LAG(periodo)    OVER w  AS periodo_prev
    FROM s
    WINDOW w AS (PARTITION BY persona_norm ORDER BY ym)
)
SELECT persona_norm, persona, periodo, periodo_prev,
       entidad_prev, entidad AS entidad_actual,
       cargo_prev, cargo AS cargo_actual,
       total_prev, total AS total_actual,
       (cargo_norm IS DISTINCT FROM cargo_prev)     AS cambio_cargo,
       (id_entidad IS DISTINCT FROM entidad_prev_id) AS cambio_entidad
FROM o
WHERE cargo_prev IS NOT NULL
  AND (cargo_norm IS DISTINCT FROM cargo_prev OR id_entidad IS DISTINCT FROM entidad_prev_id);
