"""Genera salarios.json para el Dashboard Salarial (distribución, top, por categoría/régimen)."""
from __future__ import annotations

import csv
import json
import os
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from clasificacion import categoria  # noqa: E402

OUT = Path("frontend/public/data/salarios.json")


def num(x):
    try:
        v = float(x)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


def main() -> None:
    rows = list(csv.DictReader(open("data/funcionarios.csv", encoding="utf-8")))
    sueldos = []
    top = []
    por_cat = defaultdict(list)
    por_reg = defaultdict(list)
    for r in rows:
        s = num(r["total_ingreso_mensual"])
        if s is None:
            continue
        sueldos.append(s)
        por_cat[categoria(r["entidad"])].append(s)
        por_reg[r["regimen"]].append(s)
        top.append((s, r["apellidos_nombres"], r["cargo"][:40], r["entidad"][:40]))

    # distribución (histograma)
    bins = [0, 1000, 2000, 3000, 4000, 5000, 7000, 10000, 15000, 20000, 30000, 1e12]
    labels = ["<1k", "1-2k", "2-3k", "3-4k", "4-5k", "5-7k", "7-10k", "10-15k", "15-20k", "20-30k", "30k+"]
    hist = [0] * (len(bins) - 1)
    for s in sueldos:
        for i in range(len(bins) - 1):
            if bins[i] <= s < bins[i + 1]:
                hist[i] += 1
                break

    top.sort(reverse=True)
    top_list = [{"sueldo": round(s), "nombre": n, "cargo": c, "entidad": e} for s, n, c, e in top[:40]]

    def stats(vals):
        vals = sorted(vals)
        return {"n": len(vals), "mediana": round(st.median(vals)),
                "p25": round(vals[len(vals) // 4]), "p75": round(vals[len(vals) * 3 // 4]),
                "max": round(max(vals))}

    cat_stats = sorted(([k, *stats(v).values()] for k, v in por_cat.items() if len(v) >= 20),
                       key=lambda x: -x[2])  # por mediana
    reg_stats = sorted(([k, *stats(v).values()] for k, v in por_reg.items() if len(v) >= 5),
                       key=lambda x: -x[1])  # por n

    OUT.write_text(json.dumps({
        "total_con_sueldo": len(sueldos),
        "mediana_nacional": round(st.median(sueldos)),
        "promedio_nacional": round(st.mean(sueldos)),
        "hist_labels": labels, "hist": hist,
        "top": top_list,
        "por_categoria": [{"categoria": c[0], "n": c[1], "mediana": c[2], "p25": c[3], "p75": c[4], "max": c[5]} for c in cat_stats],
        "por_regimen": [{"regimen": c[0], "n": c[1], "mediana": c[2], "p25": c[3], "p75": c[4], "max": c[5]} for c in reg_stats],
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"✔ salarios.json · mediana nacional S/{round(st.median(sueldos)):,} · {len(sueldos):,} con sueldo")


if __name__ == "__main__":
    main()
