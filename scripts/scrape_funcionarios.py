"""Descarga PROGRESIVA de funcionarios del Estado peruano → CSV.

Recorre entidades del Portal de Transparencia Estándar por `id_entidad`, busca el
período más reciente con datos y vuelca TODOS los regímenes (de altos funcionarios
a jefaturas y servidores) a un CSV, fila por fila.

Características:
  - Progresivo: escribe cada fila al instante (no espera el final).
  - Resumable: checkpoint de entidades ya procesadas (.checkpoint.json). Re-ejecutar
    continúa donde quedó.
  - Cortés: rate-limit configurable entre peticiones.
  - Tolerante: una entidad que falla no detiene el resto.

Uso:
    python scripts/scrape_funcionarios.py --ids 1-300 --out data/funcionarios.csv
    python scripts/scrape_funcionarios.py --ids 145,146,001 --year 2025 --delay 1.0
    python scripts/scrape_funcionarios.py --ids 1-3000 --resume   # continúa
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scrapers"))

from peru_transparente.connectors.pte_personal import (  # noqa: E402
    CSV_FIELDS, REGIMES, PtePersonalConnector,
)


def parse_ids(spec: str) -> list[int]:
    ids: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            ids.extend(range(int(a), int(b) + 1))
        elif part:
            ids.append(int(part))
    return ids


def load_checkpoint(path: Path) -> set[int]:
    if path.exists():
        return set(json.loads(path.read_text()).get("done", []))
    return set()


def save_checkpoint(path: Path, done: set[int]) -> None:
    path.write_text(json.dumps({"done": sorted(done), "updated": datetime.now(timezone.utc).isoformat()}))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", required=True, help="ej. '1-300' o '145,146,1'")
    ap.add_argument("--out", default="data/funcionarios.csv")
    ap.add_argument("--year", type=int, default=datetime.now(timezone.utc).year)
    ap.add_argument("--month", type=int, default=0, help="0 = autodetecta el mes más reciente con datos")
    ap.add_argument("--regimes", default="", help="csv de códigos; vacío = todos menos pensionistas")
    ap.add_argument("--delay", type=float, default=0.8, help="segundos entre entidades")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--max-empty-entities", type=int, default=0,
                    help=">0: corta tras N entidades seguidas sin datos (útil al escanear)")
    ap.add_argument("--max-minutes", type=float, default=0,
                    help=">0: detiene con gracia tras N minutos (para CI), guardando checkpoint")
    args = ap.parse_args()
    deadline = time.monotonic() + args.max_minutes * 60 if args.max_minutes else None

    ids = parse_ids(args.ids)
    regimes = [int(x) for x in args.regimes.split(",") if x.strip()] or list(REGIMES)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    ckpt = out.with_suffix(".checkpoint.json")
    done = load_checkpoint(ckpt) if args.resume else set()

    write_header = not out.exists() or out.stat().st_size == 0
    conn = PtePersonalConnector()
    total_rows = 0
    empty_streak = 0

    # meses a probar para autodetección: el indicado, o de actual hacia atrás
    def months_to_try() -> list[tuple[int, int]]:
        if args.month:
            return [(args.year, args.month)]
        seq = []
        y, m = args.year, datetime.now(timezone.utc).month
        for _ in range(14):  # hasta ~14 meses atrás cruzando de año
            seq.append((y, m))
            m -= 1
            if m == 0:
                m, y = 12, y - 1
        return seq

    with out.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        if write_header:
            writer.writeheader()
            fh.flush()

        for i, eid in enumerate(ids, 1):
            if eid in done:
                continue
            if deadline and time.monotonic() > deadline:
                print(f"[stop] Tope de tiempo ({args.max_minutes} min). Guardo checkpoint y salgo.", flush=True)
                break
            rows_here = 0
            entity_name = None
            # 1) Detectar período más reciente con datos usando sondas baratas (CAS, 728).
            found_period = None
            for (yy, mm) in months_to_try():
                probe = next(conn.fetch_entity(eid, yy, mm, regimes=[1, 3, 2]), None)
                if probe is not None:
                    found_period = (yy, mm)
                    break
            # 2) Cosechar TODOS los regímenes para ese período.
            if found_period:
                yy, mm = found_period
                for row in conn.fetch_entity(eid, yy, mm, regimes=regimes):
                    writer.writerow(asdict(row))
                    entity_name = row.entidad
                    rows_here += 1
                fh.flush()
            total_rows += rows_here
            done.add(eid)
            tag = f"[{i}/{len(ids)}] id={eid}"
            if rows_here:
                empty_streak = 0
                print(f"{tag}  {entity_name[:55] if entity_name else ''}  → {rows_here} filas "
                      f"(acum {total_rows})", flush=True)
            else:
                empty_streak += 1
                print(f"{tag}  (sin datos)", flush=True)

            if i % 10 == 0:
                save_checkpoint(ckpt, done)
            if args.max_empty_entities and empty_streak >= args.max_empty_entities:
                print(f"Corte: {empty_streak} entidades seguidas sin datos.", flush=True)
                break
            time.sleep(args.delay)

    save_checkpoint(ckpt, done)
    conn.close()
    print(f"\n✔ Listo. {total_rows} filas en {out}. Entidades procesadas: {len(done)}.")


if __name__ == "__main__":
    main()
