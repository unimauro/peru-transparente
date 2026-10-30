#!/usr/bin/env bash
# actualizar_diario.sh — envoltorio para la ejecución AUTOMÁTICA (launchd) de ./actualizar.sh.
#
# Por qué existe: el refresco debe correr desde una IP residencial peruana (el OECE bloquea
# datacenters), así que se programa en la laptop con launchd (ver scripts/instalar_actualizacion_diaria.sh).
# Añade lo que una corrida desatendida necesita: lock (no dos a la vez), caffeinate (que la Mac no
# duerma a mitad), PATH mínimo, log con fecha y aviso si falla.
set -uo pipefail
cd "$(dirname "$0")/.."
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export LANG=es_PE.UTF-8 LC_ALL=es_PE.UTF-8
MIN="${1:-8}"
LOG="$HOME/Library/Logs/peru-transparente-actualizar.log"
LOCK="/tmp/peru-transparente-actualizar.lock"
mkdir -p "$(dirname "$LOG")"

if ! mkdir "$LOCK" 2>/dev/null; then
  echo "[$(date '+%F %T')] ya hay una corrida en curso (lock $LOCK); salgo." >> "$LOG"; exit 0
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

{
  echo "================ $(date '+%F %T') · inicio (min=$MIN) ================"
  # caffeinate: evita que la laptop duerma mientras scrapea; -i (idle) -s (sistema con corriente).
  if command -v caffeinate >/dev/null; then
    caffeinate -is ./actualizar.sh "$MIN"; rc=$?
  else
    ./actualizar.sh "$MIN"; rc=$?
  fi
  if [ "$rc" -ne 0 ]; then
    echo "✖ actualizar.sh terminó con código $rc"
    command -v osascript >/dev/null && osascript -e 'display notification "Falló el refresco diario (ver ~/Library/Logs/peru-transparente-actualizar.log)" with title "Perú Transparente"' 2>/dev/null || true
  fi
  echo "================ $(date '+%F %T') · fin (rc=$rc) ================"
} >> "$LOG" 2>&1
# Rotación simple: conserva las últimas ~5,000 líneas.
tail -n 5000 "$LOG" > "$LOG.tmp" 2>/dev/null && mv "$LOG.tmp" "$LOG"
exit 0
