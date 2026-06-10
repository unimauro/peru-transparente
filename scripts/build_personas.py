"""Índice estático de personas para el buscador global (sin BD).

- personas/<LETRA>.json : shards por inicial del apellido (carga on-demand al buscar).
- personas_red.json     : personas en 2+ entidades (redes de poder) — destacado.

Cada persona: [nombre, n_entidades, [[id_entidad, entidad_abrev, cargo, regimen, sueldo], ...]]
"""
from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

OUT = Path("frontend/public/data")


def na(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKD", s or "")
                  .encode("ascii", "ignore").decode().upper()).strip()


def ab(e: str) -> str:
    m = re.search(r"\(([^)]{2,12})\)\s*$", e)
    return m.group(1) if m else e[:24]


def main() -> None:
    pers: dict[str, list] = defaultdict(list)
    fuentes = ["data/funcionarios.csv"]
    if Path("data/funcionarios_historico.csv").exists():
        fuentes.append("data/funcionarios_historico.csv")
    vistos: set = set()  # dedup por (nombre, entidad, cargo, año)
    for fn in fuentes:
        for r in csv.DictReader(open(fn, encoding="utf-8")):
            try:
                s = round(float(r["total_ingreso_mensual"]))
            except (TypeError, ValueError):
                s = 0
            nm = na(r["apellidos_nombres"])
            anio = r.get("anio", "")
            k = (nm, r["id_entidad"], r["cargo"][:38], anio)
            if k in vistos:
                continue
            vistos.add(k)
            # aparición: [id_entidad, abrev, cargo, regimen, sueldo, año]
            pers[nm].append([r["id_entidad"], ab(r["entidad"]), r["cargo"][:38], r["regimen"], s, anio])

    shards: dict[str, list] = defaultdict(list)
    red: list = []
    for nombre, aps in pers.items():
        n_ent = len(set(a[0] for a in aps))
        rec = [nombre, n_ent, aps]
        letra = nombre[0] if nombre and nombre[0].isalpha() else "_"
        shards[letra].append(rec)
        if n_ent >= 2:
            red.append(rec)

    (OUT / "personas").mkdir(parents=True, exist_ok=True)
    for letra, recs in shards.items():
        recs.sort(key=lambda x: x[0])
        (OUT / "personas" / f"{letra}.json").write_text(
            json.dumps({"items": recs}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    red.sort(key=lambda x: -x[1])
    (OUT / "personas_red.json").write_text(
        json.dumps({"items": red}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    print(f"✔ {len(pers):,} personas en {len(shards)} shards · {len(red):,} en 2+ entidades")


if __name__ == "__main__":
    main()
