"""Barrido HISTÓRICO del PTE: snapshot de diciembre de varios años por entidad.

Permite rastrear la TRAYECTORIA de cada servidor en el tiempo (en qué cargo/entidad
estuvo cada año). Guarda en data/funcionarios_historico.csv (aparte de la foto actual).
Resumable por (año, entidad). Pensado para correr largo en background.

Uso:
  python scripts/scrape_historico.py --ids-file data/_con_datos.csv --years 2024,2021,2018,2015
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scrapers"))
from peru_transparente.connectors.pte_personal import CSV_FIELDS, REGIMES, PtePersonalConnector  # noqa: E402

OUT = Path("data/funcionarios_historico.csv")
CKPT = Path("data/historico.checkpoint.json")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids-file", required=True)
    ap.add_argument("--years", default="2024,2021,2018,2015")
    ap.add_argument("--mes", type=int, default=12)
    ap.add_argument("--delay", type=float, default=0.3)
    ap.add_argument("--max-minutes", type=float, default=0)
    args = ap.parse_args()

    years = [int(y) for y in args.years.split(",")]
    ids = [int(r["id_entidad"]) for r in csv.DictReader(open(args.ids_file, encoding="utf-8"))]
    done = set(json.loads(CKPT.read_text()).get("done", [])) if CKPT.exists() else set()
    conn = PtePersonalConnector()
    deadline = time.monotonic() + args.max_minutes * 60 if args.max_minutes else None

    write_header = not OUT.exists() or OUT.stat().st_size == 0
    total = 0
    with OUT.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        if write_header:
            w.writeheader()
        for year in years:
            for i, eid in enumerate(ids, 1):
                key = f"{year}-{eid}"
                if key in done:
                    continue
                if deadline and time.monotonic() > deadline:
                    print("[stop] tope de tiempo", flush=True)
                    CKPT.write_text(json.dumps({"done": sorted(done)}))
                    conn.close()
                    return
                got = 0
                for row in conn.fetch_entity(eid, year, args.mes, regimes=list(REGIMES)):
                    w.writerow(asdict(row))
                    got += 1
                done.add(key)
                total += got
                if got:
                    print(f"[{year}] {i}/{len(ids)} id={eid} → {got} (acum {total})", flush=True)
                if i % 20 == 0:
                    CKPT.write_text(json.dumps({"done": sorted(done)}))
                    fh.flush()
                time.sleep(args.delay)
    CKPT.write_text(json.dumps({"done": sorted(done)}))
    conn.close()
    print(f"✔ histórico: {total} filas en {OUT}")


if __name__ == "__main__":
    main()
