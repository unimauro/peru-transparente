"""Genera los JSON estáticos que consume el frontend (estático-primero).

Lee el canónico de PostgreSQL y escribe a frontend/public/data/*.json:
  - national_kpis.json
  - entities.json + entities/<id>.json
  - officials/<id>.json

Pensado para ejecutarse al final de cada corrida del pipeline (GitHub Actions).
El resultado se commitea y dispara el redeploy de GitHub Pages.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg

OUT = Path(os.environ.get("PT_STATIC_OUT", "frontend/public/data"))
DSN = os.environ.get("PT_PG_DSN", "postgresql://pt:pt@localhost:5432/peru_transparente")


def write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, default=str, indent=2), encoding="utf-8")


def main() -> None:
    with psycopg.connect(DSN, row_factory=psycopg.rows.dict_row) as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM analytics.national_kpis")
        write(OUT / "national_kpis.json", cur.fetchone() or {})

        cur.execute(
            "SELECT e.id, e.name, e.acronym, e.level, s.name AS sector "
            "FROM core.entity e LEFT JOIN core.sector s ON s.id = e.sector_id "
            "WHERE e.is_current ORDER BY e.name"
        )
        entities = cur.fetchall()
        write(OUT / "entities.json", {"items": entities})

        for ent in entities:
            write(OUT / "entities" / f"{ent['id']}.json", ent)

    print(f"[build_static] {len(entities)} entidades exportadas a {OUT}")


if __name__ == "__main__":
    main()
