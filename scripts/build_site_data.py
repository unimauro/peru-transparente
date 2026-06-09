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

    # muestra para tabla (priorizar cargos clave)
    funcionarios.sort(key=lambda f: 0 if nivel(f.get("cargo", "")) in CLAVE else 1)
    sample = [
        {"entidad": f["entidad"], "nombre": f["apellidos_nombres"], "cargo": f["cargo"],
         "dependencia": f["dependencia"], "regimen": f["regimen"],
         "anio": f["anio"], "mes": f["mes"], "total": f["total_ingreso_mensual"],
         "url": f["fuente_url"], "nivel": nivel(f.get("cargo", ""))}
        for f in funcionarios[:2000]
    ]
    write("funcionarios_sample.json", {"items": sample})
    write("funcionarios_clave.json",
          {"items": [s for s in sample if s["nivel"] in CLAVE][:1000]})

    # Per-entidad: dependencias agrupadas (organigrama-lite) para entidades con datos.
    by_ent = defaultdict(list)
    for f in funcionarios:
        by_ent[f["id_entidad"]].append(f)
    ent_name = {e["id_entidad"]: e["nombre"] for e in entidades}
    ent_tipo = ent_cat
    (OUT / "entidad").mkdir(parents=True, exist_ok=True)
    for eid, fs in by_ent.items():
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
        (OUT / "entidad" / f"{eid}.json").write_text(json.dumps({
            "id": eid, "nombre": ent_name.get(eid, fs[0]["entidad"]),
            "tipo": ent_tipo.get(eid, ""), "periodo": period,
            "total": len(fs), "clave": sum(1 for f in fs if nivel(f.get("cargo", "")) in CLAVE),
            "dependencias": dep_list,
        }, ensure_ascii=False), encoding="utf-8")

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
