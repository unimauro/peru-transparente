"""Divide las entidades NO procesadas en N shards para barrido paralelo (multi-worker).

Respeta la prioridad del catálogo (reguladores/ministerios/etc. ya van arriba) y
reparte round-robin para balancear. Excluye las ya procesadas (checkpoint global).

Uso: python scripts/preparar_shards.py --workers 5
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--catalogo", default="data/entidades.csv")
    ap.add_argument("--checkpoint", default="data/funcionarios.checkpoint.json")
    ap.add_argument("--outdir", default="data/shards")
    args = ap.parse_args()

    done: set[int] = set()
    ck = Path(args.checkpoint)
    if ck.exists():
        done = set(json.loads(ck.read_text()).get("done", []))

    ids = [int(r["id_entidad"]) for r in csv.DictReader(open(args.catalogo, encoding="utf-8"))]
    remaining = [i for i in ids if i not in done]

    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    shards: list[list[int]] = [[] for _ in range(args.workers)]
    for idx, eid in enumerate(remaining):
        shards[idx % args.workers].append(eid)

    for i, sh in enumerate(shards):
        with (out / f"shard_{i}.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["id_entidad"])
            w.writeheader()
            for eid in sh:
                w.writerow({"id_entidad": eid})

    print(f"{len(remaining)} entidades pendientes (de {len(ids)}; {len(done)} ya procesadas)")
    print(f"Repartidas en {args.workers} shards (~{len(remaining)//args.workers} c/u) en {out}/")


if __name__ == "__main__":
    main()
