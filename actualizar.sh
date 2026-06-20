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

echo "▶ 3/4  Reconstruyendo JSON + contexto del bot…"
"$PY" scripts/build_ordenes.py
"$PY" scripts/build_trayectorias.py
"$PY" scripts/build_bot_context.py

echo "▶ 4/4  Commit + push (dispara el redeploy de Pages)…"
git add frontend/public/data data/ordenes_servicio.csv
if git diff --staged --quiet; then
  echo "  (sin datos nuevos hoy — nada que publicar)"
else
  git commit -q -m "data: refresco $(date +%F)"
  git push -q
  echo "  ✔ publicado — Pages reconstruye en ~1-2 min"
fi
echo "✅ Listo."
