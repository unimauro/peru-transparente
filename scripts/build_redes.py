"""Genera redes_entidades.json: grafo institucional con color por categoría
y los nombres de las personas compartidas por arista (la 'razón' del vínculo)."""
from __future__ import annotations

import csv
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from clasificacion import categoria  # noqa: E402


def main() -> None:
    red = json.loads(Path("frontend/public/data/personas_red.json").read_text())["items"]
    ent_nom = {e["id_entidad"]: e["nombre"] for e in csv.DictReader(open("data/entidades.csv", encoding="utf-8"))}

    pares = Counter()
    deg = Counter()
    edge_people: dict[tuple, list] = defaultdict(list)
    for nombre, n, aps in red:
        ents = sorted(set(a[0] for a in aps))
        persona = nombre.split(",")[0].title()
        for i in range(len(ents)):
            for j in range(i + 1, len(ents)):
                k = (ents[i], ents[j])
                pares[k] += 1
                deg[ents[i]] += 1
                deg[ents[j]] += 1
                if len(edge_people[k]) < 6:
                    edge_people[k].append(persona)

    top_ents = [e for e, _ in deg.most_common(80)]
    ts = set(top_ents)
    # solo conexiones fuertes (≥3 personas en común) para que el grafo sea legible
    MIN_W = 3
    edges = sorted(
        ({"a": a, "b": b, "w": w, "quienes": edge_people[(a, b)]}
         for (a, b), w in pares.items() if a in ts and b in ts and w >= MIN_W),
        key=lambda x: -x["w"],
    )[:400]
    # recalcular grado solo con aristas visibles (para el tamaño de nodo)
    vis_deg = Counter()
    for e in edges:
        vis_deg[e["a"]] += 1
        vis_deg[e["b"]] += 1
    nodes = [{"id": e, "label": ent_nom.get(e, e)[:28], "deg": vis_deg.get(e, 1),
              "cat": categoria(ent_nom.get(e, e))} for e in top_ents if vis_deg.get(e, 0) > 0]

    Path("frontend/public/data/redes_entidades.json").write_text(
        json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"✔ redes: {len(nodes)} entidades, {len(edges)} conexiones (con categoría + quiénes)")


if __name__ == "__main__":
    main()
