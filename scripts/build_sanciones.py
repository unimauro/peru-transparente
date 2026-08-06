"""Genera JSON estático del RNSSC + índice de cruce por nombre con la planilla.

Lee data/sanciones_rnssc.csv (dump del scraper) y produce en frontend/public/data/:
- sanciones.json          : resumen para una sección (totales por tipo, por sector,
                            top entidades sancionadoras, total de sanciones vigentes).
- sanciones_por_nombre.json : mapa {nombre_normalizado: [{tipo, entidad, causa,
                            fecha_fin, dni_masked}]} para que la ficha de persona
                            muestre la señal.

PRIVACIDAD: el DNI se enmascara a ***555 (solo últimos 3). NUNCA se publica completo.
ANTI-OVERCLAIMING: el cruce es por NOMBRE normalizado (mismo na() que build_personas),
así que es una COINCIDENCIA por homónimo posible, NO un hecho confirmado. El JSON lo
marca explícitamente (match_por_nombre / homonimo_posible) para que la UI lo advierta.
"""
from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

SRC = Path("data/sanciones_rnssc.csv")
OUT = Path("frontend/public/data")


def na(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKD", s or "")
                  .encode("ascii", "ignore").decode().upper()).strip()


def rows(path: Path):
    """csv.DictReader tolerante a bytes NUL (líneas corruptas del scraping)."""
    fh = path.open(encoding="utf-8", errors="ignore", newline="")
    return csv.DictReader(line.replace("\x00", "") for line in fh)


def mask_dni(dni: str) -> str:
    d = (dni or "").strip()
    return "***" + d[-3:] if len(d) >= 3 else "***"


def main() -> None:
    if not SRC.exists():
        print("aún no hay datos del RNSSC (corre scrapers/scrape_rnssc.py)")
        return

    por_tipo: Counter = Counter()
    por_sector: Counter = Counter()
    por_entidad: Counter = Counter()
    por_nombre: dict[str, list] = defaultdict(list)
    total = 0

    for r in rows(SRC):
        sid = r.get("sancion_id")
        if not sid:
            continue
        total += 1
        tipo = r.get("tipo_sancion", "") or "SIN CLASIFICAR"
        por_tipo[tipo] += 1
        por_sector[r.get("sector", "") or "SIN SECTOR"] += 1
        ent = r.get("entidad", "") or r.get("siglas", "")
        if ent:
            por_entidad[ent] += 1

        # Clave = na("AP_PATERNO AP_MATERNO, NOMBRES"), idéntica al formato
        # "apellidos_nombres" de la planilla (na() conserva la coma), para que el
        # índice de personas (build_personas.py) case por el mismo string.
        apellidos = " ".join(x for x in (r.get("ap_paterno"), r.get("ap_materno")) if x)
        nombre = na(f"{apellidos}, {r.get('nombres', '')}" if apellidos else r.get("nombres", ""))
        if nombre:
            por_nombre[nombre].append({
                "tipo": tipo,
                "entidad": ent,
                "causa": r.get("causa", ""),
                "fecha_fin": r.get("fecha_fin", ""),
                "dni_masked": mask_dni(r.get("dni", "")),
                "homonimo_posible": True,   # cruce por nombre, no por DNI verificado
            })

    OUT.mkdir(parents=True, exist_ok=True)

    resumen = {
        "fuente": "RNSSC - SERVIR (sanciones vigentes)",
        "advertencia": "Solo sanciones VIGENTES al momento del dump. El cruce con la planilla "
                       "es por nombre (homónimo posible), no un hecho confirmado.",
        "total_sanciones": total,
        "total_personas": len(por_nombre),
        "por_tipo": por_tipo.most_common(),
        "por_sector": por_sector.most_common(15),
        "top_entidades": por_entidad.most_common(30),
    }
    (OUT / "sanciones.json").write_text(
        json.dumps(resumen, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # Índice por nombre SHARDEADO por inicial (como personas/): la ficha y el buscador
    # cargan solo el shard de la letra consultada → carga liviana en móvil.
    shards: dict[str, dict] = defaultdict(dict)
    for nombre, ms in por_nombre.items():
        letra = nombre[0] if nombre and nombre[0].isalpha() else "_"
        shards[letra][nombre] = ms
    (OUT / "sanciones").mkdir(parents=True, exist_ok=True)
    meta = {"match": "por_nombre", "homonimo_posible": True,
            "nota": "Coincidencia por nombre normalizado; verificar identidad antes de afirmar."}
    for letra, idx in shards.items():
        (OUT / "sanciones" / f"{letra}.json").write_text(
            json.dumps({"_meta": meta, "index": idx}, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8")

    print(f"✔ {total} sanciones · {len(por_nombre)} nombres únicos · {len(por_tipo)} tipos "
          f"→ {OUT}/sanciones.json + {OUT}/sanciones/<LETRA>.json ({len(shards)} shards)")


if __name__ == "__main__":
    main()
