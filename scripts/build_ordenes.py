"""Agrega el rastreo de órdenes de servicio por RUC/DNI y lo cruza con la planilla.

- Agrupa por RUC: nº de órdenes, monto total, entidades, DNI.
- CRUCE: ¿el locador (por nombre normalizado) también figura en la planilla del PTE?
  Eso señala a alguien que es servidor y además recibe órdenes de servicio
  (puede ser legítimo si es en otra entidad/período — se marca como señal, no acusación).

Salida: frontend/public/data/ordenes_servicio.json
"""
from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

SRC = Path("data/ordenes_servicio.csv")
OUT = Path("frontend/public/data/ordenes_servicio.json")


def na(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKD", s or "")
                  .encode("ascii", "ignore").decode().upper()).strip()


def rows(path: Path):
    """csv.DictReader tolerante a bytes NUL (líneas corruptas del scraping)."""
    fh = path.open(encoding="utf-8", errors="ignore", newline="")
    return csv.DictReader(line.replace("\x00", "") for line in fh)


def main() -> None:
    if not SRC.exists():
        print("aún no hay datos de órdenes de servicio")
        return

    # nombres en planilla (actual + histórico) para el cruce
    planilla = {}
    for fn in ["data/funcionarios.csv", "data/funcionarios_historico.csv"]:
        p = Path(fn)
        if p.exists():
            for r in rows(p):
                if r.get("apellidos_nombres"):
                    planilla[na(r["apellidos_nombres"])] = r.get("entidad", "")

    by_ruc = defaultdict(lambda: {"dni": "", "nombre": "", "n": 0, "monto": 0.0, "entidades": set(), "desc": set(), "_ocids": set()})
    for r in rows(SRC):
        if not r.get("ruc"):
            continue
        g = by_ruc[r["ruc"]]
        oc = r.get("ocid", "")
        if oc in g["_ocids"]:   # evitar contar 2 veces la misma orden (re-runs del sweep)
            continue
        g["_ocids"].add(oc)
        g["dni"] = r["dni"]
        g["nombre"] = r["proveedor"]
        g["n"] += 1
        try:
            g["monto"] += float(r["monto"])
        except (TypeError, ValueError):
            pass
        g["entidades"].add(r["entidad"])
        if r["descripcion"]:
            g["desc"].add(r["descripcion"][:50])

    items = []
    cruces = []
    for ruc, g in by_ruc.items():
        en_planilla = na(g["nombre"]) in planilla
        rec = {
            "ruc": ruc, "dni": g["dni"], "nombre": g["nombre"], "n": g["n"],
            "monto": round(g["monto"]), "entidades": len(g["entidades"]),
            "servicios": list(g["desc"])[:4], "en_planilla": en_planilla,
            "entidad_planilla": planilla.get(na(g["nombre"]), "") if en_planilla else "",
        }
        items.append(rec)
        if en_planilla:
            cruces.append(rec)

    items.sort(key=lambda x: -x["monto"])
    cruces.sort(key=lambda x: -x["monto"])
    total_monto = sum(g["monto"] for g in by_ruc.values())

    OUT.write_text(json.dumps({
        "total_locadores": len(by_ruc),
        "total_ordenes": sum(g["n"] for g in by_ruc.values()),
        "monto_total": round(total_monto),
        "en_planilla": len(cruces),
        "top": items[:300],
        "cruces": cruces[:200],
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"✔ {len(by_ruc)} locadores · {sum(g['n'] for g in by_ruc.values())} órdenes · "
          f"S/{round(total_monto):,} · {len(cruces)} también en planilla")


if __name__ == "__main__":
    main()
