#!/usr/bin/env python3
"""
Serie histórica diaria de las cifras clave del portal Perú Transparente.

Lee los JSON publicados en ``frontend/public/data/`` y guarda una fila por
fecha con las métricas agregadas, para graficar "cómo se movieron las cosas".
Solo stdlib.

Uso
----
    .venv/bin/python scripts/snapshot_historico.py              # snapshot de hoy
    .venv/bin/python scripts/snapshot_historico.py --fecha 2026-10-20
    .venv/bin/python scripts/snapshot_historico.py --backfill   # reconstruye desde git

Salidas
-------
- ``data/historico/serie_diaria.csv``            UPSERT por fecha, orden ascendente.
- ``data/historico/snapshots/YYYY-MM-DD/*.json`` copia de los JSON pequeños (<1 MB).
- ``frontend/public/data/historico_serie.json``  contrato para el front:
      {"generated_at": ISO, "campos": {metrica: etiqueta_es}, "serie": [fila, ...]}

Origen de cada métrica (archivo → clave)
----------------------------------------
funcionarios            national_kpis.json → total_funcionarios
entidades_con_datos     national_kpis.json → entities_with_data
cargos_clave            national_kpis.json → total_cargos_clave
contratos_n             contratos.json → resumen.n_adjudicaciones (fallback _meta.n_adjudicaciones)
contratos_monto         contratos.json → resumen.monto_total   (fallback _meta.monto_total)
ordenes_n               ordenes_servicio.json → total_ordenes
ordenes_monto           ordenes_servicio.json → monto_total
designaciones_total     nuevos_funcionarios.json → meta.universo.total (o total)
designaciones_oficiales nuevos_funcionarios.json → meta.universo.oficiales (o oficiales)
sanciones_n             sanciones.json → total_sanciones
dj_n                    dj.json → total_declaraciones
autoridades_n           autoridades.json → len(items)

Si el archivo o la clave no existe la métrica queda ``null`` (vacío en el CSV).

Backfill
--------
Recorre ``git log HEAD -- frontend/public/data`` (solo historial local, limpio;
los commits del bot de CI en origin/main traen total_funcionarios=0 y no se
usan). Para cada fecha de commit toma el ÚLTIMO commit del día, lee cada
archivo con ``git show <sha>:<ruta>`` y arma la fila. Las filas con
funcionarios == 0 se descartan. El snapshot de hoy se sigue tomando del
working tree, nunca de git.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA_DIR = REPO / "frontend" / "public" / "data"
DATA_REL = "frontend/public/data"
HIST_DIR = REPO / "data" / "historico"
CSV_PATH = HIST_DIR / "serie_diaria.csv"
SNAP_DIR = HIST_DIR / "snapshots"
OUT_JSON = DATA_DIR / "historico_serie.json"

MAX_SNAPSHOT_BYTES = 1_000_000

# Orden fijo de columnas del CSV y del JSON.
CAMPOS: dict[str, str] = {
    "funcionarios": "Servidores públicos nominales (PTE)",
    "entidades_con_datos": "Entidades con planilla publicada",
    "cargos_clave": "Cargos clave identificados",
    "contratos_n": "Adjudicaciones SEACE (n)",
    "contratos_monto": "Monto adjudicado SEACE (S/)",
    "ordenes_n": "Órdenes de servicio (n)",
    "ordenes_monto": "Monto de órdenes de servicio (S/)",
    "designaciones_total": "Designaciones y altas recientes",
    "designaciones_oficiales": "Designaciones oficiales (El Peruano)",
    "sanciones_n": "Sanciones vigentes RNSSC",
    "dj_n": "Declaraciones juradas de intereses",
    "autoridades_n": "Autoridades registradas (gob.pe)",
}
COLUMNAS = ["fecha", *CAMPOS]

# Archivos que necesita la fila (todos pequeños salvo autoridades, 1.8 MB).
ARCHIVOS_METRICAS = [
    "national_kpis.json",
    "contratos.json",
    "ordenes_servicio.json",
    "nuevos_funcionarios.json",
    "sanciones.json",
    "dj.json",
    "autoridades.json",
]
# Archivos que se copian al snapshot del día (si pesan < 1 MB).
ARCHIVOS_SNAPSHOT = [
    "national_kpis.json",
    "meta.json",
    "contratos.json",
    "sanciones.json",
    "dj.json",
    "bot_context.json",
]


# --------------------------------------------------------------------------- #
# Lectura de JSON (working tree o git)
# --------------------------------------------------------------------------- #
def _parse(raw: bytes | str | None):
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return None


def leer_local(nombre: str):
    p = DATA_DIR / nombre
    if not p.is_file():
        return None
    return _parse(p.read_bytes())


def leer_git(sha: str, nombre: str):
    r = subprocess.run(
        ["git", "-C", str(REPO), "show", f"{sha}:{DATA_REL}/{nombre}"],
        capture_output=True,
    )
    if r.returncode != 0:
        return None  # la ruta no existe en ese commit
    return _parse(r.stdout)


def _get(d, *claves):
    """Navega claves anidadas; devuelve None si algo falta."""
    cur = d
    for k in claves:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def _num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, str):
        try:
            f = float(v.replace(",", ""))
            return int(f) if f.is_integer() else f
        except ValueError:
            return None
    return None


def construir_fila(fecha: str, leer) -> dict:
    """``leer(nombre) -> dict|list|None``. Devuelve la fila con las métricas."""
    docs = {n: leer(n) for n in ARCHIVOS_METRICAS}
    kpis = docs["national_kpis.json"]
    con = docs["contratos.json"]
    ord_ = docs["ordenes_servicio.json"]
    nf = docs["nuevos_funcionarios.json"]
    san = docs["sanciones.json"]
    dj = docs["dj.json"]
    aut = docs["autoridades.json"]

    def first(*vals):
        for v in vals:
            n = _num(v)
            if n is not None:
                return n
        return None

    items_aut = _get(aut, "items") if isinstance(aut, dict) else aut
    return {
        "fecha": fecha,
        "funcionarios": first(_get(kpis, "total_funcionarios")),
        "entidades_con_datos": first(_get(kpis, "entities_with_data")),
        "cargos_clave": first(_get(kpis, "total_cargos_clave")),
        "contratos_n": first(_get(con, "resumen", "n_adjudicaciones"),
                             _get(con, "_meta", "n_adjudicaciones")),
        "contratos_monto": first(_get(con, "resumen", "monto_total"),
                                 _get(con, "_meta", "monto_total")),
        "ordenes_n": first(_get(ord_, "total_ordenes")),
        "ordenes_monto": first(_get(ord_, "monto_total")),
        # universo detectado (meta.universo) antes que el recorte publicado (`total`)
        "designaciones_total": first(_get(nf, "meta", "universo", "total"), _get(nf, "total")),
        "designaciones_oficiales": first(_get(nf, "meta", "universo", "oficiales"), _get(nf, "oficiales")),
        "sanciones_n": first(_get(san, "total_sanciones")),
        "dj_n": first(_get(dj, "total_declaraciones")),
        "autoridades_n": len(items_aut) if isinstance(items_aut, list) else None,
    }


# --------------------------------------------------------------------------- #
# CSV (UPSERT por fecha)
# --------------------------------------------------------------------------- #
def leer_csv() -> dict[str, dict]:
    filas: dict[str, dict] = {}
    if not CSV_PATH.is_file():
        return filas
    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            fila = {"fecha": row.get("fecha", "")}
            for c in CAMPOS:
                fila[c] = _num(row.get(c)) if row.get(c) not in (None, "") else None
            if fila["fecha"]:
                filas[fila["fecha"]] = fila
    return filas


def escribir_csv(filas: dict[str, dict]) -> None:
    HIST_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CSV_PATH.with_suffix(".csv.tmp")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNAS, extrasaction="ignore")
        w.writeheader()
        for fecha in sorted(filas):
            fila = filas[fecha]
            w.writerow({c: ("" if fila.get(c) is None else fila[c]) for c in COLUMNAS})
    tmp.replace(CSV_PATH)


def upsert(filas: dict[str, dict], nuevas: list[dict]) -> None:
    for fila in nuevas:
        filas[fila["fecha"]] = {c: fila.get(c) for c in COLUMNAS}


# --------------------------------------------------------------------------- #
# Snapshot de archivos pequeños
# --------------------------------------------------------------------------- #
def copiar_snapshot(fecha: str) -> list[str]:
    dest = SNAP_DIR / fecha
    dest.mkdir(parents=True, exist_ok=True)
    copiados = []
    for nombre in ARCHIVOS_SNAPSHOT:
        src = DATA_DIR / nombre
        if not src.is_file():
            continue
        if src.stat().st_size > MAX_SNAPSHOT_BYTES:
            print(f"  · {nombre}: >1 MB, no se copia")
            continue
        shutil.copy2(src, dest / nombre)
        copiados.append(nombre)
    return copiados


# --------------------------------------------------------------------------- #
# JSON para el front
# --------------------------------------------------------------------------- #
def escribir_json(filas: dict[str, dict]) -> int:
    serie = []
    for fecha in sorted(filas):
        fila = filas[fecha]
        serie.append({"fecha": fecha, **{c: fila.get(c) for c in CAMPOS}})
    doc = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "campos": CAMPOS,
        "serie": serie,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT_JSON.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(OUT_JSON)
    return len(serie)


# --------------------------------------------------------------------------- #
# Backfill desde git
# --------------------------------------------------------------------------- #
def commits_por_dia() -> dict[str, str]:
    """{fecha: sha} con el ÚLTIMO commit de cada día (log viene de nuevo a viejo)."""
    r = subprocess.run(
        ["git", "-C", str(REPO), "log", "HEAD", "--format=%H %cs", "--", DATA_REL],
        capture_output=True, text=True, check=True,
    )
    por_dia: dict[str, str] = {}
    for linea in r.stdout.splitlines():
        sha, fecha = linea.split()
        por_dia.setdefault(fecha, sha)  # el primero visto = el más reciente del día
    return por_dia


def backfill(filas: dict[str, dict]) -> tuple[int, int]:
    por_dia = commits_por_dia()
    fechas = sorted(por_dia)
    print(f"Backfill: {len(fechas)} fechas con commits en {DATA_REL}")
    ok = descartadas = 0
    for i, fecha in enumerate(fechas, 1):
        sha = por_dia[fecha]
        fila = construir_fila(fecha, lambda n, sha=sha: leer_git(sha, n))
        if not fila["funcionarios"]:
            descartadas += 1
            print(f"  [{i}/{len(fechas)}] {fecha} {sha[:8]} descartada (funcionarios={fila['funcionarios']!r})")
            continue
        upsert(filas, [fila])
        ok += 1
        print(f"  [{i}/{len(fechas)}] {fecha} {sha[:8]} funcionarios={fila['funcionarios']} "
              f"contratos_n={fila['contratos_n']} ordenes_n={fila['ordenes_n']} "
              f"designaciones={fila['designaciones_total']}")
    return ok, descartadas


# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--fecha", help="YYYY-MM-DD a usar para el snapshot (default hoy)")
    ap.add_argument("--backfill", action="store_true",
                    help="reconstruir la serie desde el historial git (no toma snapshot de hoy)")
    args = ap.parse_args(argv)

    filas = leer_csv()

    if args.backfill:
        ok, desc = backfill(filas)
        print(f"Backfill: {ok} filas incorporadas, {desc} descartadas (funcionarios==0 / sin datos)")
    else:
        fecha = args.fecha or dt.date.today().isoformat()
        try:
            dt.date.fromisoformat(fecha)
        except ValueError:
            print(f"--fecha inválida: {fecha}", file=sys.stderr)
            return 2
        fila = construir_fila(fecha, leer_local)
        if not fila["funcionarios"]:
            print(f"ADVERTENCIA: funcionarios={fila['funcionarios']!r} en {fecha}; "
                  "no se guarda la fila (datos incompletos)", file=sys.stderr)
        else:
            upsert(filas, [fila])
            print(f"Snapshot {fecha}: " + ", ".join(f"{k}={v}" for k, v in fila.items() if k != "fecha"))
        copiados = copiar_snapshot(fecha)
        print(f"Snapshot JSON en {SNAP_DIR.relative_to(REPO)}/{fecha}/: {', '.join(copiados) or 'nada'}")

    escribir_csv(filas)
    n = escribir_json(filas)
    fechas = sorted(filas)
    print(f"Serie: {n} fechas ({fechas[0] if fechas else '-'} → {fechas[-1] if fechas else '-'}) "
          f"→ {CSV_PATH.relative_to(REPO)}, {OUT_JSON.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
