"""Carga el esquema normalizado core.* (que consume la API de cheka) desde los CSV.

Fase 1.5: entidad + persona + cargo (position) + designación (appointment), a partir de
data/entidades.csv y data/funcionarios.csv (foto 2026 = is_current). Contratos/proveedores
van en un paso aparte (load_core_contratos, si se agrega).

Conexión por PT_PG_DSN (túnel SSH al Postgres del VPS):
  export PT_PG_DSN="postgresql://cheka:<PGPASS>@localhost:5433/cheka"
Uso: .venv/bin/python scripts/load_core.py
"""
from __future__ import annotations

import csv
import os
import re
import sys
import unicodedata
import uuid
from pathlib import Path

import psycopg

DSN = os.environ.get("PT_PG_DSN")
if not DSN:
    sys.exit("Falta PT_PG_DSN (cadena de conexión al Postgres de cheka).")


def na(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKD", s or "")
                  .encode("ascii", "ignore").decode().upper()).strip()


def acron(name: str) -> str | None:
    m = re.search(r"\(([^)]{2,12})\)\s*$", name or "")
    return m.group(1) if m else None


def rows(fn: str):
    fh = open(fn, encoding="utf-8", errors="ignore", newline="")
    return csv.DictReader(line.replace("\x00", "") for line in fh)


def main() -> None:
    ent_uuid: dict[str, uuid.UUID] = {}
    ent_rows: list[tuple] = []          # (id, name, acronym)
    for r in rows("data/entidades.csv"):
        if not r.get("id_entidad"):
            continue
        eid = uuid.uuid4()
        ent_uuid[r["id_entidad"]] = eid
        ent_rows.append((eid, r["nombre"], acron(r["nombre"])))

    persons: dict[str, tuple[uuid.UUID, str]] = {}          # normname -> (id, full_name)
    positions: dict[tuple, tuple[uuid.UUID, str, str]] = {}  # (eid, normtitle) -> (id, title, regime)
    appts: list[tuple] = []
    n_src = 0
    for r in rows("data/funcionarios.csv"):
        nm = r.get("apellidos_nombres")
        if not nm:
            continue
        n_src += 1
        nn = na(nm)
        if nn not in persons:
            persons[nn] = (uuid.uuid4(), nm.strip())
        pid = persons[nn][0]

        ide = r.get("id_entidad") or "?"
        if ide not in ent_uuid:                     # entidad presente en planilla pero no en catálogo
            eid = uuid.uuid4()
            ent_uuid[ide] = eid
            ent_rows.append((eid, r.get("entidad") or "SIN NOMBRE", acron(r.get("entidad") or "")))
        eid = ent_uuid[ide]

        cargo = (r.get("cargo") or "SIN CARGO").strip()[:200] or "SIN CARGO"
        nt = na(cargo)
        pk = (eid, nt)
        if pk not in positions:
            positions[pk] = (uuid.uuid4(), cargo, (r.get("regimen") or "")[:60])
        posid = positions[pk][0]

        try:
            rem = round(float(r["total_ingreso_mensual"]), 2)
        except (TypeError, ValueError, KeyError):
            rem = None
        y = (r.get("anio") or "2026").strip() or "2026"
        try:
            m = int(r.get("mes") or 1)
        except ValueError:
            m = 1
        start = f"{y}-{max(1, min(12, m)):02d}-01"
        appts.append((uuid.uuid4(), pid, posid, eid, start, rem))

    print(f"· leído: {n_src:,} filas planilla → {len(persons):,} personas · "
          f"{len(positions):,} cargos · {len(ent_rows):,} entidades · {len(appts):,} designaciones",
          flush=True)

    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("TRUNCATE core.appointment, core.position, core.person, core.entity "
                    "RESTART IDENTITY CASCADE")
        with cur.copy("COPY core.entity (id,name,acronym,is_current) FROM STDIN") as cp:
            for e in ent_rows:
                cp.write_row([str(e[0]), e[1], e[2], True])
        with cur.copy("COPY core.person (id,full_name,normalized_name) FROM STDIN") as cp:
            for nn, (pid, fn) in persons.items():
                cp.write_row([str(pid), fn, nn])
        with cur.copy("COPY core.position (id,entity_id,title,normalized_title,regime) FROM STDIN") as cp:
            for (eid, nt), (posid, title, reg) in positions.items():
                cp.write_row([str(posid), str(eid), title, nt, reg or None])
        with cur.copy("COPY core.appointment "
                      "(id,person_id,position_id,entity_id,start_date,remuneration_amount,status,is_current) "
                      "FROM STDIN") as cp:
            for a in appts:
                cp.write_row([str(a[0]), str(a[1]), str(a[2]), str(a[3]), a[4], a[5], "vigente", True])
        conn.commit()

    print(f"✔ cargado a core.*: {len(ent_rows):,} entidades · {len(persons):,} personas · "
          f"{len(appts):,} designaciones vigentes", flush=True)


if __name__ == "__main__":
    main()
