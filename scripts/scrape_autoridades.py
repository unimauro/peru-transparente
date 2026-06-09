"""Barre el directorio de AUTORIDADES de gob.pe para todas las entidades.

Deriva el slug de gob.pe del acrónimo de cada entidad (ej. "(UNI)" → uni) y
descarga /institucion/<slug>/funcionarios. Complementa al PTE con rectores,
ministros, jefes, gerentes y directores (cargo + correo + teléfono).

Salida: data/autoridades.csv  (resumable por checkpoint).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scrapers"))
from peru_transparente.connectors.gobpe_directorio import GobpeDirectorioConnector  # noqa: E402

OUT = Path("data/autoridades.csv")
CKPT = Path("data/autoridades.checkpoint.json")
FIELDS = ["id_entidad", "slug", "institucion_pte", "nombre", "cargo", "email", "telefono", "detalle_url", "fuente_url", "captured_at"]


def slug_candidates(nombre: str) -> list[str]:
    """Deriva posibles slugs de gob.pe del acrónimo entre paréntesis y del nombre."""
    cands: list[str] = []
    m = re.search(r"\(([A-Za-z0-9.\-\s]{2,18})\)\s*$", nombre)
    if m:
        ac = re.sub(r"[.\s]", "", m.group(1)).lower()
        if 2 <= len(ac) <= 18:
            cands.append(ac)
    return list(dict.fromkeys(cands))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalogo", default="data/entidades.csv")
    ap.add_argument("--delay", type=float, default=0.3)
    ap.add_argument("--max-minutes", type=float, default=0)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    done: set[str] = set()
    if args.resume and CKPT.exists():
        done = set(json.loads(CKPT.read_text()).get("done", []))

    ents = list(csv.DictReader(open(args.catalogo, encoding="utf-8")))
    conn = GobpeDirectorioConnector()
    deadline = time.monotonic() + args.max_minutes * 60 if args.max_minutes else None

    write_header = not OUT.exists() or OUT.stat().st_size == 0
    total = 0
    with OUT.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if write_header:
            w.writeheader()
        for i, e in enumerate(ents, 1):
            eid = e["id_entidad"]
            if eid in done:
                continue
            if deadline and time.monotonic() > deadline:
                print("[stop] tope de tiempo", flush=True)
                break
            got = 0
            for slug in slug_candidates(e["nombre"]):
                rows = conn.fetch(slug)
                if rows:
                    for a in rows:
                        d = asdict(a)
                        w.writerow({"id_entidad": eid, "slug": d["slug"], "institucion_pte": e["nombre"],
                                    "nombre": d["nombre"], "cargo": d["cargo"], "email": d["email"],
                                    "telefono": d["telefono"], "detalle_url": d["detalle_url"],
                                    "fuente_url": d["fuente_url"], "captured_at": d["captured_at"]})
                    got = len(rows)
                    fh.flush()
                    break
                time.sleep(args.delay)
            done.add(eid)
            total += got
            if got:
                print(f"[{i}/{len(ents)}] {e['nombre'][:42]} → {got} autoridades (acum {total})", flush=True)
            if i % 25 == 0:
                CKPT.write_text(json.dumps({"done": sorted(done)}))
            time.sleep(args.delay)
    CKPT.write_text(json.dumps({"done": sorted(done)}))
    conn.close()
    print(f"\n✔ {total} autoridades en {OUT}")


if __name__ == "__main__":
    main()
