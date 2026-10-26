#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agrega el AIRHSP del MEF (planilla oficial del Estado, sin nombres).

Fuente: datos abiertos MEF, dataset "Personal activo y pensionista del sector público registrado
en el AIRHSP" (PERSONALSP_AAAA.csv, ~600 MB por año; stream, sin pandas). Cobertura: Gobierno
Nacional y Gobierno Regional (sin municipalidades, EsSalud, FONAFE, BCRP, SBS, SUNAT).

El dataset mezcla ACTIVOS con PENSIONISTAS/SOBREVIVIENTES, modalidad formativa y plazas VACANTES:
    DESC_TIPO_REGISTRO  -> Activos | Contrato Administrativo de Servicios | Convenio de Administración
                           | Pensionistas | Sobrevivientes | CPMP | Palmas Magisteriales | Reconocimientos Estatales
                           | Modalidad Formativa | Promotoras
    ESTADO_REGISTRO     -> OCUPADO | VACANTE
Este script separa activos / pensiones / formativa, cuenta las vacantes aparte (fuera del headcount)
y usa COSTO_TOTAL_ANUAL para el costo anual (incluye aguinaldos, escolaridad y aportes; la
"masa mensual" = ingresos permanentes del mes, sin esos conceptos).

Salidas (snapshot del mes objetivo, por defecto el último mes del archivo):
  data/airhsp_por_regimen.csv, data/airhsp_por_grupo.csv, data/airhsp_por_pliego_regimen.csv
      (legado: TODOS los registros con CANTIDAD>0, incl. pensionistas y vacantes; los usan otras páginas)
  data/airhsp_resumen.json        resumen completo (activos/pensiones/formativa/vacantes + cortes)
  frontend/public/data/airhsp.json  campos legado (periodo,total,masa_mensual,por_regimen,por_grupo)
                                    + los campos nuevos
Con --serie recorre todos los PERSONALSP_*.csv del directorio y escribe
  data/airhsp_headcount_anual.csv  (un snapshot por año: último mes disponible; 2020 llega a mes 11)

Uso:
  python scripts/procesar_airhsp.py                       # snapshot PERSONALSP_2025.csv
  AIRHSP_CSV=... AIRHSP_MES=06 python scripts/procesar_airhsp.py
  python scripts/procesar_airhsp.py --serie               # headcount 2017..2025
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data")
SRC = os.environ.get("AIRHSP_CSV", os.path.expanduser("~/salariosperu-data/mef_airhsp/PERSONALSP_2025.csv"))
DATASET_URL = ("https://www.datosabiertos.gob.pe/dataset/"
               "personal-activo-y-pensionista-del-sector-p%C3%BAblico-registrado-en-el-airhsp")
COBERTURA = "Gobierno Nacional y Regional; sin municipalidades, EsSalud, FONAFE, BCRP, SBS, SUNAT"

ACTIVOS_TIPOS = {"Activos", "Contrato Administrativo de Servicios", "Convenio de Administración"}
PENSION_TIPOS = {"Pensionistas", "Sobrevivientes", "CPMP", "Palmas Magisteriales", "Reconocimientos Estatales"}
FORMATIVA_TIPOS = {"Modalidad Formativa", "Promotoras"}
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def grupo_de(tipo: str) -> str:
    if tipo in ACTIVOS_TIPOS:
        return "activos"
    if tipo in PENSION_TIPOS:
        return "pensiones"
    if tipo in FORMATIVA_TIPOS:
        return "formativa"
    return "otros"


def latest_month(path: str) -> str:
    """El archivo viene ordenado por mes ascendente: basta mirar la cola. Si no se puede, escanea todo."""
    try:
        with open(path, "rb") as fh:
            fh.seek(0, 2)
            size = fh.tell()
            fh.seek(max(0, size - 4_000_000))
            tail = fh.read().decode("utf-8", errors="ignore").splitlines()[1:]
        meses = [row[2] for row in csv.reader(tail) if len(row) > 3 and row[2].isdigit()]
        if meses:
            return max(meses)
    except OSError:
        pass
    last = ""
    with open(path, encoding="utf-8-sig", errors="ignore") as fh:
        for row in csv.DictReader(fh):
            m = (row.get("MES") or "").strip()
            last = m if m > last else last
    return last


class Agg:
    """Acumuladores de una pasada por el CSV para un mes."""

    def __init__(self):
        z = lambda: [0.0, 0.0, 0.0]  # n, masa_mensual, costo_anual
        self.legacy_reg = defaultdict(z)
        self.legacy_grupo = defaultdict(z)
        self.legacy_pli = defaultdict(z)
        self.grupo = defaultdict(z)            # activos/pensiones/formativa/otros (solo OCUPADO)
        self.vacantes = z()
        self.vacantes_grupo = defaultdict(z)
        self.act_reg = defaultdict(z)
        self.act_nivel = defaultdict(z)
        self.act_sector = defaultdict(z)
        self.act_tipo = defaultdict(z)
        self.pen_tipo = defaultdict(z)
        self.otros_tipos = defaultdict(z)
        self.rows = 0
        self.niveles = set()

    def add(self, row):
        n = num(row.get("CANTIDAD"))
        if n <= 0:
            return
        masa = (num(row.get("ING_IMPONIBLE_PERM_MENSUAL")) + num(row.get("ING_NO_IMPONIBLE_PERM_MENSUAL"))
                + num(row.get("INCENTIVO_UNICO_MENSUAL")))
        cta = num(row.get("COSTO_TOTAL_ANUAL"))
        reg = (row.get("DESC_REGIMEN_LABORAL") or "?").strip()
        grp = (row.get("DESC_GRUPO_OCASIONAL") or "?").strip()
        pli = (row.get("PLIEGO") or "?").strip()
        tipo = (row.get("DESC_TIPO_REGISTRO") or "?").strip()
        estado = (row.get("ESTADO_REGISTRO") or "").strip().upper()
        nivel = (row.get("NIVEL") or "?").strip()
        sector = (row.get("SECTOR") or "?").strip()
        self.niveles.add(nivel)
        for d, k in ((self.legacy_reg, reg), (self.legacy_grupo, grp), (self.legacy_pli, (pli, reg))):
            a = d[k]; a[0] += n; a[1] += masa; a[2] += cta
        g = grupo_de(tipo)
        if estado == "VACANTE":
            self.vacantes[0] += n; self.vacantes[1] += masa; self.vacantes[2] += cta
            a = self.vacantes_grupo[g]; a[0] += n; a[1] += masa; a[2] += cta
            return
        a = self.grupo[g]; a[0] += n; a[1] += masa; a[2] += cta
        if g == "activos":
            for d, k in ((self.act_reg, reg), (self.act_nivel, nivel), (self.act_sector, sector), (self.act_tipo, tipo)):
                a = d[k]; a[0] += n; a[1] += masa; a[2] += cta
        elif g == "pensiones":
            a = self.pen_tipo[tipo]; a[0] += n; a[1] += masa; a[2] += cta
        elif g == "otros":
            a = self.otros_tipos[tipo]; a[0] += n; a[1] += masa; a[2] += cta
        self.rows += 1


def aggregate(path: str, mes: str) -> Agg:
    csv.field_size_limit(sys.maxsize)
    agg = Agg()
    seen = 0
    with open(path, encoding="utf-8-sig", errors="ignore") as fh:
        for row in csv.DictReader(fh):
            seen += 1
            if seen % 1_000_000 == 0:
                print(f"  …{seen:,} filas leídas", flush=True)
            if (row.get("MES") or "").strip() != mes:
                continue
            agg.add(row)
    return agg


def stat(v, extra_key=None):
    n, masa, cta = v
    d = {"n": int(round(n)), "masa": int(round(masa)), "prom": int(round(masa / n)) if n else 0, "costo_anual": int(round(cta))}
    return d


def breakdown(d, key, top=None, sort_by="masa"):
    items = [{key: k, **stat(v)} for k, v in d.items()]
    items.sort(key=lambda x: -x[sort_by])
    return items[:top] if top else items


def resumen(agg: Agg, anio: str, mes: str, path: str) -> dict:
    act, pen, form = agg.grupo["activos"], agg.grupo["pensiones"], agg.grupo["formativa"]
    total_reg = sum(v[0] for v in agg.legacy_reg.values())
    total_masa = sum(v[1] for v in agg.legacy_reg.values())
    total_cta = sum(v[2] for v in agg.legacy_reg.values())
    r = {
        "periodo": f"{MESES[int(mes) - 1]} {anio}", "anio": int(anio), "mes": int(mes),
        "fuente": "AIRHSP — MEF (datos abiertos)", "fuente_url": DATASET_URL, "cobertura": COBERTURA,
        "archivo": os.path.basename(path), "capturado_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total_registros": int(round(total_reg)), "masa_mensual_total": int(round(total_masa)),
        "costo_anual_total": int(round(total_cta)),
        "activos": {"registros": int(round(act[0])), "masa_mensual": int(round(act[1])), "costo_anual": int(round(act[2])),
                    "prom": int(round(act[1] / act[0])) if act[0] else 0,
                    "por_regimen": breakdown(agg.act_reg, "regimen"),
                    "por_nivel": breakdown(agg.act_nivel, "nivel"),
                    "por_sector": breakdown(agg.act_sector, "sector", top=12),
                    "por_tipo_registro": breakdown(agg.act_tipo, "tipo")},
        "pensiones": {"registros": int(round(pen[0])), "masa_mensual": int(round(pen[1])), "costo_anual": int(round(pen[2])),
                      "prom": int(round(pen[1] / pen[0])) if pen[0] else 0,
                      "detalle": breakdown(agg.pen_tipo, "tipo", sort_by="n")},
        "formativa": {"registros": int(round(form[0])), "masa_mensual": int(round(form[1])), "costo_anual": int(round(form[2]))},
        "vacantes": {"plazas": int(round(agg.vacantes[0])), "masa_mensual": int(round(agg.vacantes[1])),
                     "costo_anual": int(round(agg.vacantes[2])),
                     "por_grupo": {k: int(round(v[0])) for k, v in agg.vacantes_grupo.items()}},
        "otros_tipos_no_clasificados": breakdown(agg.otros_tipos, "tipo", sort_by="n"),
        "niveles": sorted(agg.niveles),
    }
    return r


def dump_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(header)
        for r in rows:
            w.writerow(r)


def write_snapshot(agg: Agg, anio: str, mes: str, path: str):
    os.makedirs(DATA, exist_ok=True)
    dump_csv(os.path.join(DATA, "airhsp_por_regimen.csv"), ["regimen", "n", "sueldo_promedio", "masa_mensual"],
             sorted(([k, int(v[0]), round(v[1] / v[0]) if v[0] else 0, round(v[1])] for k, v in agg.legacy_reg.items()),
                    key=lambda x: -x[1]))
    dump_csv(os.path.join(DATA, "airhsp_por_grupo.csv"), ["grupo_ocupacional", "n", "sueldo_promedio", "masa_mensual"],
             sorted(([k, int(v[0]), round(v[1] / v[0]) if v[0] else 0, round(v[1])] for k, v in agg.legacy_grupo.items()),
                    key=lambda x: -x[1]))
    dump_csv(os.path.join(DATA, "airhsp_por_pliego_regimen.csv"), ["pliego", "regimen", "n", "sueldo_promedio", "masa_mensual"],
             sorted(([p, rg, int(v[0]), round(v[1] / v[0]) if v[0] else 0, round(v[1])] for (p, rg), v in agg.legacy_pli.items()),
                    key=lambda x: -x[2]))
    res = resumen(agg, anio, mes, path)
    with open(os.path.join(DATA, "airhsp_resumen.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    # airhsp.json: campos legado intactos (otras páginas los leen) + campos nuevos
    out_json = os.path.join(ROOT, "frontend", "public", "data", "airhsp.json")
    legacy_reg = sorted(agg.legacy_reg.items(), key=lambda kv: -kv[1][0])
    legacy_grp = sorted(agg.legacy_grupo.items(), key=lambda kv: -kv[1][0])[:12]
    out = {
        "periodo": res["periodo"],
        "fuente": "AIRHSP — MEF (planilla oficial, agregado sin nombres)",
        "total": res["total_registros"], "masa_mensual": res["masa_mensual_total"],
        "por_regimen": [{"regimen": k, "n": int(v[0]), "prom": round(v[1] / v[0]) if v[0] else 0, "masa": round(v[1])} for k, v in legacy_reg],
        "por_grupo": [{"grupo": k, "n": int(v[0]), "prom": round(v[1] / v[0]) if v[0] else 0, "masa": round(v[1])} for k, v in legacy_grp],
        "nota_total": ("'total' y 'masa_mensual' cuentan TODOS los registros del AIRHSP: activos + pensionistas y "
                       "sobrevivientes + modalidad formativa + plazas vacantes. Para headcount usar 'activos'."),
        "fuente_url": DATASET_URL, "cobertura": COBERTURA,
        "total_registros": res["total_registros"], "costo_anual_total": res["costo_anual_total"],
        "activos": res["activos"], "pensiones": res["pensiones"], "formativa": res["formativa"], "vacantes": res["vacantes"],
    }
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    a, p = res["activos"], res["pensiones"]
    print(f"\n✔ AIRHSP {os.path.basename(path)} {res['periodo']}: {res['total_registros']:,} registros = "
          f"{a['registros']:,} activos (S/{a['masa_mensual']:,}/mes, S/{a['costo_anual']:,}/año, prom S/{a['prom']:,}) + "
          f"{p['registros']:,} pensiones (S/{p['masa_mensual']:,}/mes) + {res['formativa']['registros']:,} formativa + "
          f"{res['vacantes']['plazas']:,} vacantes")
    if res["otros_tipos_no_clasificados"]:
        print("  ADVERTENCIA tipos de registro no clasificados:", res["otros_tipos_no_clasificados"])
    return res


def serie(src_dir: str):
    rows = []
    for path in sorted(glob.glob(os.path.join(src_dir, "PERSONALSP_*.csv"))):
        anio = os.path.basename(path)[11:15]
        mes = latest_month(path)
        print(f"== {anio} (mes {mes}) {os.path.basename(path)}", flush=True)
        agg = aggregate(path, mes)
        res = resumen(agg, anio, mes, path)
        a, p, f_, v = res["activos"], res["pensiones"], res["formativa"], res["vacantes"]
        rows.append([anio, int(mes), a["registros"], a["masa_mensual"], a["costo_anual"], a["prom"],
                     p["registros"], p["masa_mensual"], p["costo_anual"], f_["registros"], f_["masa_mensual"],
                     v["plazas"], v["masa_mensual"], res["total_registros"], os.path.basename(path),
                     datetime.now(timezone.utc).isoformat(timespec="seconds")])
        print(f"  activos {a['registros']:,} masa {a['masa_mensual']/1e6:,.1f}M prom {a['prom']:,} | pensiones {p['registros']:,} | vacantes {v['plazas']:,}", flush=True)
        if res["otros_tipos_no_clasificados"]:
            print("  ADVERTENCIA tipos no clasificados:", res["otros_tipos_no_clasificados"], flush=True)
    dump_csv(os.path.join(DATA, "airhsp_headcount_anual.csv"),
             ["anio", "mes", "activos", "activos_masa_mensual", "activos_costo_anual", "activos_prom",
              "pensiones", "pensiones_masa_mensual", "pensiones_costo_anual", "formativa", "formativa_masa_mensual",
              "vacantes", "vacantes_masa_mensual", "total_registros", "archivo", "capturado_en"], rows)
    print(f"✔ data/airhsp_headcount_anual.csv: {len(rows)} años")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--serie", action="store_true", help="headcount anual con todos los PERSONALSP_*.csv del directorio")
    ap.add_argument("--src", default=SRC)
    ap.add_argument("--mes", default=os.environ.get("AIRHSP_MES"))
    a = ap.parse_args()
    if a.serie:
        serie(os.path.dirname(a.src))
        return
    mes = a.mes or latest_month(a.src)
    anio = os.path.basename(a.src)[11:15]
    print(f"Mes objetivo (snapshot): {anio}-{mes}")
    agg = aggregate(a.src, mes)
    write_snapshot(agg, anio, mes, a.src)


if __name__ == "__main__":
    main()
