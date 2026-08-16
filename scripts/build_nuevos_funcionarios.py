"""Sección "Nuevos Funcionarios": incorporaciones al Estado desde una fecha de corte.

Combina DOS fuentes (principio de trazabilidad, cada fila declara su origen y confianza):

  A) Designaciones oficiales de El Peruano (data/designaciones.csv) con fecha ≥ corte.
     Es el hecho publicado con fecha exacta de nombramiento → confianza ALTA.

  B) Altas en planilla: personas presentes en la planilla actual (funcionarios.csv, 2026)
     que NO estaban en el último snapshot histórico (funcionarios_historico.csv, 2025),
     acotado a CARGOS CLAVE (jefaturas ↑) para que sea señal útil y no ruido masivo.
     Es una inferencia por comparación de snapshots (no hay fecha exacta) →
     confianza POSSIBLE_ALTA (anti-overclaiming, principio #2).

SALARIOS ("cruzar todo lo que se tenga"):
  1) match individual por nombre+entidad en funcionarios.csv → sueldo exacto de planilla.
  2) si no hay match (designación demasiado reciente para figurar en planilla) → rango
     REFERENCIAL por entidad+régimen desde salarios_pt_por_entidad_regimen.csv (mediana).
  Cada fila marca el origen del monto (`salario_tipo`: "planilla" | "referencial" | null).

Salida: frontend/public/data/nuevos_funcionarios.json
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "scripts")
from build_site_data import CLAVE, nivel  # noqa: E402

CORTE_DEFAULT = "2026-07-21"
OUT = Path("frontend/public/data/nuevos_funcionarios.json")
FUN = Path("data/funcionarios.csv")
HIST = Path("data/funcionarios_historico.csv")
DESIG = Path("data/designaciones.csv")
SAL_ENT = Path("data/salarios_pt_por_entidad_regimen.csv")


def na(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKD", s or "")
                  .encode("ascii", "ignore").decode().upper()).strip()


def rows(path: Path):
    """csv.DictReader tolerante a bytes NUL (líneas corruptas del scraping)."""
    fh = path.open(encoding="utf-8", errors="ignore", newline="")
    return csv.DictReader(line.replace("\x00", "") for line in fh)


def to_num(s: str) -> float:
    try:
        return float(s)
    except (TypeError, ValueError):
        return 0.0


def cargar_planilla() -> tuple[dict, dict]:
    """Índice de la planilla actual: sueldo por nombre+entidad y por nombre suelto."""
    por_ne: dict[tuple[str, str], dict] = {}
    por_n: dict[str, dict] = {}
    for r in rows(FUN):
        nm = na(r.get("apellidos_nombres", ""))
        if not nm:
            continue
        rec = {
            "cargo": r.get("cargo", ""),
            "dependencia": r.get("dependencia", ""),
            "entidad": r.get("entidad", ""),
            "id_entidad": r.get("id_entidad", ""),
            "regimen": r.get("regimen", ""),
            "total": to_num(r.get("total_ingreso_mensual", "")),
            "fuente_url": r.get("fuente_url", ""),
        }
        por_ne[(nm, na(r.get("entidad", "")))] = rec
        por_n.setdefault(nm, rec)
    return por_ne, por_n


def cargar_referencial() -> dict:
    """Mediana salarial por (id_entidad, régimen) para el salario referencial."""
    ref: dict[tuple[str, str], dict] = {}
    if not SAL_ENT.exists():
        return ref
    for r in rows(SAL_ENT):
        ref[(r.get("id_entidad", ""), r.get("regimen", ""))] = {
            "mediana": to_num(r.get("mediana", "")),
            "p25": to_num(r.get("p25", "")),
            "p75": to_num(r.get("p75", "")),
        }
    return ref


def salario_de(nombre: str, entidad: str, regimen: str, id_ent: str,
               por_ne, por_n, ref) -> dict:
    """Cruza todo lo disponible: primero planilla individual, luego referencial."""
    nm = na(nombre)
    hit = por_ne.get((nm, na(entidad))) or por_n.get(nm)
    if hit and hit["total"] > 0:
        return {"salario": round(hit["total"]), "salario_tipo": "planilla",
                "regimen": hit.get("regimen") or regimen}
    rg = (hit or {}).get("regimen") or regimen
    ie = (hit or {}).get("id_entidad") or id_ent
    r = ref.get((ie, rg))
    if r and r["mediana"] > 0:
        return {"salario": round(r["mediana"]), "salario_tipo": "referencial",
                "salario_rango": [round(r["p25"]), round(r["p75"])], "regimen": rg}
    return {"salario": None, "salario_tipo": None, "regimen": rg}


def altas_planilla(por_n) -> list[dict]:
    """Cargos clave presentes hoy (2026) y ausentes del snapshot 2025."""
    prev: dict[str, set] = defaultdict(set)
    if HIST.exists():
        for r in rows(HIST):
            if r.get("anio") != "2025":
                continue
            prev[r.get("id_entidad", "")].add(na(r.get("apellidos_nombres", "")))
    if not any(prev.values()):
        return []  # sin snapshot 2025 comparable → no inferimos altas
    items = []
    for r in rows(FUN):
        cargo = r.get("cargo", "")
        if nivel(cargo) not in CLAVE:
            continue
        eid = r.get("id_entidad", "")
        nm = na(r.get("apellidos_nombres", ""))
        if not nm or eid not in prev or nm in prev[eid]:
            continue
        items.append({
            "nombre": r.get("apellidos_nombres", "").title(),
            "cargo": cargo, "entidad": r.get("entidad", ""),
            "dependencia": r.get("dependencia", ""), "id_entidad": eid,
            "regimen": r.get("regimen", ""), "fecha": "",
            "nivel": nivel(cargo), "fuente": "planilla",
            "confianza": "POSSIBLE_ALTA",
            "fuente_url": r.get("fuente_url", ""), "norma": "",
        })
    return items


def designaciones(corte: str) -> list[dict]:
    """Designaciones oficiales de El Peruano con fecha ≥ corte."""
    if not DESIG.exists():
        return []
    items = []
    for r in rows(DESIG):
        f = r.get("fecha", "")
        if not f or f < corte:
            continue
        items.append({
            "nombre": (r.get("nombre") or "").title(),
            "cargo": r.get("cargo", ""), "entidad": r.get("entidad", ""),
            "dependencia": "", "id_entidad": "", "regimen": "",
            "fecha": f, "nivel": nivel(r.get("cargo", "")),
            "fuente": "el_peruano", "confianza": "ALTA",
            "fuente_url": r.get("fuente_url", ""), "norma": r.get("norma", ""),
        })
    return items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corte", default=CORTE_DEFAULT, help="aaaa-mm-dd (por defecto 2026-07-21)")
    args = ap.parse_args()
    corte = args.corte

    por_ne, por_n = cargar_planilla()
    ref = cargar_referencial()

    crudos = designaciones(corte) + altas_planilla(por_n)

    # dedup por (nombre, entidad, cargo); la designación oficial gana sobre el alta inferida
    orden = {"el_peruano": 0, "planilla": 1}
    crudos.sort(key=lambda x: orden.get(x["fuente"], 9))
    vistos: set = set()
    items = []
    for it in crudos:
        # El Peruano: cada norma es única → dedup por su URL (el nombre suele ir en blanco).
        # Planilla: dedup por persona+entidad+cargo.
        k = it["fuente_url"] if it["fuente"] == "el_peruano" and it["fuente_url"] \
            else (na(it["nombre"]), na(it["entidad"]), na(it["cargo"]))
        if k in vistos:
            continue
        vistos.add(k)
        it.update(salario_de(it["nombre"], it["entidad"], it["regimen"],
                             it["id_entidad"], por_ne, por_n, ref))
        items.append(it)

    # orden de presentación: primero designaciones con fecha (más reciente), luego altas
    items.sort(key=lambda x: (x["fuente"] != "el_peruano", x.get("fecha", "") == "",
                              -_fecha_key(x.get("fecha", "")), x["entidad"]))

    con_salario = sum(1 for x in items if x.get("salario"))
    oficiales = sum(1 for x in items if x["fuente"] == "el_peruano")
    data = {
        "meta": {
            "corte": corte,
            "generado": time.strftime("%Y-%m-%d"),
            "provenance": {
                "designaciones": "Diario Oficial El Peruano · Normas Legales (busquedas.elperuano.pe)",
                "altas": "Portal de Transparencia Estándar · planilla 2026 vs snapshot 2025",
                "salarios": "PTE (sueldo individual) · salarios_pt_por_entidad_regimen (referencial por cargo)",
            },
            "nota": ("Los ‘nuevos’ por planilla son altas inferidas por comparación de snapshots "
                     "(sin fecha exacta, confianza POSSIBLE_ALTA); las designaciones de El Peruano "
                     "llevan fecha y norma. No se imputa irregularidad alguna."),
        },
        "total": len(items),
        "oficiales": oficiales,
        "altas_planilla": len(items) - oficiales,
        "con_salario": con_salario,
        "items": items[:1000],
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"✔ nuevos_funcionarios.json · {len(items)} nuevos "
          f"({oficiales} designaciones El Peruano · {len(items) - oficiales} altas planilla) · "
          f"{con_salario} con salario · corte {corte}")


def _fecha_key(f: str) -> int:
    return int(f.replace("-", "")) if f else 0


if __name__ == "__main__":
    main()
