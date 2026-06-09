"""Barre OCDS/OECE y extrae LOCADORES (proveedor persona natural, RUC 10…).

Son personas que prestan servicios al Estado por orden de servicio / locación —
no van en la planilla del PTE. Trae nombre, RUC, entidad, monto, fecha.
Resumable por página (data/locadores.checkpoint.json). Append a data/locadores_ocds.csv.
"""
from __future__ import annotations

import csv
import json
import os
import time
from pathlib import Path

import httpx

BASE = "https://contratacionesabiertas.oece.gob.pe/api/v1/releases"
UA = "PeruTransparente/1.0 (+https://github.com/unimauro/peru-transparente)"
OUT = Path("data/locadores_ocds.csv")
CKPT = Path("data/locadores.checkpoint.json")
FIELDS = ["ocid", "entidad", "proveedor_ruc", "proveedor", "monto", "moneda", "fecha"]


def main() -> None:
    start = json.loads(CKPT.read_text())["page"] if CKPT.exists() else 1
    max_minutes = float(os.environ.get("LOC_MAX_MIN", "0"))
    deadline = time.monotonic() + max_minutes * 60 if max_minutes else None
    cl = httpx.Client(timeout=60, headers={"User-Agent": UA})
    write_header = not OUT.exists() or OUT.stat().st_size == 0
    seen: set = set()
    total = 0
    with OUT.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if write_header:
            w.writeheader()
        page = start
        while True:
            if deadline and time.monotonic() > deadline:
                break
            try:
                d = cl.get(BASE, params={"page": page, "pageSize": 100}).json()
            except Exception:
                time.sleep(5)
                continue
            rels = d.get("releases", [])
            if not rels:
                break
            for r in rels:
                buyer = (r.get("buyer") or {}).get("name")
                for aw in r.get("awards", []):
                    val = aw.get("value") or {}
                    for s in aw.get("suppliers", []):
                        ruc = (s.get("id") or "").replace("PE-RUC-", "")
                        if ruc.startswith("10"):
                            k = (r.get("ocid"), ruc)
                            if k in seen:
                                continue
                            seen.add(k)
                            w.writerow({"ocid": r.get("ocid"), "entidad": buyer, "proveedor_ruc": ruc,
                                        "proveedor": s.get("name"), "monto": val.get("amount"),
                                        "moneda": val.get("currency"), "fecha": aw.get("date")})
                            total += 1
            fh.flush()
            if page % 20 == 0:
                CKPT.write_text(json.dumps({"page": page}))
                print(f"  página {page} · {total} locadores acumulados (esta corrida)", flush=True)
            page += 1
    CKPT.write_text(json.dumps({"page": page}))
    cl.close()
    print(f"✔ {total} locadores nuevos · siguiente página {page}")


if __name__ == "__main__":
    main()
