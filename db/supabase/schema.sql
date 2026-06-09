-- Perú Transparente — esquema Supabase/Postgres para BÚSQUEDA GLOBAL de personas.
-- Denormalizado y optimizado para: buscar a cualquier persona en todo el Estado,
-- ver sus cargos en N entidades (redes de poder) y full-text + fuzzy.
-- Capa gratuita Supabase (500 MB): ~267k funcionarios entran holgados (~60 MB).

create extension if not exists pg_trgm;     -- fuzzy / similitud de nombres
create extension if not exists unaccent;    -- búsqueda sin tildes

-- ───────────────────────── Entidades ─────────────────────────
create table if not exists entidad (
    id_entidad   text primary key,
    nombre       text not null,
    categoria    text,
    tipo_label   text,
    estado       text,          -- con_datos | sin_datos | pendiente
    funcionarios int default 0
);

-- ───────────────────────── Funcionarios (planilla PTE) ─────────────────────────
create table if not exists funcionario (
    id            bigint generated always as identity primary key,
    id_entidad    text references entidad(id_entidad),
    entidad       text,
    apellidos_nombres text not null,
    nombre_norm   text,          -- sin tildes/upper, para búsqueda
    cargo         text,
    dependencia   text,
    nivel         text,          -- Ministro/Director/Jefe/Profesional...
    regimen       text,
    anio          int,
    mes           int,
    remuneracion        numeric,
    otros               numeric,
    total_ingreso_mensual numeric,
    fuente_url    text,
    captured_at   timestamptz
);

create index if not exists idx_func_entidad   on funcionario(id_entidad);
create index if not exists idx_func_nivel      on funcionario(nivel);
-- búsqueda full-text (nombre + cargo + entidad) sin tildes
create index if not exists idx_func_fts on funcionario
    using gin (to_tsvector('spanish', unaccent(coalesce(apellidos_nombres,'')||' '||coalesce(cargo,'')||' '||coalesce(entidad,''))));
-- fuzzy por nombre
create index if not exists idx_func_nombre_trgm on funcionario using gin (nombre_norm gin_trgm_ops);

-- ───────────────────────── Autoridades (gob.pe) ─────────────────────────
create table if not exists autoridad (
    id           bigint generated always as identity primary key,
    id_entidad   text references entidad(id_entidad),
    institucion  text,
    nombre       text not null,
    nombre_norm  text,
    cargo        text,
    email        text,
    telefono     text,
    detalle_url  text
);
create index if not exists idx_aut_entidad on autoridad(id_entidad);
create index if not exists idx_aut_nombre_trgm on autoridad using gin (nombre_norm gin_trgm_ops);

-- ───────────────────────── Vista: PERSONA (redes de poder) ─────────────────────────
-- Agrupa por nombre normalizado: cuántas entidades/cargos tiene una persona.
-- (Aproximado por nombre; la resolución por DNI/IA es el siguiente paso.)
create or replace view persona_resumen as
select
    nombre_norm,
    max(apellidos_nombres)              as nombre,
    count(*)                            as registros,
    count(distinct id_entidad)          as entidades,
    array_agg(distinct entidad)         as lista_entidades,
    max(total_ingreso_mensual)          as ingreso_max
from funcionario
where nombre_norm is not null and length(nombre_norm) > 6
group by nombre_norm;

-- ───────────────────────── Función de búsqueda global ─────────────────────────
-- Uso desde el frontend (Supabase RPC): select * from buscar_persona('sanchez ferrer');
create or replace function buscar_persona(q text)
returns table (apellidos_nombres text, cargo text, entidad text, nivel text,
               total_ingreso_mensual numeric, fuente_url text)
language sql stable as $$
    select apellidos_nombres, cargo, entidad, nivel, total_ingreso_mensual, fuente_url
    from funcionario
    where nombre_norm % upper(unaccent(q))
       or to_tsvector('spanish', unaccent(coalesce(apellidos_nombres,'')||' '||coalesce(cargo,'')||' '||coalesce(entidad,'')))
          @@ plainto_tsquery('spanish', unaccent(q))
    order by similarity(nombre_norm, upper(unaccent(q))) desc
    limit 200;
$$;
