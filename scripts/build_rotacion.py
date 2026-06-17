"""Dashboard de Designaciones/Rotación: compara snapshots (2024 ↔ 2026).

Calcula por entidad: altas (entraron), bajas (salieron), permanecen y tasa de
rotación. Aparte, los CARGOS CLAVE (jefe ↑) que cambiaron — los nombramientos
y ceses de mando, que es lo que el roadmap llamaba "Dashboard de Designaciones".

Salida: frontend/public/data/rotacion.json
Comparación por nombre normalizado (anti-overclaiming: se declara en el sitio).
"""
from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "scripts")
from build_site_data import CLAVE, nivel  # noqa: E402

OUT = Path("frontend/public/data/rotacion.json")
MIN_BASE = 30  # solo entidades con ≥30 personas en 2024 para tasas estables


def na(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKD", s or "")
                  .encode("ascii", "ignore").decode().upper()).strip()


def main() -> None:
    now: dict[str, set] = defaultdict(set)
    now_clave: dict[str, dict] = defaultdict(dict)   # eid -> {nombre: cargo}
    ent_nom: dict[str, str] = {}
    for r in csv.DictReader(open("data/funcionarios.csv", encoding="utf-8")):
        eid = r["id_entidad"]
        nm = na(r["apellidos_nombres"])
        now[eid].add(nm)
        ent_nom[eid] = r["entidad"]
        if nivel(r.get("cargo", "")) in CLAVE:
            now_clave[eid][nm] = r["cargo"][:40]

    prev: dict[str, set] = defaultdict(set)
    prev_clave: dict[str, dict] = defaultdict(dict)
    for r in csv.DictReader(open("data/funcionarios_historico.csv", encoding="utf-8")):
        if r["anio"] != "2024":
            continue
        eid = r["id_entidad"]
        nm = na(r["apellidos_nombres"])
        prev[eid].add(nm)
        if nivel(r.get("cargo", "")) in CLAVE:
            prev_clave[eid][nm] = r["cargo"][:40]

    # excluir entidades cuya planilla 2026 fue deduplicada al "padre" (falso 100% de bajas)
    comp_path = Path("data/_planillas_compartidas.json")
    compartidas = set(json.loads(comp_path.read_text())) if comp_path.exists() else set()
    comunes = sorted((set(now) & set(prev)) - compartidas)
    tot_a = tot_b = tot_q = 0
    ents = []
    cambios_clave = []
    for e in comunes:
        altas = now[e] - prev[e]
        bajas = prev[e] - now[e]
        quedan = now[e] & prev[e]
        tot_a += len(altas); tot_b += len(bajas); tot_q += len(quedan)
        base = len(prev[e])
        if base >= MIN_BASE:
            ents.append({
                "id": e, "entidad": ent_nom[e][:48], "base_2024": base,
                "altas": len(altas), "bajas": len(bajas), "permanecen": len(quedan),
                "tasa": round(len(bajas) / base * 100, 1),
            })
        # cambios de mando: clave que entró / salió
        ck_in = [{"nombre": n.title(), "cargo": c} for n, c in now_clave[e].items() if n not in prev[e]][:6]
        ck_out = [{"nombre": n.title(), "cargo": c} for n, c in prev_clave[e].items() if n not in now[e]][:6]
        if ck_in or ck_out:
            cambios_clave.append({"id": e, "entidad": ent_nom[e][:44],
                                  "nombrados": ck_in, "cesados": ck_out,
                                  "n_in": len([n for n in now_clave[e] if n not in prev[e]]),
                                  "n_out": len([n for n in prev_clave[e] if n not in now[e]])})

    ents_rot = sorted(ents, key=lambda x: -x["tasa"])[:25]
    ents_est = sorted(ents, key=lambda x: x["tasa"])[:15]
    cambios_clave.sort(key=lambda x: -(x["n_in"] + x["n_out"]))

    OUT.write_text(json.dumps({
        "periodo": "dic 2024 → 2026",
        "entidades_comparables": len(comunes),
        "altas": tot_a, "bajas": tot_b, "permanecen": tot_q,
        "tasa_global": round(tot_b / (tot_b + tot_q) * 100, 1),
        "mas_rotacion": ents_rot,
        "mas_estables": ents_est,
        "cambios_mando": cambios_clave[:30],
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"✔ rotacion.json · {len(comunes)} entidades · tasa global {round(tot_b/(tot_b+tot_q)*100,1)}% · {len(cambios_clave)} con cambios de mando")


if __name__ == "__main__":
    main()
