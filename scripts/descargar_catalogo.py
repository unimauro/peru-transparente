"""Descarga el catálogo de entidades del Estado → data/entidades.csv.

Es el universo de instituciones públicas (incluye militares y empresas del Estado)
sobre el que se barre funcionarios. Úsalo con scrape_funcionarios.py --ids-file.
"""
from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scrapers"))
sys.path.insert(0, os.path.dirname(__file__))
from peru_transparente.connectors.pte_catalogo import fetch_catalogo  # noqa: E402
from clasificacion import categoria, prioridad  # noqa: E402


def main() -> None:
    out = Path("data/entidades.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    cat = fetch_catalogo()
    # categoría por nombre + orden de barrido (UNI → educación → salud → fiscalías → …)
    for r in cat:
        r["categoria"] = categoria(r["nombre"])
    cat.sort(key=lambda r: prioridad(r["nombre"]))
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id_entidad", "nombre", "categoria", "tipo_pod", "tipo_label"])
        w.writeheader()
        w.writerows(cat)
    print(f"✔ {len(cat)} entidades → {out}")
    from collections import Counter
    c = Counter(r["categoria"] for r in cat)
    for k, v in c.most_common():
        print(f"  {v:>5}  {k}")
    print("Primeras 5 (orden de barrido):", [r["nombre"][:30] for r in cat[:5]])


if __name__ == "__main__":
    main()
