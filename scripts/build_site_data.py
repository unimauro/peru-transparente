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
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("frontend/public/data")
ENT = Path("data/entidades.csv")
FUN = Path("data/funcionarios.csv")

NIVELES = [
    ("Ministro/Titular", re.compile(r"\bMINISTR[OA]\b|PRESIDENTE EJECUTIV|\bTITULAR\b", re.I)),
    ("Viceministro", re.compile(r"VICE\s?MINISTR", re.I)),
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

    fun_por_entidad = Counter(f["id_entidad"] for f in funcionarios)
    niv_count = Counter(nivel(f.get("cargo", "")) for f in funcionarios)
    clave_total = sum(niv_count[k] for k in CLAVE)
    tipo_count = Counter(e["tipo_label"] for e in entidades)

    # catálogo enriquecido con nº de funcionarios scrapeados
    cat = [
        {
            "id": e["id_entidad"],
            "nombre": e["nombre"],
            "tipo": e["tipo_label"],
            "funcionarios": fun_por_entidad.get(e["id_entidad"], 0),
        }
        for e in entidades
    ]
    cat.sort(key=lambda x: (-x["funcionarios"], x["nombre"]))
    write("entidades.json", {"items": cat})

    write("national_kpis.json", {
        "total_entities": len(entidades),
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

    write("meta.json", {
        "entidades_catalogo": len(entidades),
        "entidades_con_datos": sum(1 for c in cat if c["funcionarios"]),
        "funcionarios_descargados": len(funcionarios),
        "cobertura_pct": round(100 * sum(1 for c in cat if c["funcionarios"]) / max(len(entidades), 1), 2),
        "actualizado": datetime.now(timezone.utc).isoformat(),
    })

    print(f"✔ JSON estático generado: {len(entidades)} entidades, {len(funcionarios)} funcionarios, "
          f"{clave_total} cargos clave.")


if __name__ == "__main__":
    main()
