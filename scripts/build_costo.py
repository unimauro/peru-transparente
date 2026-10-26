#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera frontend/public/data/costo_estado.json: "¿Cuánto cuesta el Estado en personal?".

Entradas:
  - data/mef_personal_anual.csv             (scrapers/scrape_mef_personal.py --detalle; Consulta Amigable MEF)
  - data/airhsp_resumen.json                (scripts/procesar_airhsp.py; AIRHSP activos/pensiones/formativa/vacantes)
      fallback: frontend/public/data/airhsp.json
  - data/airhsp_headcount_anual.csv         (scripts/procesar_airhsp.py --serie; headcount 2017..2025)
  - data/funcionarios.csv                   (PTE, planilla nominal publicada por entidades)
  - frontend/public/data/ordenes_servicio.json (órdenes de servicio OCDS)
  - BCRPData PN38705PM  IPC Lima Metropolitana (índice Dic.2021=100, mensual) -> promedio anual, base 2025=100
  - BCRPData PM05920FA/PM05921FA/PM05922FA/PM05923FA  remuneraciones del gobierno general (% PBI), anual
  - INEI proy_01_3.xlsx población estimada y proyectada por año calendario (1980-2026)
  Las tres fuentes externas tienen copia estática capturada el 26-oct-2026 (--offline las fuerza).

Reglas: cada cifra con fuente y período; nunca se inventa un número (null si no hay dato);
números como int/float, nunca strings. Valida el JSON al final.

Uso: .venv/bin/python scripts/build_costo.py [--offline]
"""
import argparse
import csv
import io
import json
import os
import re
import sys
import zipfile
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MEF_CSV = os.path.join(ROOT, "data", "mef_personal_anual.csv")
AIRHSP_RESUMEN = os.path.join(ROOT, "data", "airhsp_resumen.json")
AIRHSP_JSON = os.path.join(ROOT, "frontend", "public", "data", "airhsp.json")
HEADCOUNT_CSV = os.path.join(ROOT, "data", "airhsp_headcount_anual.csv")
FUNC_CSV = os.path.join(ROOT, "data", "funcionarios.csv")
ORDENES_JSON = os.path.join(ROOT, "frontend", "public", "data", "ordenes_servicio.json")
OUT = os.path.join(ROOT, "frontend", "public", "data", "costo_estado.json")

BASE_ANIO = 2025
YEARS = list(range(2015, 2027))
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"
BCRP_API = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api/{code}/json/{ini}/{fin}"

# --- IPC: promedio anual del índice PN38705PM (Dic.2021=100), copia estática 26-oct-2026 (2026 = ene-sep)
IPC_CODE = "PN38705PM"
IPC_STATIC = {2015: 83.021, 2016: 86.004, 2017: 88.416, 2018: 89.58, 2019: 91.493, 2020: 93.165,
              2021: 96.872, 2022: 104.503, 2023: 111.049, 2024: 113.66, 2025: 115.366, 2026: 119.46}
IPC_STATIC_MESES_2026 = 9
INFL_DICDIC = {2015: 4.40, 2016: 3.23, 2017: 1.36, 2018: 2.19, 2019: 1.90, 2020: 1.97,
               2021: 6.43, 2022: 8.46, 2023: 3.24, 2024: 1.97, 2025: None}

# --- Remuneraciones del gobierno general (% PBI), BCRP; copia estática 26-oct-2026
PBI_CODES = {"remun_pct_pbi": "PM05920FA", "gn_pct_pbi": "PM05921FA", "gr_pct_pbi": "PM05922FA", "gl_pct_pbi": "PM05923FA"}
PBI_STATIC = {
    "remun_pct_pbi": {2015: 5.72, 2016: 5.82, 2017: 5.96, 2018: 6.11, 2019: 6.23, 2020: 7.23, 2021: 6.08, 2022: 5.83, 2023: 6.15, 2024: 6.13, 2025: 6.04},
    "gn_pct_pbi": {2015: 3.53, 2016: 3.57, 2017: 3.57, 2018: 3.56, 2019: 3.57, 2020: 4.08, 2021: 3.32, 2022: 3.25, 2023: 3.28, 2024: 3.23, 2025: 3.23},
    "gr_pct_pbi": {2015: 1.86, 2016: 1.93, 2017: 2.08, 2018: 2.23, 2019: 2.36, 2020: 2.81, 2021: 2.46, 2022: 2.27, 2023: 2.56, 2024: 2.59, 2025: 2.49},
    "gl_pct_pbi": {2015: 0.33, 2016: 0.32, 2017: 0.30, 2018: 0.31, 2019: 0.31, 2020: 0.34, 2021: 0.29, 2022: 0.31, 2023: 0.31, 2024: 0.32, 2025: 0.32},
}

# --- Población INEI (proyección al 30 de junio), copia estática 26-oct-2026
INEI_URL = "https://www.inei.gob.pe/media/MenuRecursivo/indices_tematicos/proy_01_3.xlsx"
INEI_NOMBRE = ("INEI, Población estimada y proyectada por sexo y tasa de crecimiento promedio anual, "
               "según año calendario, 1980-2026 (Estimaciones y Proyecciones de Población, al 30 de junio)")
POB_STATIC = {2015: 29964499, 2016: 30422831, 2017: 30973992, 2018: 31562130, 2019: 32131400,
              2020: 32625948, 2021: 33035304, 2022: 33396698, 2023: 33725844, 2024: 34038457,
              2025: 34350244, 2026: 34660114}

AIRHSP_DATASET = ("https://www.datosabiertos.gob.pe/dataset/"
                  "personal-activo-y-pensionista-del-sector-p%C3%BAblico-registrado-en-el-airhsp")
AIRHSP_DICC = "https://fs.datosabiertos.mef.gob.pe/datastorefiles/PersonalSP_Diccionario.csv"
CLASIFICADOR_2024 = ("https://cdn.www.gob.pe/uploads/document/file/5627853/"
                     "4986320-anexo-ii-clasificador-economico-de-gastos-para-el-ano-fiscal-2024.pdf")
CONSULTA_AMIGABLE = "https://apps5.mineco.gob.pe/transparencia/Navegador/Navegar.aspx?y={anio}&ap=ActProy"


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def fnum(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if x != x:  # NaN
        return None
    return int(x) if x.is_integer() else x


def bcrp(code, ini, fin):
    import httpx  # en el venv del repo
    r = httpx.get(BCRP_API.format(code=code, ini=ini, fin=fin), timeout=60, headers={"User-Agent": UA})
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------- IPC
def build_ipc(offline):
    raw, meses, fuente = None, {}, None
    if not offline:
        try:
            j = bcrp(IPC_CODE, "2014-1", "2026-12")
            title = j["config"]["title"]
            if "Lima Metropolitana" not in title or "ndice" not in title:
                raise RuntimeError(f"título inesperado: {title}")
            by = {}
            for p in j["periods"]:
                _, yr = p["name"].split(".")
                by.setdefault(int(yr), []).append(float(p["values"][0]))
            raw = {y: sum(v) / len(v) for y, v in by.items() if y in YEARS}
            meses = {y: len(v) for y, v in by.items() if y in YEARS}
            fuente = f"BCRPData {IPC_CODE} ({title}), promedio anual re-basado a {BASE_ANIO}=100"
        except Exception as e:  # noqa: BLE001
            log(f"IPC: API BCRP falló ({repr(e)[:100]}); uso copia estática")
    if raw is None:
        raw = dict(IPC_STATIC)
        meses = {y: 12 for y in raw}
        meses[2026] = IPC_STATIC_MESES_2026
        fuente = (f"BCRPData {IPC_CODE} (IPC Lima Metropolitana, índice Dic.2021=100), promedio anual "
                  f"re-basado a {BASE_ANIO}=100 (copia estática capturada 2026-10-26)")
    if not raw.get(BASE_ANIO):
        log("IPC: sin base 2025; encadeno inflación dic/dic (fallback estático)")
        idx, level = {}, 100.0
        for y in YEARS:
            if y == 2015:
                idx[y] = level
                continue
            inf = INFL_DICDIC.get(y)
            level = level * (1 + inf / 100) if inf is not None else None
            idx[y] = level
            if level is None:
                break
        base_y = max(y for y, v in idx.items() if v)
        out = {y: (round(idx[y] / idx[base_y] * 100, 4) if idx.get(y) else None) for y in YEARS}
        return out, "BCRP, inflación dic/dic (fallback estático)", f"base real {base_y}; 2025 sin dato"
    out = {y: (round(raw[y] / raw[BASE_ANIO] * 100, 4) if raw.get(y) else None) for y in YEARS}
    parciales = [f"{y} ({m} meses)" for y, m in meses.items() if m < 12]
    nota = "Promedio anual del índice mensual." + (" Parcial: " + ", ".join(parciales) + "." if parciales else "")
    return out, fuente, nota


# ---------------------------------------------------------------- Remuneraciones % PBI
def build_pbi(offline):
    series, fuente_nota = {}, []
    for key, code in PBI_CODES.items():
        vals = None
        if not offline:
            try:
                j = bcrp(code, "2015", "2025")
                name = j["config"]["series"][0]["name"]
                if "Remuneraciones" not in name:
                    raise RuntimeError(f"serie inesperada: {name}")
                vals = {int(p["name"]): round(float(p["values"][0]), 2) for p in j["periods"] if p["values"][0] not in ("n.d.", "")}
                fuente_nota.append(f"{key}={code} ({name})")
            except Exception as e:  # noqa: BLE001
                log(f"PBI {code}: API falló ({repr(e)[:80]}); copia estática")
        if vals is None:
            vals = dict(PBI_STATIC[key])
            fuente_nota.append(f"{key}={code} (copia estática 2026-10-26)")
        series[key] = vals
    serie = [{"anio": y, **{k: series[k].get(y) for k in PBI_CODES}} for y in range(2015, 2026)]
    return {"fuente": "BCRP, PM05920FA (gastos del gobierno general, % del PBI, gastos corrientes, remuneraciones)",
            "url": BCRP_API.format(code="PM05920FA", ini="2015", fin="2025"),
            "codigos": PBI_CODES, "nota": "; ".join(fuente_nota),
            "serie": serie}


# ---------------------------------------------------------------- Población
def poblacion_live():
    import httpx
    r = httpx.get(INEI_URL, timeout=60, headers={"User-Agent": UA}, follow_redirects=True)
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    ss = []
    if "xl/sharedStrings.xml" in z.namelist():
        x = z.read("xl/sharedStrings.xml").decode("utf-8")
        ss = [re.sub(r"<[^>]+>", "", m) for m in re.findall(r"<si>(.*?)</si>", x, re.S)]
    sh = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
    pob = {}
    for row in re.findall(r"<row[^>]*>(.*?)</row>", sh, re.S):
        cells = {}
        for col, attr, v in re.findall(r'<c r="([A-Z]+)\d+"([^>]*)>(?:<v>(.*?)</v>)?', row, re.S):
            if v:
                cells[col] = ss[int(v)] if 't="s"' in attr else v
        a, b = cells.get("A", ""), cells.get("B", "")
        if re.fullmatch(r"\d{4}", a.strip()) and re.fullmatch(r"\d+(\.0+)?", b.strip()):
            pob[int(a)] = int(float(b))
    if 2025 not in pob or not (30_000_000 < pob[2025] < 40_000_000):
        raise RuntimeError(f"población 2025 fuera de rango o ausente: {pob.get(2025)}")
    return {y: pob[y] for y in YEARS if y in pob}


def build_poblacion(offline):
    if not offline:
        try:
            return poblacion_live(), f"{INEI_NOMBRE}; {INEI_URL}"
        except Exception as e:  # noqa: BLE001
            log(f"Población: descarga INEI falló ({repr(e)[:100]}); uso copia estática")
    return dict(POB_STATIC), f"{INEI_NOMBRE}; {INEI_URL} (copia estática capturada 2026-10-26)"


# ---------------------------------------------------------------- MEF
def load_mef():
    if not os.path.exists(MEF_CSV):
        log(f"MEF: no existe {MEF_CSV}; serie vacía")
        return {}
    by = {}
    with open(MEF_CSV, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            y = int(r["anio"])
            d = by.setdefault(y, {})
            gen = r["generica"]
            if gen.startswith("2.1 "):
                key = "personal"
            elif gen.startswith("2.2 "):
                key = "pensiones"
            elif gen.startswith("2.3.2.8 "):
                key = "cas_23"
            elif gen.startswith("2.1.1.") and "CONTRATO ADMINISTRATIVO" in gen:
                key = "cas_21"
            elif gen.startswith("2.3.2.9 "):
                key = "locacion_23"
            elif gen.startswith("2.3.2.7 "):
                key = "servicios_prof_23"
            else:
                continue
            d[key] = {"pia": fnum(r["pia"]), "pim": fnum(r["pim"]), "devengado": fnum(r["devengado"]), "generica": gen}
            d["total_pim"] = fnum(r["total_pim_anio"])
            d["total_devengado"] = fnum(r["total_devengado_anio"])
            d["fuente_url"] = r["fuente_url"]
            d["capturado_en"] = r["capturado_en"]
    return by


def es_parcial(y, now):
    return y >= now.year or (y == now.year - 1 and now.month <= 3)


def build_serie(mef, ipc, pob, now):
    serie = []
    i_b = ipc.get(BASE_ANIO)

    def real(v, y):
        i_y = ipc.get(y)
        return round(v * i_b / i_y) if (v is not None and i_y and i_b) else None

    for y in YEARS:
        d = mef.get(y)
        if not d:
            serie.append({"anio": y, "personal_pia": None, "personal_pim": None, "personal_devengado": None,
                          "pensiones_pia": None, "pensiones_pim": None, "pensiones_devengado": None,
                          "total_pim": None, "total_devengado": None, "personal_real_2025": None,
                          "personal_per_capita": None, "personal_pct_total": None, "poblacion": pob.get(y),
                          "cas_23_devengado": None, "cas_21_devengado": None, "cas_devengado": None,
                          "locacion_23_devengado": None, "servicios_prof_23_devengado": None,
                          "personal_incl_cas": None, "personal_incl_cas_real_2025": None,
                          "personal_incl_cas_per_capita": None, "quiebre_cas": y == 2024,
                          "parcial": es_parcial(y, now), "sin_dato": True, "capturado_en": None, "fuente_url": None})
            continue
        p, q = d.get("personal", {}), d.get("pensiones", {})
        dev = p.get("devengado")
        hab = pob.get(y) or pob.get(BASE_ANIO)
        tot_dev = d.get("total_devengado")
        cas_23 = d.get("cas_23", {}).get("devengado")
        cas_21 = d.get("cas_21", {}).get("devengado")
        # Serie comparable: 2.1 + 2.3.2.8 hasta 2023; desde 2024 el CAS ya está dentro de 2.1 (2.1.1.13)
        if y <= 2023:
            incl = (dev + cas_23) if (dev is not None and cas_23 is not None) else None
        else:
            incl = dev
        serie.append({
            "anio": y,
            "personal_pia": p.get("pia"), "personal_pim": p.get("pim"), "personal_devengado": dev,
            "pensiones_pia": q.get("pia"), "pensiones_pim": q.get("pim"), "pensiones_devengado": q.get("devengado"),
            "total_pim": d.get("total_pim"), "total_devengado": tot_dev,
            "personal_real_2025": real(dev, y),
            "personal_per_capita": round(dev / hab, 2) if (dev is not None and hab) else None,
            "personal_pct_total": round(dev / tot_dev * 100, 2) if (dev is not None and tot_dev) else None,
            "poblacion": hab,
            "cas_23_devengado": cas_23, "cas_21_devengado": cas_21,
            "cas_devengado": cas_21 if cas_21 is not None else cas_23,
            "locacion_23_devengado": d.get("locacion_23", {}).get("devengado"),
            "servicios_prof_23_devengado": d.get("servicios_prof_23", {}).get("devengado"),
            "personal_incl_cas": incl, "personal_incl_cas_real_2025": real(incl, y),
            "personal_incl_cas_per_capita": round(incl / hab, 2) if (incl is not None and hab) else None,
            "quiebre_cas": y == 2024,
            "parcial": es_parcial(y, now),
            "capturado_en": d.get("capturado_en"), "fuente_url": d.get("fuente_url"),
        })
    return serie


# ---------------------------------------------------------------- Planilla mensual
def planilla_airhsp():
    src = AIRHSP_RESUMEN if os.path.exists(AIRHSP_RESUMEN) else AIRHSP_JSON
    j = json.load(open(src, encoding="utf-8"))
    act, pen, form, vac = j.get("activos") or {}, j.get("pensiones") or {}, j.get("formativa") or {}, j.get("vacantes") or {}
    nn = lambda d, k: fnum(d.get(k)) if d else None
    out = {
        "periodo": j.get("periodo"), "fuente": "AIRHSP — MEF (datos abiertos)", "url": AIRHSP_DATASET,
        "cobertura": j.get("cobertura") or "Gobierno Nacional y Regional; sin municipalidades, EsSalud, FONAFE, BCRP, SBS, SUNAT",
        "total_registros": fnum(j.get("total_registros") if j.get("total_registros") is not None else j.get("total")),
        "masa_mensual_todos_los_registros": fnum(j.get("masa_mensual_total") if j.get("masa_mensual_total") is not None else j.get("masa_mensual")),
        "activos": {
            "registros": nn(act, "registros"), "masa_mensual": nn(act, "masa_mensual"), "costo_anual": nn(act, "costo_anual"), "prom": nn(act, "prom"),
            "por_regimen": [{"regimen": r["regimen"], "n": fnum(r["n"]), "prom": fnum(r["prom"]), "masa": fnum(r["masa"])} for r in act.get("por_regimen", [])],
            "por_nivel": [{"nivel": r["nivel"], "n": fnum(r["n"]), "masa": fnum(r["masa"]), "prom": fnum(r["prom"])} for r in act.get("por_nivel", [])],
            "por_sector": [{"sector": r["sector"], "n": fnum(r["n"]), "masa": fnum(r["masa"]), "prom": fnum(r["prom"])} for r in act.get("por_sector", [])],
            "por_tipo_registro": [{"tipo": r["tipo"], "n": fnum(r["n"]), "masa": fnum(r["masa"]), "prom": fnum(r["prom"])} for r in act.get("por_tipo_registro", [])],
        },
        "pensiones": {
            "registros": nn(pen, "registros"), "masa_mensual": nn(pen, "masa_mensual"), "costo_anual": nn(pen, "costo_anual"), "prom": nn(pen, "prom"),
            "detalle": [{"tipo": r["tipo"], "n": fnum(r["n"]), "masa": fnum(r["masa"])} for r in pen.get("detalle", [])],
        },
        "formativa": {"registros": nn(form, "registros"), "masa_mensual": nn(form, "masa_mensual")},
        "vacantes": {"plazas": nn(vac, "plazas"), "masa_mensual": nn(vac, "masa_mensual")},
        # compatibilidad con el contrato v1
        "servidores": fnum(j.get("total_registros") if j.get("total_registros") is not None else j.get("total")),
        "masa_mensual": fnum(j.get("masa_mensual_total") if j.get("masa_mensual_total") is not None else j.get("masa_mensual")),
        "por_regimen": [{"regimen": r["regimen"], "n": fnum(r["n"]), "prom": fnum(r["prom"]), "masa": fnum(r.get("masa"))} for r in (j.get("activos") or {}).get("por_regimen", [])] or
                       [{"regimen": r["regimen"], "n": fnum(r["n"]), "prom": fnum(r["prom"]), "masa": fnum(r.get("masa"))} for r in j.get("por_regimen", [])],
        "nota": ("'total_registros' mezcla activos, pensionistas y sobrevivientes, modalidad formativa y plazas vacantes; "
                 "el headcount es 'activos.registros'. 'masa_mensual' = ingresos permanentes del mes (sin aguinaldos, "
                 "escolaridad ni aportes del empleador); 'costo_anual' = COSTO_TOTAL_ANUAL del AIRHSP, que sí los incluye."),
    }
    if not act:
        out["nota"] += " ATENCIÓN: airhsp_resumen.json ausente; faltan los cortes activos/pensiones (null)."
    return out


def load_headcount(ipc):
    if not os.path.exists(HEADCOUNT_CSV):
        log("Headcount: no existe data/airhsp_headcount_anual.csv")
        return []
    i_b = ipc.get(BASE_ANIO)
    out = []
    with open(HEADCOUNT_CSV, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            y = int(r["anio"])
            prom = fnum(r["activos_prom"])
            i_y = ipc.get(y)
            out.append({"anio": y, "mes": int(r["mes"]), "activos": fnum(r["activos"]),
                        "masa_mensual": fnum(r["activos_masa_mensual"]), "costo_anual": fnum(r["activos_costo_anual"]),
                        "prom": prom, "prom_real_2025": round(prom * i_b / i_y) if (prom and i_y and i_b) else None,
                        "pensiones": fnum(r["pensiones"]), "pensiones_masa_mensual": fnum(r["pensiones_masa_mensual"]),
                        "formativa": fnum(r["formativa"]), "vacantes": fnum(r["vacantes"]),
                        "total_registros": fnum(r["total_registros"]),
                        "nota": "mes 11 (el archivo 2020 no trae diciembre)" if int(r["mes"]) != 12 else None})
    out.sort(key=lambda x: x["anio"])
    return out


def planilla_pte():
    """Suma total_ingreso_mensual de data/funcionarios.csv (una fila por servidor; el mes publicado varía por entidad)."""
    base = {"fuente": "PTE, planilla nominal publicada por entidades", "url": "https://www.transparencia.gob.pe/"}
    if not os.path.exists(FUNC_CSV):
        return {**base, "periodo": None, "servidores_con_sueldo": None, "masa_mensual": None, "nota": "data/funcionarios.csv ausente"}
    csv.field_size_limit(10 ** 9)
    n = con = 0
    suma = 0.0
    meses = {}
    with open(FUNC_CSV, encoding="utf-8", errors="ignore") as fh:
        rd = csv.DictReader(line.replace("\x00", "") for line in fh)
        col = "total_ingreso_mensual" if "total_ingreso_mensual" in (rd.fieldnames or []) else "remuneracion"
        for r in rd:
            n += 1
            x = fnum((r.get(col) or "").strip())
            if x and x > 0:
                con += 1
                suma += x
                try:
                    k = f"{int(r.get('anio'))}-{int(r.get('mes')):02d}"
                except (TypeError, ValueError):
                    continue
                meses[k] = meses.get(k, 0) + 1
    MES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    def lab(k):
        y, m = k.split("-")
        return f"{MES[int(m) - 1]}-{y}"
    ks = sorted(meses)
    periodo = f"último mes publicado por entidad ({lab(ks[0])} a {lab(ks[-1])})" if ks else None
    top = sorted(meses.items(), key=lambda kv: -kv[1])[:3]
    return {**base, "periodo": periodo, "servidores_con_sueldo": con, "masa_mensual": round(suma),
            "servidores_publicados": n, "columna": col,
            "meses_mas_frecuentes": [{"mes": k, "n": v} for k, v in top],
            "nota": ("Suma del ingreso mensual de cada servidor en el último mes publicado por su entidad "
                     "(los meses difieren entre entidades). No incluye entidades sin publicar, docentes, FF.AA./PNP ni filas sin monto. "
                     "No es comparable entre años: depende de qué entidades publicaron y cuándo se barrió.")}


def planilla_locadores():
    j = json.load(open(ORDENES_JSON, encoding="utf-8"))
    per = j.get("periodo")
    desde = per[0] if isinstance(per, list) and per else None
    if isinstance(per, list):
        per = " a ".join(str(x) for x in per)
    n_ord = fnum(j.get("total_ordenes"))
    return {"ordenes": n_ord, "monto_total": fnum(j.get("monto_total")), "locadores": fnum(j.get("total_locadores")),
            "periodo": per,
            "cobertura": f"muestra OCDS, {int(n_ord) if n_ord else '?'} órdenes acumuladas desde {desde or '?'}; no es el universo",
            "nota": "monto total de órdenes de servicio OCDS; duración del contrato no informada",
            "fuente": "OECE/OCDS", "url": "https://www.gob.pe/oece"}


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="no consultar BCRP/INEI; usar copias estáticas")
    a = ap.parse_args()
    now = datetime.now(timezone.utc)
    ipc, ipc_fuente, ipc_nota = build_ipc(a.offline)
    pbi = build_pbi(a.offline)
    pob, pob_fuente = build_poblacion(a.offline)
    mef = load_mef()
    serie = build_serie(mef, ipc, pob, now)
    faltan = [y for y in YEARS if y not in mef]
    if faltan:
        log(f"MEF: años sin dato -> null: {faltan}")
    air = planilla_airhsp()
    headcount = load_headcount(ipc)

    m25 = mef.get(2025, {})
    conciliacion = {
        "airhsp_activos_anual": air["activos"]["costo_anual"],
        "airhsp_activos_masa_x12": (air["activos"]["masa_mensual"] * 12) if air["activos"]["masa_mensual"] else None,
        "mef_21_devengado_2025": m25.get("personal", {}).get("devengado"),
        "airhsp_pensiones_anual": air["pensiones"]["costo_anual"],
        "mef_22_devengado_2025": m25.get("pensiones", {}).get("devengado"),
        "nota": ("AIRHSP cubre GN+GR; MEF 2.1 incluye municipalidades; ambos excluyen FONAFE y EsSalud. "
                 "AIRHSP costo_anual = COSTO_TOTAL_ANUAL (con aguinaldos, escolaridad y aportes); MEF 2.1 = devengado del año. "
                 "MEF 2.2 incluye pensiones de regímenes que el AIRHSP no registra como planilla (p. ej. transferencias a la ONP)."),
    }

    out = {
        "generated_at": now.isoformat(timespec="seconds"),
        "planilla_mensual": {"airhsp": air, "pte": planilla_pte(), "locadores": planilla_locadores()},
        "headcount_airhsp": headcount,
        "pbi": pbi,
        "poblacion": {"anio": BASE_ANIO, "habitantes": pob.get(BASE_ANIO), "fuente": pob_fuente,
                      "serie": [{"anio": y, "habitantes": pob.get(y)} for y in YEARS]},
        "serie_mef": serie,
        "inflacion": {"base": BASE_ANIO, "indice": [{"anio": y, "ipc": ipc.get(y)} for y in YEARS],
                      "fuente": ipc_fuente, "nota": ipc_nota},
        "conciliacion": conciliacion,
        "notas_metodologicas": [
            "Serie MEF: genéricas 2.1 'Personal y obligaciones sociales' y 2.2 'Pensiones y otras prestaciones sociales', "
            "Consulta Amigable, nivel nacional (Gobierno Nacional + Regional + Local), Actividades + Proyectos, soles corrientes, "
            "devengado. 'total_*' = presupuesto público total del año (todas las genéricas). Consulta exacta: Navegar.aspx?y=AÑO&ap=ActProy "
            "→ botón 'Genérica' (y 'Sub-Genérica' → 'Sub-Genérica Detalle' para 2.3.2.7/2.3.2.8/2.3.2.9 y 2.1.1.13).",
            "Quiebre CAS 2024 (quiebre_cas=true): la Ley 31953 (Presupuesto 2024) y el Clasificador Económico de Gastos 2024 "
            "trasladaron el Contrato Administrativo de Servicios de 2.3 'Bienes y servicios' (específica 2.3.2.8) a 2.1 "
            "'Personal y obligaciones sociales' (2.1.1.13). En la Consulta Amigable, 2.3 devengado cae de S/ 50,4 mil M (2023) a "
            "S/ 39,0 mil M (2024) y 2.1 sube de S/ 58,9 a S/ 79,2 mil M; el CAS devengado fue S/ 13,1 mil M en 2023 y S/ 12,5 mil M en 2024. "
            "'personal_incl_cas' = 2.1 + 2.3.2.8 hasta 2023 y = 2.1 desde 2024: es la serie comparable.",
            "locacion_23_devengado = específica 2.3.2.9 'Locación de servicios realizados por persona natural' (honorarios de locadores, "
            "siguen en 2.3 todos los años); servicios_prof_23_devengado = 2.3.2.7 'Servicios profesionales y técnicos' (incluye empresas).",
            f"personal_real_2025 y personal_incl_cas_real_2025 = devengado × IPC_{BASE_ANIO} / IPC_año, con IPC = promedio anual del índice de "
            "Lima Metropolitana (BCRP PN38705PM); no existe IPC nacional mensual largo en BCRPData.",
            "personal_per_capita = devengado del año / población INEI del mismo año (proyección al 30 de junio). "
            "Una sola fuente de población en todo el JSON.",
            "parcial = true si el año es el actual (devengado acumulado a la fecha de captura, IPC de los meses publicados) "
            "o si es el año anterior y estamos en el primer trimestre (cierre contable aún en curso).",
            "AIRHSP (MEF, datos abiertos): un registro por plaza/pensión. 'total_registros' (2,72 M en dic-2025) mezcla activos, "
            "pensionistas y sobrevivientes, modalidad formativa y plazas VACANTES; el headcount de servidores activos es 'activos.registros'. "
            "Clasificación por DESC_TIPO_REGISTRO: activos = Activos + CAS + Convenio de Administración; pensiones = Pensionistas + "
            "Sobrevivientes + CPMP + Palmas Magisteriales + Reconocimientos Estatales; formativa = Modalidad Formativa + Promotoras; "
            "ESTADO_REGISTRO = VACANTE se cuenta aparte. Cobertura: Gobierno Nacional y Regional; sin municipalidades, EsSalud, FONAFE, BCRP, SBS ni SUNAT.",
            "masa_mensual (AIRHSP) = ING_IMPONIBLE_PERM_MENSUAL + ING_NO_IMPONIBLE_PERM_MENSUAL + INCENTIVO_UNICO_MENSUAL: ingreso permanente "
            "del mes, SIN aguinaldos, gratificaciones, escolaridad ni aportes del empleador. costo_anual = COSTO_TOTAL_ANUAL, que SÍ los incluye. "
            "Por eso costo_anual > masa_mensual × 12.",
            "headcount_airhsp: snapshot del último mes de cada archivo anual PERSONALSP_AAAA.csv (mes 12; 2020 solo llega a mes 11). "
            "Años sin archivo en disco no aparecen (no se interpolan).",
            "PTE: planilla nominal que publica cada entidad en el Portal de Transparencia Estándar; universo distinto al AIRHSP "
            "(sin docentes, FF.AA./PNP ni entidades que no publican) y no comparable entre años. No se suma con el AIRHSP.",
            "Locadores (OCDS): montos totales de órdenes de servicio de una muestra, no mensuales ni el universo.",
            "pbi: remuneraciones del gobierno general como % del PBI (BCRP, series anuales de finanzas públicas); gobierno general "
            "= GN + GR + GL (sin empresas públicas).",
        ],
        "fuentes": [
            {"nombre": "MEF, Consulta Amigable (Transparencia Económica)", "url": CONSULTA_AMIGABLE.format(anio=2025),
             "nota": "Gasto por genérica y específica, nivel nacional, 2015-2026; consulta Navegar.aspx?y=AÑO&ap=ActProy → Genérica → Sub-Genérica → Sub-Genérica Detalle; captura " + now.date().isoformat()},
            {"nombre": "MEF, AIRHSP — dataset 'Personal activo y pensionista del sector público registrado en el AIRHSP'", "url": AIRHSP_DATASET,
             "nota": "PERSONALSP_AAAA.csv (fs.datosabiertos.mef.gob.pe/datastorefiles/PERSONALSP_2025.csv); diccionario: " + AIRHSP_DICC},
            {"nombre": "Ley 31638, Ley de Presupuesto del Sector Público para el Año Fiscal 2023 (art. 9.4: registro en el AIRHSP como condición para el pago de planillas)",
             "url": "https://leyes.congreso.gob.pe/Documentos/2021_2026/ADLP/Texto_Consolidado/31638-TXM.pdf",
             "nota": "texto consolidado del Congreso (publicada en El Peruano el 6-dic-2022)"},
            {"nombre": "Ley 31953, Ley de Presupuesto del Sector Público para el Año Fiscal 2024",
             "url": "https://leyes.congreso.gob.pe/Documentos/2021_2026/ADLP/Texto_Consolidado/31953-TXM.pdf",
             "nota": "texto consolidado del Congreso; ejercicio desde el que el CAS se registra en la genérica 2.1 (ver Clasificador 2024)"},
            {"nombre": "MEF, Clasificador Económico de Gastos para el Año Fiscal 2024 (Anexo II)", "url": CLASIFICADOR_2024,
             "nota": "2.1.1.13 Contrato Administrativo de Servicios dentro de 2.1 Personal y obligaciones sociales"},
            {"nombre": "BCRPData PM05920FA (remuneraciones del gobierno general, % PBI)", "url": pbi["url"], "nota": pbi["nota"]},
            {"nombre": "BCRPData PN38705PM (IPC Lima Metropolitana, índice Dic.2021=100)", "url": BCRP_API.format(code=IPC_CODE, ini="2014-1", fin="2026-12"), "nota": ipc_fuente},
            {"nombre": "INEI, Estimaciones y Proyecciones de Población", "url": INEI_URL, "nota": pob_fuente},
            {"nombre": "Portal de Transparencia Estándar (PTE)", "url": "https://www.transparencia.gob.pe/", "nota": "Planilla nominal por entidad; ver data/funcionarios.csv"},
            {"nombre": "OECE / OCDS", "url": "https://www.gob.pe/oece", "nota": "Órdenes de servicio; ver frontend/public/data/ordenes_servicio.json"},
            {"nombre": "SERVIR, Características del Servicio Civil Peruano 2025 (cross-check)",
             "url": "https://elperuano.pe/noticia/302924-servir-politicas-de-gestion-del-servicio-civil-deben-construirse-sobre-evidencia",
             "nota": "1 618 940 servidores civiles en 2025 (GN 42,4 %, GR 43,5 %, GL 14,1 %) según nota de El Peruano sobre el estudio de SERVIR; "
                     "compara con 1 334 972 activos AIRHSP GN+GR: la diferencia son sobre todo los gobiernos locales, que el AIRHSP no cubre"},
            {"nombre": "INEI, Censos Nacionales 2025, resultados preliminares (cross-check de población)",
             "url": "https://andina.pe/agencia/noticia-poblacion-total-del-peru-se-eleva-a-34-millones-157-mil-732-habitantes-informa-inei-1077241.aspx",
             "nota": "34 157 732 habitantes (29-may-2026). NO se usa en los cálculos: todo el JSON usa la proyección INEI (34 350 244 en 2025, 0,6 % mayor) "
                     "porque es la única fuente con serie anual 2015-2026"},
        ],
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    chk = json.load(open(OUT, encoding="utf-8"))
    assert chk["serie_mef"][0]["anio"] == 2015 and len(chk["serie_mef"]) == len(YEARS)
    log(f"OK {OUT} ({os.path.getsize(OUT)} bytes); años MEF con dato: {sorted(mef)}")
    for s in chk["serie_mef"]:
        g = lambda k: (s.get(k) or 0) / 1e9
        log(f"  {s['anio']}: 2.1 {g('personal_devengado'):.2f} | incl.CAS {g('personal_incl_cas'):.2f} | real25 {g('personal_incl_cas_real_2025'):.2f} | "
            f"pens {g('pensiones_devengado'):.2f} | CAS {g('cas_devengado'):.2f} | loc {g('locacion_23_devengado'):.2f} | "
            f"pct {s['personal_pct_total']} | pc {s['personal_per_capita']}{' PARCIAL' if s['parcial'] else ''}")
    a = chk["planilla_mensual"]["airhsp"]["activos"]
    log(f"  AIRHSP activos {a['registros']} masa {a['masa_mensual']} costo_anual {a['costo_anual']} prom {a['prom']}; headcount años {[h['anio'] for h in chk['headcount_airhsp']]}")


if __name__ == "__main__":
    main()
