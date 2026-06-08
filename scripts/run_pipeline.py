"""Orquestador mínimo del pipeline (extract → stage → promote).

Para producción esto vive como DAGs de Airflow (etl/dags/), pero este runner
permite ejecutar el flujo completo desde GitHub Actions o localmente sin Airflow.

Flujo:
  1. extract: corre el connector → IngestRecords
  2. stage:   upsert idempotente a staging.ingest (dedupe por sha256)
  3. promote: valida y promueve staging → core.* (+ provenance)

Las fases 'promote' por tipo de registro se implementan incrementalmente; aquí
se deja el esqueleto y la fase de staging totalmente funcional.
"""
from __future__ import annotations

import argparse
import os
import sys

import psycopg

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scrapers"))

from peru_transparente.connectors.fonafe import FonafeConnector  # noqa: E402
from peru_transparente.connectors.osce_ocds import OsceOcdsConnector  # noqa: E402

DSN = os.environ.get("PT_PG_DSN", "postgresql://pt:pt@localhost:5432/peru_transparente")

CONNECTORS = {
    "osce": lambda: OsceOcdsConnector(max_pages=int(os.environ.get("PT_OSCE_MAX_PAGES", "2"))),
    "fonafe": FonafeConnector,
}


def stage(records, conn) -> tuple[int, int]:
    """Inserta deltas en staging.ingest. Devuelve (nuevos, duplicados)."""
    new = dup = 0
    with conn.cursor() as cur:
        for r in records:
            cur.execute(
                """
                INSERT INTO staging.ingest
                    (source, record_type, natural_key, payload, source_url, captured_at, sha256)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source, record_type, sha256) DO NOTHING
                """,
                (r.source, r.record_type, r.natural_key,
                 psycopg.types.json.Json(r.payload), r.source_url, r.captured_at, r.sha256),
            )
            if cur.rowcount:
                new += 1
            else:
                dup += 1
    conn.commit()
    return new, dup


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="osce", choices=[*CONNECTORS, "all"])
    args = ap.parse_args()

    sources = list(CONNECTORS) if args.source == "all" else [args.source]
    with psycopg.connect(DSN) as conn:
        for name in sources:
            connector = CONNECTORS[name]()
            print(f"[pipeline] extract: {name}")
            new, dup = stage(connector.run(), conn)
            print(f"[pipeline] {name}: {new} nuevos, {dup} sin cambios")
            # registrar corrida
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO meta.scrape_run (source, finished_at, new_records, status) "
                    "VALUES (%s, now(), %s, 'ok')",
                    (connector.source, new),
                )
            conn.commit()
    print("[pipeline] TODO: promote staging→core (entity resolution + validación).")


if __name__ == "__main__":
    main()
