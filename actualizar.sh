#!/usr/bin/env bash
# actualizar.sh — Refresco de datos desde una IP de Perú (tu laptop).
#
# Por qué local: el API del OECE/OCDS bloquea las IPs de datacenter de GitHub
# Actions (403 Forbidden), pero tu laptop con IP residencial peruana pasa (200).
# Por eso la actualización diaria se corre acá y se publica con git push.
#
# Uso (al cerrar el día):   ./actualizar.sh           # 8 min de scrape
#                           ./actualizar.sh 15        # 15 min de scrape
set -euo pipefail
cd "$(dirname "$0")"
PY=.venv/bin/python
MIN="${1:-8}"

echo "▶ 1/4  Reescaneando órdenes de servicio recientes (OECE/OCDS), ${MIN} min…"
rm -f data/ordenes.checkpoint.json            # desde la página 1 = lo más reciente
"$PY" scripts/scrape_ordenes_servicio.py --max-minutes "$MIN"

echo "▶ 2/4  Deduplicando CSV (los reescaneos repiten filas)…"
if [ -f data/ordenes_servicio.csv ]; then
  head -n1 data/ordenes_servicio.csv > /tmp/ord.head
  tail -n +2 data/ordenes_servicio.csv | awk '!seen[$0]++' > /tmp/ord.body
  cat /tmp/ord.head /tmp/ord.body > data/ordenes_servicio.csv
  rm -f /tmp/ord.head /tmp/ord.body
fi

echo "▶ 3/6  Refrescando contratos/adjudicaciones (bulk OCDS mensual)…"
# Bulk incremental: solo re-descarga meses cuyo SHA cambió (checkpoint). Ventana
# corta = meses recientes; el histórico se carga una vez con --desde a mano.
"$PY" scrapers/scrape_contratos.py --meses 3

echo "▶ 4/6  Sanciones RNSSC (SERVIR) — barrido completo, solo los lunes…"
# El RNSSC solo expone VIGENTES (foto del momento) y el barrido tarda 20-40 min:
# lo corremos SEMANAL (lunes) para no alargar el refresco diario. Corre igual con
# ./actualizar.sh N sanciones. La DJ de Intereses es un dump congelado 2022 → no se
# refresca (se publicó una vez).
if [ "$(date +%u)" = "1" ] || [ "${2:-}" = "sanciones" ]; then
  "$PY" scrapers/scrape_rnssc.py && "$PY" scripts/build_sanciones.py
else
  echo "  (hoy no toca; corre 'lunes' o './actualizar.sh $MIN sanciones' para forzar)"
fi

echo "▶ 4.5/6  Designaciones/nombramientos recientes (El Peruano), ${MIN} min…"
# Fuente con FECHA de designación. Best-effort (parseo por heurística del buscador);
# 0 filas no rompe el pipeline. La sección "Nuevos" degrada a altas de planilla.
"$PY" scripts/scrape_designaciones.py --desde 21-07-2026 --max-minutes "$MIN" || \
  echo "  (designaciones: sin datos nuevos o buscador no accesible; se usa solo altas de planilla)"

echo "▶ 5/6  Reconstruyendo JSON + contexto del bot…"
"$PY" scripts/build_ordenes.py
"$PY" scripts/build_contratos.py
"$PY" scripts/build_nuevos_funcionarios.py --corte 2026-07-21
"$PY" scripts/build_trayectorias.py
"$PY" scripts/build_bot_context.py

echo "▶ 6/6  Commit + push (dispara el redeploy de Pages)…"
# data/contratos.csv y data/sanciones_rnssc.csv NO se versionan (RUC/DNI = PII). El
# checkpoint de contratos SÍ (guarda el SHA por mes = estado incremental); el de RNSSC no
# (es efímero, se reinicia en cada barrido completo). Los JSON publicados van todos.
git add frontend/public/data data/ordenes_servicio.csv data/contratos.checkpoint.json
# Las designaciones de El Peruano son 100% públicas (norma + persona + cargo) → se versionan.
[ -f data/designaciones.csv ] && git add data/designaciones.csv data/designaciones.checkpoint.json
if git diff --staged --quiet; then
  echo "  (sin datos nuevos hoy — nada que publicar)"
else
  git commit -q -m "data: refresco $(date +%F)"
  git push -q
  echo "  ✔ publicado — Pages reconstruye en ~1-2 min"
fi
echo "✅ Listo."
