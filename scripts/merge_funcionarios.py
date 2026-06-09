"""Fusiona funcionarios.csv + shards de workers (data/shards/part_*.csv) con dedup.

Clave de dedup: (id_entidad, apellidos_nombres, cargo, anio, mes, regimen).
Reescribe data/funcionarios.csv. También fusiona los checkpoints de los workers.
"""
from __future__ import annotations

import csv
import glob
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scrapers"))
from peru_transparente.connectors.pte_personal import CSV_FIELDS  # noqa: E402

MAIN = Path("data/funcionarios.csv")
CKPT = Path("data/funcionarios.checkpoint.json")


def key(r: dict) -> tuple:
    return (r["id_entidad"], r["apellidos_nombres"], r["cargo"], r["anio"], r["mes"], r["regimen"])


def main() -> None:
    rows: dict[tuple, dict] = {}
    sources = ([MAIN] if MAIN.exists() else []) + [Path(p) for p in sorted(glob.glob("data/shards/part_*.csv"))]
    for src in sources:
        with src.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                rows[key(r)] = r

    with MAIN.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        w.writeheader()
        w.writerows(rows.values())

    # fusionar checkpoints (entidades procesadas por cualquier worker)
    done: set[int] = set()
    if CKPT.exists():
        done |= set(json.loads(CKPT.read_text()).get("done", []))
    for cp in glob.glob("data/shards/part_*.checkpoint.json"):
        done |= set(json.loads(Path(cp).read_text()).get("done", []))
    CKPT.write_text(json.dumps({"done": sorted(done)}))

    print(f"✔ {len(rows)} filas únicas en {MAIN} · {len(done)} entidades procesadas")


if __name__ == "__main__":
    main()
