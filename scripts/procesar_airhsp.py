"""Agrega el AIRHSP del MEF (planilla oficial del Estado, sin nombres).

Stream del CSV grande (~600MB). Produce cobertura COMPLETA por tipo de empleo:
incluye docentes (Carreras Especiales), FF.AA./Policía, salud — los gaps del PTE.

Salida (data/):
  airhsp_por_regimen.csv         nacional por régimen laboral (n + sueldo prom.)
  airhsp_por_grupo.csv           por grupo ocupacional
  airhsp_por_pliego_regimen.csv  por entidad (pliego) × régimen
"""
from __future__ import annotations

import csv
import os
import sys
from collections import defaultdict

SRC = os.environ.get("AIRHSP_CSV", os.path.expanduser("~/salariosperu-data/mef_airhsp/PERSONALSP_2025.csv"))


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def latest_month(path: str) -> str:
    # archivo ordenado por mes ascendente → el último registro tiene el mes más reciente
    last = ""
    with open(path, encoding="utf-8", errors="ignore") as fh:
        r = csv.DictReader(fh)
        for row in r:
            m = (row.get("MES") or "").strip()
            if m:
                last = m if m > last else last
    return last


def main() -> None:
    csv.field_size_limit(sys.maxsize)
    target = os.environ.get("AIRHSP_MES") or latest_month(SRC)
    print(f"Mes objetivo (snapshot): {target}")
    by_reg = defaultdict(lambda: [0.0, 0.0])      # regimen -> [n, masa_mensual]
    by_grupo = defaultdict(lambda: [0.0, 0.0])
    by_pli = defaultdict(lambda: [0.0, 0.0])      # (pliego, regimen) -> [n, masa]
    rows = 0
    with open(SRC, encoding="utf-8", errors="ignore") as fh:
        r = csv.DictReader(fh)
        for row in r:
            if (row.get("MES") or "").strip() != target:
                continue
            n = num(row.get("CANTIDAD"))
            if n <= 0:
                continue
            # los montos ING_* son el TOTAL del grupo (no por persona)
            masa = (num(row.get("ING_IMPONIBLE_PERM_MENSUAL")) + num(row.get("ING_NO_IMPONIBLE_PERM_MENSUAL"))
                    + num(row.get("INCENTIVO_UNICO_MENSUAL")))
            reg = (row.get("DESC_REGIMEN_LABORAL") or "?").strip()
            grp = (row.get("DESC_GRUPO_OCASIONAL") or "?").strip()
            pli = (row.get("PLIEGO") or "?").strip()
            by_reg[reg][0] += n; by_reg[reg][1] += masa
            by_grupo[grp][0] += n; by_grupo[grp][1] += masa
            key = (pli, reg)
            by_pli[key][0] += n; by_pli[key][1] += masa
            rows += 1
            if rows % 500000 == 0:
                print(f"  …{rows:,} filas", flush=True)

    def dump(path, header, data_iter):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(header)
            for r in data_iter:
                w.writerow(r)

    dump("data/airhsp_por_regimen.csv", ["regimen", "n", "sueldo_promedio", "masa_mensual"],
         sorted(([k, int(v[0]), round(v[1] / v[0]) if v[0] else 0, round(v[1])] for k, v in by_reg.items()),
                key=lambda x: -x[1]))
    dump("data/airhsp_por_grupo.csv", ["grupo_ocupacional", "n", "sueldo_promedio", "masa_mensual"],
         sorted(([k, int(v[0]), round(v[1] / v[0]) if v[0] else 0, round(v[1])] for k, v in by_grupo.items()),
                key=lambda x: -x[1]))
    dump("data/airhsp_por_pliego_regimen.csv", ["pliego", "regimen", "n", "sueldo_promedio", "masa_mensual"],
         sorted(([p, rg, int(v[0]), round(v[1] / v[0]) if v[0] else 0, round(v[1])] for (p, rg), v in by_pli.items()),
                key=lambda x: -x[2]))

    tot = sum(v[0] for v in by_reg.values())
    masa = sum(v[1] for v in by_reg.values())
    print(f"\n✔ AIRHSP {os.path.basename(SRC)}: {int(tot):,} servidores · masa S/{round(masa):,}/mes · {len(by_pli)} pliego×régimen")
    print("Top régimen:")
    for k, v in sorted(by_reg.items(), key=lambda x: -x[1][0])[:8]:
        print(f"  {int(v[0]):>8,}  {k[:34]:34} prom S/{round(v[1]/v[0]) if v[0] else 0:,}")


if __name__ == "__main__":
    main()
