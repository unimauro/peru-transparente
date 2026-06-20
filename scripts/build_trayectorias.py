"""Trayectorias de poder: personas que ocuparon cargos de MANDO en varias
instituciones del Estado a lo largo del tiempo (2015→2026).

Insumo: frontend/public/data/personas_red.json (personas multi-entidad, cada
aparición = [id_entidad, abrev, cargo, regimen, sueldo, año]).
Salida:  frontend/public/data/trayectorias_poder.json

Define "mando" con el MISMO clasificador del resto del sitio (build_site_data:
nivel ∈ CLAVE). Anti-overclaiming: describe movimientos de información pública;
NO imputa irregularidades. Que alguien rote por varias entidades puede ser
carrera técnica legítima u homonimia — se declara en el sitio.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "scripts")
from build_site_data import CLAVE, nivel  # noqa: E402

SRC = Path("frontend/public/data/personas_red.json")
OUT = Path("frontend/public/data/trayectorias_poder.json")

# Peso para estimar el "pico" de la carrera (nivel más alto alcanzado).
# Usa las MISMAS etiquetas que build_site_data.nivel() / CLAVE.
ORDEN = ["Ministro", "Viceministro", "Secretario General", "Presidente Ejecutivo",
         "Gerente General", "Director/a", "Gerente", "Jefe/a"]


def rank_nivel(n: str) -> int:
    return ORDEN.index(n) if n in ORDEN else len(ORDEN)


def main() -> None:
    data = json.loads(SRC.read_text())["items"]
    items = []
    for nombre, _n, aps in data:
        # aparición → (año, abrev, cargo, nivel) solo si es cargo de mando
        mando = []
        ent = set()
        for eid, abrev, cargo, reg, sueldo, anio in aps:
            niv = nivel(cargo or "")
            if niv in CLAVE:
                mando.append({"anio": anio, "abrev": abrev, "cargo": cargo[:60], "nivel": niv})
                ent.add(abrev)
        if len(ent) < 2:           # nos interesa el cruce entre instituciones
            continue
        mando.sort(key=lambda x: x["anio"])
        anios = [m["anio"] for m in mando]
        pico = min((m["nivel"] for m in mando), key=rank_nivel)
        items.append({
            "nombre": nombre,
            "n_inst": len(ent),            # instituciones DISTINTAS con cargo de mando
            "n_cargos": len(mando),
            "span": [anios[0], anios[-1]],
            "pico": pico,                  # nivel más alto alcanzado
            "trace": mando,
        })

    # Rankear: más instituciones, luego pico más alto, luego más cargos.
    items.sort(key=lambda x: (-x["n_inst"], rank_nivel(x["pico"]), -x["n_cargos"]))

    from collections import Counter
    ALTO = ("Ministro", "Viceministro", "Secretario General", "Presidente Ejecutivo")
    picos = Counter(x["pico"] for x in items)
    summary = {
        "total": len(items),                                   # con mando en ≥2 instituciones
        "alto": sum(1 for x in items if x["pico"] in ALTO),    # llegaron a la cúpula
        "ge3": sum(1 for x in items if x["n_inst"] >= 3),      # mando en 3+ instituciones
        "picos": dict(picos),
    }

    OUT.write_text(json.dumps({
        "summary": summary,
        "nota": "Movimientos de cargos de mando entre instituciones (datos públicos PTE 2015-2026). No implica irregularidad.",
        "items": items[:600],
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"✔ trayectorias_poder.json · {len(items)} personas con mando en ≥2 instituciones")
    print("  top por nº de instituciones:")
    for it in items[:5]:
        print(f"    {it['n_inst']} inst · pico {it['pico']:14} · {it['span'][0]}–{it['span'][1]} · {it['nombre']}")


if __name__ == "__main__":
    main()
