"""Genera JSON estático de Declaraciones Juradas de Intereses + índice de cruce por nombre.

Lee data/dj_intereses.csv (descarga de scrapers/download_dj_intereses.py) y produce
en frontend/public/data/:
- dj.json          : resumen (total de declaraciones, personas, entidades, top entidades,
                     rango de fechas de presentación).
- dj_por_nombre.json : mapa {nombre_normalizado: [{entidad, cargo, fecha, codigo}]} con la
                     MISMA clave na("AP_PATERNO AP_MATERNO, NOMBRES") que build_personas /
                     build_sanciones, para marcar la ficha de persona.

COBERTURA: instantánea jul–dic 2022 (entrada en vigor de la Ley 31227). Que una persona
NO aparezca NO implica que no declaró después; el dataset abierto es de ese período.
ANTI-OVERCLAIMING: el cruce es por nombre (homónimo posible), no un hecho verificado.
Declarar es una OBLIGACIÓN cumplida (señal positiva), no un indicio de irregularidad.
"""
from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

SRC = Path("data/dj_intereses.csv")
OUT = Path("frontend/public/data")


def na(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKD", s or "")
                  .encode("ascii", "ignore").decode().upper()).strip()


def rows(path: Path):
    """csv.DictReader tolerante a bytes NUL (líneas corruptas del scraping)."""
    fh = path.open(encoding="utf-8", errors="ignore", newline="")
    return csv.DictReader(line.replace("\x00", "") for line in fh)


def main() -> None:
    if not SRC.exists():
        print("aún no hay datos de DJ (corre scrapers/download_dj_intereses.py)")
        return

    por_entidad: Counter = Counter()
    por_nombre: dict[str, list] = defaultdict(list)
    fechas: list[str] = []
    total = 0

    for r in rows(SRC):
        cod = r.get("codigo")
        if not cod:
            continue
        total += 1
        ent = r.get("entidad", "")
        if ent:
            por_entidad[ent] += 1
        f = r.get("fecha_presentacion", "")
        if f:
            fechas.append(f)

        apellidos = " ".join(x for x in (r.get("ap_paterno"), r.get("ap_materno")) if x)
        nombre = na(f"{apellidos}, {r.get('nombres', '')}" if apellidos else r.get("nombres", ""))
        if nombre:
            por_nombre[nombre].append({
                "entidad": ent,
                "cargo": r.get("cargo", ""),
                "fecha": f,
                "codigo": cod,
            })

    OUT.mkdir(parents=True, exist_ok=True)
    resumen = {
        "fuente": "Declaraciones Juradas de Intereses — Ley 31227 (CGR, datos abiertos)",
        "cobertura": f"{min(fechas)[:10] if fechas else '—'} a {max(fechas)[:10] if fechas else '—'} "
                     "(instantánea inicial del sistema; no es histórico completo)",
        "advertencia": "Declarar es una obligación cumplida (señal positiva). La ausencia no implica "
                       "incumplimiento fuera de este período. El cruce con la planilla es por nombre "
                       "(homónimo posible), no un hecho confirmado.",
        "total_declaraciones": total,
        "total_personas": len(por_nombre),
        "total_entidades": len(por_entidad),
        "top_entidades": por_entidad.most_common(30),
    }
    (OUT / "dj.json").write_text(
        json.dumps(resumen, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # Índice por nombre SHARDEADO por inicial (como personas/): carga liviana en móvil.
    shards: dict[str, dict] = defaultdict(dict)
    for nombre, ds in por_nombre.items():
        letra = nombre[0] if nombre and nombre[0].isalpha() else "_"
        shards[letra][nombre] = ds
    (OUT / "dj").mkdir(parents=True, exist_ok=True)
    meta = {"match": "por_nombre", "homonimo_posible": True, "cobertura": resumen["cobertura"],
            "nota": "Coincidencia por nombre normalizado; declarar es señal positiva."}
    for letra, idx in shards.items():
        (OUT / "dj" / f"{letra}.json").write_text(
            json.dumps({"_meta": meta, "index": idx}, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8")

    print(f"✔ {total:,} declaraciones · {len(por_nombre):,} nombres · {len(por_entidad)} entidades "
          f"→ {OUT}/dj.json + {OUT}/dj/<LETRA>.json ({len(shards)} shards)")


if __name__ == "__main__":
    main()
