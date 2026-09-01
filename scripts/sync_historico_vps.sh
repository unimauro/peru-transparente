#!/usr/bin/env bash
# sync_historico_vps.sh — Empuja el histórico local al Postgres del VPS (api.tunky.net).
#
# Por qué así: el Postgres del VPS (contenedor api-tunky-db) NO está expuesto a internet.
# En vez de abrir un puerto, se streamea por SSH hacia `docker exec ... psql`, usando el
# socket local del contenedor (trust auth) → no viaja ninguna contraseña ni queda en el repo.
# El transporte va comprimido (gzip) y sin CR/NUL (los CSV vienen con CRLF).
#
#   designaciones: upsert idempotente por norma (barato, corre a diario).
#   planilla:      recarga completa 1.6M filas (pesado); solo con --planilla, cuando llega
#                  un nuevo volcado mensual del PTE.
#
# Config por entorno (defaults para este VPS):
#   VPS_SSH=vidlif-vps  VPS_PG_CONTAINER=api-tunky-db  VPS_PG_DB=peru_transparente
#
# Uso:  ./scripts/sync_historico_vps.sh              # solo designaciones
#       ./scripts/sync_historico_vps.sh --planilla   # además recarga la planilla
set -euo pipefail
cd "$(dirname "$0")/.."

VPS="${VPS_SSH:-vidlif-vps}"
CT="${VPS_PG_CONTAINER:-api-tunky-db}"
DB="${VPS_PG_DB:-peru_transparente}"
USER_PG="${VPS_PG_USER:-tunky}"
REMOTE="gunzip | docker exec -i $CT psql -U $USER_PG -d $DB -v ON_ERROR_STOP=1"

sync_designaciones() {
  [ -f data/designaciones.csv ] || { echo "  (sin data/designaciones.csv; se omite)"; return; }
  echo "▶ designaciones → VPS (upsert)…"
  {
    echo "DROP TABLE IF EXISTS historico._stg_desig;"
    echo "CREATE UNLOGGED TABLE historico._stg_desig (fecha text, entidad text, cargo text, nombre text, norma text, sumilla text, fuente_url text, captured_at text);"
    echo "COPY historico._stg_desig FROM STDIN WITH (FORMAT csv, HEADER true);"
    tr -d '\000\r' < data/designaciones.csv
    printf '\\.\n'
    cat <<'SQL'
INSERT INTO historico.designacion (fecha,entidad,cargo,cargo_norm,nombre,nombre_norm,norma,sumilla,fuente_url,captured_at)
SELECT NULLIF(fecha,'')::date, coalesce(entidad,''), coalesce(cargo,''), historico.norm(cargo),
       coalesce(nombre,''), historico.norm(nombre), coalesce(norma,''), coalesce(sumilla,''),
       NULLIF(fuente_url,''), NULLIF(captured_at,'')::timestamptz
FROM historico._stg_desig WHERE NULLIF(fuente_url,'') IS NOT NULL
ON CONFLICT (fuente_url) DO UPDATE SET
  fecha=EXCLUDED.fecha, entidad=EXCLUDED.entidad, cargo=EXCLUDED.cargo, cargo_norm=EXCLUDED.cargo_norm,
  nombre=EXCLUDED.nombre, nombre_norm=EXCLUDED.nombre_norm, norma=EXCLUDED.norma,
  sumilla=EXCLUDED.sumilla, captured_at=EXCLUDED.captured_at;
INSERT INTO historico.carga (fuente,archivo,filas_leidas,filas_carga,fin)
SELECT 'designaciones','designaciones.csv',(SELECT count(*) FROM historico._stg_desig),
       (SELECT count(*) FROM historico.designacion), now();
DROP TABLE historico._stg_desig;
SQL
  } | gzip -1 | ssh "$VPS" "$REMOTE"
}

sync_planilla() {
  echo "▶ planilla → VPS (recarga completa, puede tardar)…"
  {
    echo "DROP TABLE IF EXISTS historico._stg_planilla;"
    echo "CREATE UNLOGGED TABLE historico._stg_planilla (id_entidad text, entidad text, anio text, mes text, regimen text, apellidos_nombres text, cargo text, dependencia text, remuneracion text, honorarios text, incentivo text, aguinaldo text, otros text, total_ingreso_mensual text, fuente_url text, captured_at text);"
    echo "TRUNCATE historico.planilla;"
    for idx in idx_planilla_persona idx_planilla_entidad idx_planilla_periodo idx_planilla_persona_trgm idx_planilla_cargo_trgm; do
      echo "DROP INDEX IF EXISTS historico.$idx;"
    done
    for f in data/funcionarios_historico.csv data/funcionarios.csv; do
      [ -f "$f" ] || continue
      echo "COPY historico._stg_planilla FROM STDIN WITH (FORMAT csv, HEADER true);"
      tr -d '\000\r' < "$f"
      printf '\\.\n'
    done
    cat <<'SQL'
INSERT INTO historico.planilla
  (id_entidad,entidad,anio,mes,regimen,persona,persona_norm,cargo,cargo_norm,dependencia,
   remuneracion,honorarios,incentivo,aguinaldo,otros,total,fuente_url,captured_at)
SELECT coalesce(id_entidad,''), coalesce(entidad,''),
  coalesce(NULLIF(regexp_replace(anio,'[^0-9]','','g'),''),'0')::smallint,
  coalesce(NULLIF(regexp_replace(mes,'[^0-9]','','g'),''),'0')::smallint,
  coalesce(regimen,''), coalesce(apellidos_nombres,''), historico.norm(apellidos_nombres),
  coalesce(cargo,''), historico.norm(cargo), coalesce(dependencia,''),
  NULLIF(regexp_replace(remuneracion,'[^0-9.-]','','g'),'')::numeric,
  NULLIF(regexp_replace(honorarios,'[^0-9.-]','','g'),'')::numeric,
  NULLIF(regexp_replace(incentivo,'[^0-9.-]','','g'),'')::numeric,
  NULLIF(regexp_replace(aguinaldo,'[^0-9.-]','','g'),'')::numeric,
  NULLIF(regexp_replace(otros,'[^0-9.-]','','g'),'')::numeric,
  NULLIF(regexp_replace(total_ingreso_mensual,'[^0-9.-]','','g'),'')::numeric,
  NULLIF(fuente_url,''), NULLIF(captured_at,'')::timestamptz
FROM historico._stg_planilla WHERE coalesce(apellidos_nombres,'') <> '';
CREATE INDEX idx_planilla_persona      ON historico.planilla (persona_norm);
CREATE INDEX idx_planilla_entidad      ON historico.planilla (id_entidad, anio, mes);
CREATE INDEX idx_planilla_periodo      ON historico.planilla (anio, mes);
CREATE INDEX idx_planilla_persona_trgm ON historico.planilla USING gin (persona_norm gin_trgm_ops);
CREATE INDEX idx_planilla_cargo_trgm   ON historico.planilla USING gin (cargo_norm  gin_trgm_ops);
INSERT INTO historico.carga (fuente,archivo,filas_leidas,filas_carga,fin)
SELECT 'planilla','funcionarios_historico.csv+funcionarios.csv',
       (SELECT count(*) FROM historico._stg_planilla),
       (SELECT count(*) FROM historico.planilla), now();
DROP TABLE historico._stg_planilla;
SQL
  } | gzip -1 | ssh "$VPS" "$REMOTE"
}

sync_designaciones
if [ "${1:-}" = "--planilla" ]; then
  sync_planilla
fi
echo "✅ sync histórico → $VPS:$CT/$DB listo."
