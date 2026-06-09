"""Convierte los CSV (entidades + funcionarios) en JSON estático para el frontend.

Genera en frontend/public/data/:
  - national_kpis.json    KPIs reales (entidades, funcionarios, cargos clave…)
  - entidades.json        catálogo del Estado (2,300+), con conteo de funcionarios scrapeados
  - funcionarios_sample.json   muestra (primeras N) para la tabla
  - funcionarios_clave.json    cargos clave (alta dirección + jefaturas)
  - meta.json             cobertura/avance del scraping

Estático-primero: el sitio en GitHub Pages lee estos JSON sin backend.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from clasificacion import categoria  # noqa: E402

OUT = Path("frontend/public/data")
ENT = Path("data/entidades.csv")
FUN = Path("data/funcionarios.csv")

NIVELES = [
    # Viceministro ANTES que Ministro (para no contar "VICE MINISTRO" como ministro)
    ("Viceministro", re.compile(r"VICE\s?MINISTR", re.I)),
    ("Ministro", re.compile(r"\bMINISTR[OA]\b", re.I)),
    ("Presidente Ejecutivo", re.compile(r"PRESIDENTE\s+EJECUTIV|\bTITULAR\b", re.I)),
    ("Secretario General", re.compile(r"SECRETARI[OA] GENERAL", re.I)),
    ("Gerente General", re.compile(r"GERENTE GENERAL", re.I)),
    ("Director/a", re.compile(r"\bDIRECTOR(A|ES|AS)?\b|\bDIRECCI[ÓO]N\b", re.I)),
    ("Gerente", re.compile(r"\bGERENTE\b|\bGERENCIA\b", re.I)),
    ("Jefe/a", re.compile(r"\bJEFE\b|\bJEFA\b|\bJEFATURA\b", re.I)),
]
CLAVE = {n for n, _ in NIVELES}


def nivel(cargo: str) -> str:
    for name, rx in NIVELES:
        if rx.search(cargo or ""):
            return name
    return "Profesional/Apoyo"


def read_csv(p: Path) -> list[dict]:
    return list(csv.DictReader(p.open(encoding="utf-8"))) if p.exists() else []


def write(name: str, data: object) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    entidades = read_csv(ENT)
    funcionarios = read_csv(FUN)
    ckpt = Path("data/funcionarios.checkpoint.json")
    done = set(json.loads(ckpt.read_text()).get("done", [])) if ckpt.exists() else set()
    processed = len(done)

    fun_por_entidad = Counter(f["id_entidad"] for f in funcionarios)
    niv_count = Counter(nivel(f.get("cargo", "")) for f in funcionarios)
    clave_total = sum(niv_count[k] for k in CLAVE)
    ent_cat = {e["id_entidad"]: e.get("categoria") or categoria(e["nombre"]) for e in entidades}
    tipo_count = Counter(ent_cat[e["id_entidad"]] for e in entidades)

    # Autoridades de gob.pe (cargadas temprano para el conteo + página global)
    autoridades_por_ent = defaultdict(list)
    aut_path = Path("data/autoridades.csv")
    if aut_path.exists():
        for a in csv.DictReader(aut_path.open(encoding="utf-8")):
            autoridades_por_ent[a["id_entidad"]].append({
                "nombre": a["nombre"], "cargo": a["cargo"], "email": a["email"],
                "telefono": a["telefono"], "url": a["detalle_url"],
                "entidad": ent_cat.get(a["id_entidad"]) and a.get("institucion_pte"),
                "institucion": a.get("institucion_pte"),
            })
    aut_count = {k: len(v) for k, v in autoridades_por_ent.items()}
    # página global de autoridades (buscable)
    todas_aut = [
        {"nombre": a["nombre"], "cargo": a["cargo"], "email": a["email"],
         "telefono": a["telefono"], "url": a["url"], "institucion": a["institucion"], "id_entidad": eid}
        for eid, lst in autoridades_por_ent.items() for a in lst
    ]
    write("autoridades.json", {"items": todas_aut})

    # catálogo enriquecido con nº de funcionarios scrapeados
    def estado(eid: str, n: int) -> str:
        if n > 0:
            return "con_datos"
        return "sin_datos" if int(eid) in done else "pendiente"

    cat = [
        {
            "id": e["id_entidad"],
            "nombre": e["nombre"],
            "tipo": ent_cat[e["id_entidad"]],
            "funcionarios": fun_por_entidad.get(e["id_entidad"], 0),
            "autoridades": aut_count.get(e["id_entidad"], 0),
            "estado": estado(e["id_entidad"], fun_por_entidad.get(e["id_entidad"], 0)),
        }
        for e in entidades
    ]
    cat.sort(key=lambda x: (-x["funcionarios"], x["nombre"]))
    sin_datos = sum(1 for c in cat if c["estado"] == "sin_datos")
    pendientes = sum(1 for c in cat if c["estado"] == "pendiente")
    write("entidades.json", {"items": cat})

    write("national_kpis.json", {
        "total_entities": len(entidades),
        "entities_processed": processed,
        "entities_no_data": sin_datos,
        "entities_pending": pendientes,
        "entities_with_data": sum(1 for c in cat if c["funcionarios"]),
        "total_funcionarios": len(funcionarios),
        "total_cargos_clave": clave_total,
        "por_tipo": tipo_count.most_common(),
        "por_nivel": [[k, niv_count[k]] for k, _ in NIVELES if niv_count.get(k)],
        "_generated_at": datetime.now(timezone.utc).isoformat(),
    })

    # muestra para tabla: TODOS los cargos clave (para que los botones de nivel cuadren)
    # + una muestra de Profesional/Apoyo para el navegado general.
    def to_item(f: dict) -> dict:
        return {"entidad": f["entidad"], "nombre": f["apellidos_nombres"], "cargo": f["cargo"],
                "dependencia": f["dependencia"], "regimen": f["regimen"],
                "anio": f["anio"], "mes": f["mes"], "total": f["total_ingreso_mensual"],
                "url": f["fuente_url"], "nivel": nivel(f.get("cargo", ""))}

    clave_rows = [to_item(f) for f in funcionarios if nivel(f.get("cargo", "")) in CLAVE]
    otros = [to_item(f) for f in funcionarios if nivel(f.get("cargo", "")) not in CLAVE][:4000]
    sample = clave_rows + otros  # clave completos + muestra de apoyo
    write("funcionarios_sample.json", {"items": sample})
    write("funcionarios_clave.json", {"items": clave_rows})

    # Per-entidad: dependencias agrupadas (organigrama-lite) para entidades con datos.
    by_ent = defaultdict(list)
    for f in funcionarios:
        by_ent[f["id_entidad"]].append(f)
    ent_name = {e["id_entidad"]: e["nombre"] for e in entidades}
    ent_tipo = ent_cat
    (OUT / "entidad").mkdir(parents=True, exist_ok=True)
    # entidades con PTE o con autoridades de gob.pe
    for eid in set(by_ent) | set(autoridades_por_ent):
        fs = by_ent.get(eid, [])
        deps = defaultdict(list)
        for f in fs:
            deps[f["dependencia"] or "(Sin dependencia)"].append({
                "nombre": f["apellidos_nombres"], "cargo": f["cargo"],
                "nivel": nivel(f.get("cargo", "")), "regimen": f["regimen"],
                "total": f["total_ingreso_mensual"], "url": f["fuente_url"],
            })
        dep_list = sorted(
            ({"dependencia": d, "n": len(p),
              "clave": sum(1 for x in p if x["nivel"] in CLAVE),
              "personas": sorted(p, key=lambda x: 0 if x["nivel"] in CLAVE else 1)}
             for d, p in deps.items()),
            key=lambda x: (-x["clave"], -x["n"]),
        )
        period = f"{fs[0]['mes']}/{fs[0]['anio']}" if fs else ""
        regimenes = Counter(f["regimen"] for f in fs)
        # Cobertura parcial: si publica SOLO CAS (sin nombrados/docentes/altos funcionarios)
        es_uni_o_edu = ent_tipo.get(eid, "") in ("Universidad", "Educación")
        solo_cas = bool(fs) and set(regimenes) <= {"CAS"}
        nombre_ent = ent_name.get(eid) or (fs[0]["entidad"] if fs else "")
        (OUT / "entidad" / f"{eid}.json").write_text(json.dumps({
            "id": eid, "nombre": nombre_ent,
            "tipo": ent_tipo.get(eid, ""), "periodo": period,
            "total": len(fs), "clave": sum(1 for f in fs if nivel(f.get("cargo", "")) in CLAVE),
            "regimenes": regimenes.most_common(),
            "autoridades": autoridades_por_ent.get(eid, []),
            "cobertura_parcial": bool(solo_cas),
            "nota_cobertura": (
                "Esta entidad publica en el PTE solo su planilla CAS (administrativa). "
                "No figuran docentes nombrados ni autoridades (rector/vicerrectores), que van por el régimen universitario."
                if (solo_cas and es_uni_o_edu) else
                ("Esta entidad publica solo su planilla CAS; pueden faltar nombrados (276/728) y otros regímenes." if solo_cas else "")
            ),
            "dependencias": dep_list,
        }, ensure_ascii=False), encoding="utf-8")

    # ───── Distribución por región (mapa) ─────
    import unicodedata
    def _na(s: str) -> str:
        return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper()
    DEPTS = ["AMAZONAS", "ANCASH", "APURIMAC", "AREQUIPA", "AYACUCHO", "CAJAMARCA", "CALLAO",
             "CUSCO", "HUANCAVELICA", "HUANUCO", "ICA", "JUNIN", "LA LIBERTAD", "LAMBAYEQUE",
             "LIMA", "LORETO", "MADRE DE DIOS", "MOQUEGUA", "PASCO", "PIURA", "PUNO",
             "SAN MARTIN", "TACNA", "TUMBES", "UCAYALI"]
    def region(nombre: str) -> str:
        n = _na(nombre)
        if "CALLAO" in n:
            return "Callao"
        for d in DEPTS:
            if d == "CALLAO":
                continue
            if re.search(r"\b" + re.escape(d) + r"\b", n):
                return d.title().replace("La Libertad", "La Libertad").replace("San Martin", "San Martín")
        return "Nacional (Lima)"

    pay_por_ent: dict[str, float] = defaultdict(float)
    for f in funcionarios:
        try:
            pay_por_ent[f["id_entidad"]] += float(f.get("total_ingreso_mensual") or 0)
        except ValueError:
            pass
    reg_stats: dict[str, dict] = defaultdict(lambda: {"entidades": 0, "con_datos": 0, "personal": 0, "planilla_mensual": 0.0})
    for e in entidades:
        s = reg_stats[region(e["nombre"])]
        s["entidades"] += 1
        n = fun_por_entidad.get(e["id_entidad"], 0)
        if n:
            s["con_datos"] += 1
        s["personal"] += n
        s["planilla_mensual"] += round(pay_por_ent.get(e["id_entidad"], 0), 2)
    write("regiones.json", {
        "items": sorted(
            [{"region": k, **v, "planilla_mensual": round(v["planilla_mensual"], 0)} for k, v in reg_stats.items()],
            key=lambda x: -x["personal"],
        ),
        "_nota": "Planilla = suma de ingresos mensuales reportados (aproximado, no es el presupuesto total). Región inferida del nombre de la entidad.",
    })

    write("meta.json", {
        "entidades_catalogo": len(entidades),
        "entidades_procesadas": processed,
        "entidades_con_datos": sum(1 for c in cat if c["funcionarios"]),
        "funcionarios_descargados": len(funcionarios),
        "cobertura_pct": round(100 * processed / max(len(entidades), 1), 2),
        "actualizado": datetime.now(timezone.utc).isoformat(),
    })

    print(f"✔ JSON estático generado: {len(entidades)} entidades, {len(funcionarios)} funcionarios, "
          f"{clave_total} cargos clave.")


if __name__ == "__main__":
    main()
