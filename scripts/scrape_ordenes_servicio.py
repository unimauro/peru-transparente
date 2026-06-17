"""Rastreo de ÓRDENES DE SERVICIO a personas naturales (locadores) vía OCDS/OECE.

Filtra adjudicaciones donde el proveedor es persona natural (RUC 10…) y el objeto
es un SERVICIO (no bien ni alquiler). El RUC contiene el DNI (10 + DNI(8) + dígito),
lo que permite rastrear a cada locador e incluso cruzarlo con la planilla.

Resumable por página (data/ordenes.checkpoint.json). Append a data/ordenes_servicio.csv.
Uso: python scripts/scrape_ordenes_servicio.py --max-minutes 60
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

import httpx

BASE = "https://contratacionesabiertas.oece.gob.pe/api/v1/releases"
UA = "PeruTransparente/1.0 (+https://github.com/unimauro/peru-transparente)"
OUT = Path("data/ordenes_servicio.csv")
CKPT = Path("data/ordenes.checkpoint.json")
FIELDS = ["ocid", "entidad", "ruc", "dni", "proveedor", "monto", "moneda", "fecha", "descripcion"]
EXCLUIR = ("ALQUILER", "ARRENDAMIENTO", "INMUEBLE", "LOCAL ", "VEHICUL")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-minutes", type=float, default=0)
    ap.add_argument("--page-size", type=int, default=100)
    args = ap.parse_args()

    page = json.loads(CKPT.read_text())["page"] if CKPT.exists() else 1
    deadline = time.monotonic() + args.max_minutes * 60 if args.max_minutes else None
    cl = httpx.Client(timeout=60, headers={"User-Agent": UA})
    write_header = not OUT.exists() or OUT.stat().st_size == 0
    seen: set = set()
    total = 0
    with OUT.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if write_header:
            w.writeheader()
        while True:
            if deadline and time.monotonic() > deadline:
                break
            try:
                d = cl.get(BASE, params={"page": page, "pageSize": args.page_size}).json()
            except Exception:
                time.sleep(5)
                continue
            rels = d.get("releases", [])
            if not rels:
                break
            for r in rels:
                buyer = (r.get("buyer") or {}).get("name")
                mpc = (r.get("tender") or {}).get("mainProcurementCategory")
                if mpc != "services":
                    continue
                for aw in r.get("awards", []) or []:
                    val = aw.get("value") or {}
                    items = aw.get("items", []) or [{}]
                    desc = ((items[0].get("classification") or {}).get("description") or "")[:60]
                    if any(k in desc.upper() for k in EXCLUIR):
                        continue
                    for s in aw.get("suppliers", []) or []:
                        ruc = str(s.get("id") or "").replace("PE-RUC-", "")
                        if not ruc.startswith("10") or len(ruc) != 11:
                            continue
                        k = (r.get("ocid"), ruc)
                        if k in seen:
                            continue
                        seen.add(k)
                        w.writerow({"ocid": r.get("ocid"), "entidad": buyer, "ruc": ruc,
                                    "dni": ruc[2:10], "proveedor": s.get("name"),
                                    "monto": val.get("amount"), "moneda": val.get("currency"),
                                    "fecha": aw.get("date"), "descripcion": desc})
                        total += 1
            if page % 50 == 0:
                CKPT.write_text(json.dumps({"page": page}))
                fh.flush()
                print(f"  página {page} · {total} locadores-servicio acumulados", flush=True)
            page += 1
    CKPT.write_text(json.dumps({"page": page}))
    cl.close()
    print(f"✔ {total} órdenes de servicio nuevas · próxima página {page}")


if __name__ == "__main__":
    main()
