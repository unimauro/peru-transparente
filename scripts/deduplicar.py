"""Elimina planillas duplicadas: ids del PTE que devuelven la MISMA data.

En el PTE, varios id_entidad "hijos" (gerencias regionales, cortes, programas)
devuelven la planilla completa del PADRE. Eso duplica decenas de miles de registros.

Estrategia: agrupar entidades por huella (set de nombre+cargo+ingreso+dependencia).
Si 2+ entidades comparten huella idéntica (y son ≥10 personas), se conserva UNA
(la de menor id_entidad ≈ la entidad "padre"/canónica) y se descartan las copias.
Se registra el mapeo en data/_planillas_compartidas.json para marcarlas en el sitio.

Reescribe data/funcionarios.csv in-place (idempotente).
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

FUN = Path("data/funcionarios.csv")
MAP = Path("data/_planillas_compartidas.json")
MIN_N = 10  # umbral: solo dedup grupos con ≥10 personas (evita coincidencias triviales)


def main() -> None:
    rows = list(csv.DictReader(FUN.open(encoding="utf-8")))
    fields = rows[0].keys() if rows else []
    by_ent: dict[str, list] = defaultdict(list)
    for r in rows:
        by_ent[r["id_entidad"]].append(r)

    def huella(rs: list) -> frozenset:
        return frozenset(
            (r["apellidos_nombres"], r["cargo"], r["total_ingreso_mensual"], r["dependencia"])
            for r in rs
        )

    fp_to_ids: dict[frozenset, list] = defaultdict(list)
    for eid, rs in by_ent.items():
        if len(rs) >= MIN_N:
            fp_to_ids[huella(rs)].append(eid)

    drop: set[str] = set()
    compartido: dict[str, str] = {}  # id descartado -> id conservado
    for ids in fp_to_ids.values():
        if len(ids) > 1:
            keep = min(ids, key=lambda x: int(x))
            for eid in ids:
                if eid != keep:
                    drop.add(eid)
                    compartido[eid] = keep

    out = [r for r in rows if r["id_entidad"] not in drop]
    with FUN.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(fields))
        w.writeheader()
        w.writerows(out)
    MAP.write_text(json.dumps(compartido))

    print(f"✔ Dedup: {len(rows):,} → {len(out):,} filas "
          f"(−{len(rows) - len(out):,}) · {len(drop)} entidades comparten planilla con su 'padre'")


if __name__ == "__main__":
    main()
