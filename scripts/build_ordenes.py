"""Agrega el rastreo de órdenes de servicio por locador y lo cruza con la planilla.

- Agrupa por RUC: nº de órdenes, monto total, entidades. Publica RUC y DNI completos tal
  como los expone el OECE (decisión 2026-10-30, docs/LEGAL.md) con enlace al record OCDS.
- CRUCE (scripts/cruce_planilla.py): ¿el locador figura también en la planilla del PTE?
  Primero por DNI (match "dni", ALTA), si no por nombre normalizado (match "nombre",
  POSSIBLE_ALTA, homónimo posible). Señal de doble percepción; no afirma irregularidad.

Salida: frontend/public/data/ordenes_servicio.json
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from cruce_planilla import IndicePlanilla, dni_de_ruc  # noqa: E402
from pii import enmascarar_pii  # noqa: E402

SRC = Path("data/ordenes_servicio.csv")
OUT = Path("frontend/public/data/ordenes_servicio.json")
RECORD_URL = "https://contratacionesabiertas.oece.gob.pe/api/v1/record/{ocid}"


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

    # planilla (actual + histórico) indexada por DNI y por tokens del nombre para el cruce
    planilla = IndicePlanilla()
    print(f"  planilla: {planilla.n_filas:,} filas · {len(planilla.por_dni):,} con DNI · "
          f"{len(planilla.por_tokens):,} nombres indexados")

    por_moneda: dict[str, dict] = defaultdict(lambda: {"n": 0, "monto": 0.0})
    by_ruc = defaultdict(lambda: {"nombre": "", "dni": "", "n": 0, "monto": 0.0, "entidades": set(),
                                  "desc": set(), "_ocids": set(), "ocid": ""})
    fechas: list[str] = []
    for r in rows(SRC):
        if not r.get("ruc"):
            continue
        moneda = (r.get("moneda") or "").strip().upper() or "?"
        try:
            por_moneda[moneda]["n"] += 1
            por_moneda[moneda]["monto"] += float(r["monto"])
        except (TypeError, ValueError):
            pass
        if moneda != "PEN":
            continue   # USD etc.: se cuentan aparte, no se suman como soles
        g = by_ruc[r["ruc"]]
        oc = r.get("ocid", "")
        if oc in g["_ocids"]:   # evitar contar 2 veces la misma orden (re-runs del sweep)
            continue
        g["_ocids"].add(oc)
        g["ocid"] = g["ocid"] or oc
        g["dni"] = g["dni"] or (r.get("dni") or dni_de_ruc(r["ruc"]))
        f = (r.get("fecha") or "")[:7]
        if f:
            fechas.append(f)
        g["nombre"] = r["proveedor"]
        g["n"] += 1
        try:
            g["monto"] += float(r["monto"])
        except (TypeError, ValueError):
            pass
        g["entidades"].add(r["entidad"])
        if r["descripcion"]:
            g["desc"].add(enmascarar_pii(r["descripcion"][:50]))

    items = []
    cruces = []
    for ruc, g in by_ruc.items():
        cz = planilla.buscar(g["nombre"], g["dni"])
        rec = {
            "id": hashlib.sha256(ruc.encode()).hexdigest()[:12],
            "ruc": ruc, "dni": g["dni"], "nombre": g["nombre"], "n": g["n"],
            "monto": round(g["monto"]), "entidades": len(g["entidades"]),
            "servicios": list(g["desc"])[:4],
            "fuente_url": RECORD_URL.format(ocid=g["ocid"]) if g["ocid"] else "",
            "en_planilla": bool(cz["match"]), "match": cz["match"], "confianza": cz["confianza"],
            "entidad_planilla": cz["entidad"],
        }
        items.append(rec)
        if cz["match"]:
            cruces.append(rec)

    items.sort(key=lambda x: -x["monto"])
    cruces.sort(key=lambda x: -x["monto"])
    total_monto = sum(g["monto"] for g in by_ruc.values())

    OUT.write_text(json.dumps({
        "total_locadores": len(by_ruc),
        "total_ordenes": sum(g["n"] for g in by_ruc.values()),
        "monto_total": round(total_monto),
        "periodo": [min(fechas), max(fechas)] if fechas else None,
        "_meta": {"fuente": "OECE / OCDS (contratacionesabiertas.oece.gob.pe)",
                  "fuente_url": "https://contratacionesabiertas.oece.gob.pe/",
                  "datos_personales": ("RUC y DNI (derivado del RUC de persona natural) se publican tal como los "
                                       "expone la fuente oficial, con enlace al record OCDS de cada locador "
                                       "(docs/LEGAL.md). Rectificaciones: carlos@cardenas.pe"),
                  "cruce": ("en_planilla/cruces: coincidencia con la planilla del PTE por DNI (match=dni, ALTA) o "
                            "por nombre normalizado (match=nombre, POSSIBLE_ALTA, homónimo posible). "
                            "Describe una coincidencia; no afirma irregularidad."),
                  "moneda": "PEN",
                  "nota_moneda": "Totales solo en soles (PEN); otras monedas se cuentan aparte en por_moneda.",
                  "por_moneda": {k: {"n": v["n"], "monto": round(v["monto"])} for k, v in por_moneda.items()}},
        "en_planilla": len(cruces),
        "en_planilla_dni": sum(1 for c in cruces if c["match"] == "dni"),
        "en_planilla_nombre": sum(1 for c in cruces if c["match"] == "nombre"),
        "top": items[:300],
        "cruces": cruces[:300],
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"✔ {len(by_ruc)} locadores · {sum(g['n'] for g in by_ruc.values())} órdenes · "
          f"S/{round(total_monto):,} · {len(cruces)} también en planilla "
          f"({sum(1 for c in cruces if c['match'] == 'dni')} por DNI, "
          f"{sum(1 for c in cruces if c['match'] == 'nombre')} por nombre)")


if __name__ == "__main__":
    main()
