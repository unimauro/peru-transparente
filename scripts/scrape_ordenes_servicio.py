"""Rastreo de ÓRDENES DE SERVICIO a personas naturales (locadores) vía OCDS/OECE.

Filtra adjudicaciones donde el proveedor es persona natural (RUC 10…) y el objeto
es un SERVICIO (no bien ni alquiler).

PRIVACIDAD: el RUC de persona natural embebe el DNI (10 + DNI + dígito). Se guarda el RUC
solo en el CSV LOCAL (no versionado, ver .gitignore) porque es la clave de deduplicación;
NUNCA se deriva ni persiste el DNI como campo, y build_ordenes.py publica el RUC
enmascarado (ver scripts/pii.py).

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
FIELDS = ["ocid", "entidad", "ruc", "proveedor", "monto", "moneda", "fecha", "descripcion"]
EXCLUIR = ("ALQUILER", "ARRENDAMIENTO", "INMUEBLE", "LOCAL ", "VEHICUL")


def clave(r: dict) -> tuple:
    """Identidad de una orden: (ocid, ruc, fecha, monto). El append entre corridas la repetía."""
    return (r.get("ocid", ""), r.get("ruc", ""), r.get("fecha", ""), r.get("monto", ""))


def normalizar_csv(path: Path = OUT) -> set:
    """Reescribe el CSV sin la columna `dni` (barridos antiguos) y sin filas duplicadas.

    Devuelve el conjunto de claves ya guardadas para que el barrido no vuelva a añadirlas.
    """
    if not path.exists() or path.stat().st_size == 0:
        return set()
    with path.open(encoding="utf-8", errors="ignore", newline="") as fh:
        rd = csv.DictReader(line.replace("\x00", "") for line in fh)
        tenia_dni = bool(rd.fieldnames and "dni" in rd.fieldnames)
        filas, vistas, dup = [], set(), 0
        for r in rd:
            k = clave(r)
            if k in vistas:
                dup += 1
                continue
            vistas.add(k)
            filas.append({f: r.get(f, "") for f in FIELDS})
    if tenia_dni or dup:
        tmp = path.with_suffix(".csv.tmp")
        with tmp.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(filas)
        tmp.replace(path)
        print(f"  CSV normalizado: {len(filas)} filas"
              + (" · columna dni purgada" if tenia_dni else "")
              + (f" · {dup} duplicadas eliminadas" if dup else ""))
    return vistas


def purgar_columna_dni(path: Path = OUT) -> bool:   # compat
    return bool(normalizar_csv(path))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-minutes", type=float, default=0)
    ap.add_argument("--page-size", type=int, default=100)
    args = ap.parse_args()

    guardadas = normalizar_csv()
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
                        fila = {"ocid": r.get("ocid"), "entidad": buyer, "ruc": ruc,
                                "proveedor": s.get("name"),
                                "monto": val.get("amount"), "moneda": val.get("currency"),
                                "fecha": aw.get("date"), "descripcion": desc}
                        if clave({k2: "" if v is None else str(v) for k2, v in fila.items()}) in guardadas:
                            continue   # ya estaba en el CSV de una corrida anterior
                        w.writerow(fila)
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
