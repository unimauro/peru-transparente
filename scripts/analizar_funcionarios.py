"""Analiza el CSV de funcionarios y produce una visión de PUESTOS CLAVE.

Clasifica cada cargo en un nivel jerárquico (Alta Dirección → Jefatura → Profesional/
Apoyo) y reporta:
  - Total de personas y por entidad.
  - Conteo de cargos clave (ministros, viceministros, secretarios generales,
    directores, gerentes, jefes) — para dimensionar "personas clave".
  - Genera funcionarios_clave.csv (solo alta dirección + jefaturas).

Uso: python scripts/analizar_funcionarios.py --in data/funcionarios.csv
"""
from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

# Orden importa: se evalúa de mayor a menor jerarquía.
NIVELES = [
    ("Ministro/Titular", re.compile(r"\bMINISTR[OA]\b|\bPRESIDENTE EJECUTIV|\bTITULAR\b", re.I)),
    ("Viceministro", re.compile(r"\bVICE\s?MINISTR", re.I)),
    ("Secretario General", re.compile(r"\bSECRETARI[OA] GENERAL\b", re.I)),
    ("Gerente General", re.compile(r"\bGERENTE GENERAL\b", re.I)),
    ("Director/a", re.compile(r"\bDIRECTOR(A|ES|AS)?\b|\bDIRECCI[ÓO]N\b", re.I)),
    ("Gerente", re.compile(r"\bGERENTE\b|\bGERENCIA\b", re.I)),
    ("Jefe/a", re.compile(r"\bJEFE\b|\bJEFA\b|\bJEFATURA\b", re.I)),
    ("Subdirector/Subgerente", re.compile(r"\bSUB\s?(DIRECTOR|GERENTE|JEFE)", re.I)),
    ("Asesor", re.compile(r"\bASESOR", re.I)),
    ("Coordinador", re.compile(r"\bCOORDINADOR", re.I)),
]
CLAVE = {"Ministro/Titular", "Viceministro", "Secretario General", "Gerente General",
         "Director/a", "Gerente", "Jefe/a", "Subdirector/Subgerente"}


def nivel(cargo: str) -> str:
    for name, rx in NIVELES:
        if rx.search(cargo or ""):
            return name
    return "Profesional/Apoyo"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="data/funcionarios.csv")
    ap.add_argument("--out-clave", default="data/funcionarios_clave.csv")
    args = ap.parse_args()

    rows = list(csv.DictReader(Path(args.inp).open(encoding="utf-8")))
    if not rows:
        print("CSV vacío."); return

    niv_count = Counter()
    por_entidad = defaultdict(Counter)
    entidades = {}
    clave_rows = []
    for r in rows:
        n = nivel(r.get("cargo", ""))
        niv_count[n] += 1
        eid = r.get("id_entidad")
        entidades[eid] = r.get("entidad", "")
        por_entidad[eid][n] += 1
        if n in CLAVE:
            clave_rows.append({**r, "nivel": n})

    total = len(rows)
    clave = len(clave_rows)
    print(f"\n===== VISIÓN GENERAL =====")
    print(f"Registros (personas-cargo): {total}")
    print(f"Entidades: {len(entidades)}")
    print(f"Cargos CLAVE (alta dirección + jefaturas): {clave}  ({clave*100//total}% del total)")

    print(f"\n===== POR NIVEL JERÁRQUICO =====")
    for name, _ in NIVELES + [("Profesional/Apoyo", None)]:
        if niv_count.get(name):
            print(f"  {name:28} {niv_count[name]:>6}")

    print(f"\n===== PERSONAS CLAVE POR ENTIDAD =====")
    ranking = sorted(entidades, key=lambda e: -sum(por_entidad[e][k] for k in CLAVE))
    for eid in ranking[:25]:
        kc = sum(por_entidad[eid][k] for k in CLAVE)
        tot = sum(por_entidad[eid].values())
        print(f"  [{eid:>4}] {entidades[eid][:50]:50} clave={kc:>4}  total={tot:>5}")

    # CSV de solo cargos clave
    if clave_rows:
        out = Path(args.out_clave)
        with out.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(clave_rows[0].keys()))
            w.writeheader()
            w.writerows(clave_rows)
        print(f"\n✔ {clave} cargos clave → {out}")


if __name__ == "__main__":
    main()
