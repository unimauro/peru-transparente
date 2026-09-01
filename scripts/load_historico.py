"""Carga el histórico a Postgres (esquema `historico`) — pensado para el VPS.

Alimenta las tablas de db/postgres/04_historico.sql directamente desde los CSV con COPY
(vía tabla de staging UNLOGGED + INSERT..SELECT que normaliza y castea). Es la forma rápida
de subir cientos de MB.

  • planilla     : recarga completa (TRUNCATE + COPY) desde funcionarios_historico.csv y
                   funcionarios.csv (mismo esquema; el 2º aporta el mes vigente).
  • designaciones: upsert incremental por fuente_url (dispositivo único de El Peruano).

Conexión (en este orden): --database-url | $DATABASE_URL | $PT_DATABASE_URL | docker local.
El scheme 'postgresql+asyncpg://' (SQLAlchemy) se normaliza a 'postgresql://' para psycopg.

Uso:
  # verificar conteos/normalización SIN base de datos
  python scripts/load_historico.py --dry-run

  # aplicar esquema y cargar todo contra el VPS
  DATABASE_URL=postgresql://user:pass@api.tunky.net:5432/peru_transparente \\
    python scripts/load_historico.py --apply-schema --planilla --designaciones

  # solo el incremental diario de designaciones (lo que corre el pipeline)
  python scripts/load_historico.py --designaciones
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

HIST = Path("data/funcionarios_historico.csv")
FUN = Path("data/funcionarios.csv")
DESIG = Path("data/designaciones.csv")
SCHEMA_SQL = Path("db/postgres/04_historico.sql")
DEFAULT_URL = "postgresql://pt:pt@localhost:5432/peru_transparente"
CHUNK = 1 << 20  # 1 MiB por bloque de COPY

# columnas del CSV de planilla (funcionarios_historico.csv == funcionarios.csv)
PLANILLA_COLS = ["id_entidad", "entidad", "anio", "mes", "regimen", "apellidos_nombres",
                 "cargo", "dependencia", "remuneracion", "honorarios", "incentivo",
                 "aguinaldo", "otros", "total_ingreso_mensual", "fuente_url", "captured_at"]
DESIG_COLS = ["fecha", "entidad", "cargo", "nombre", "norma", "sumilla",
              "fuente_url", "captured_at"]


def na(s: str) -> str:
    """Igual que en los build_*.py: sin tildes, MAYÚSCULAS, espacios colapsados."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKD", s or "")
                  .encode("ascii", "ignore").decode().upper()).strip()


def db_url(cli: str | None) -> str:
    url = cli or os.environ.get("DATABASE_URL") or os.environ.get("PT_DATABASE_URL") or DEFAULT_URL
    return url.replace("postgresql+asyncpg://", "postgresql://").replace("+asyncpg", "")


def copy_csv(cur, sql: str, path: Path) -> None:
    """Streamea un CSV a un COPY FROM STDIN, quitando bytes NUL (líneas corruptas)."""
    with cur.copy(sql) as cp, path.open("rb") as fh:
        while chunk := fh.read(CHUNK):
            cp.write(chunk.replace(b"\x00", b""))


# ───────────────────────── dry-run (sin base de datos) ─────────────────────────
def contar(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("rb") as fh:
        return max(sum(chunk.count(b"\n") for chunk in iter(lambda: fh.read(CHUNK), b"")) - 1, 0)


def muestra(path: Path, col: str, n: int = 5) -> list[tuple[str, str]]:
    if not path.exists():
        return []
    out = []
    fh = path.open(encoding="utf-8", errors="ignore", newline="")
    for r in csv.DictReader(line.replace("\x00", "") for line in fh):
        v = r.get(col, "")
        if v:
            out.append((v, na(v)))
        if len(out) >= n:
            break
    return out


def dry_run() -> None:
    print("── dry-run (sin escribir en Postgres) ──")
    for etiqueta, path, col in [("planilla histórica", HIST, "apellidos_nombres"),
                                ("planilla vigente", FUN, "apellidos_nombres"),
                                ("designaciones", DESIG, "nombre")]:
        existe = "✔" if path.exists() else "✗ falta:"
        print(f"\n{etiqueta}: {existe} {path} · {contar(path):,} filas")
        for orig, norm in muestra(path, col):
            print(f"    {orig!r:45} → {norm!r}")
    print("\n(usa --apply-schema/--planilla/--designaciones para cargar de verdad)")


# ───────────────────────── carga real ─────────────────────────
def aplicar_esquema(cur) -> None:
    print("▶ aplicando esquema historico (04_historico.sql)…")
    cur.execute(SCHEMA_SQL.read_text(encoding="utf-8"))


def cargar_planilla(conn) -> None:
    if not HIST.exists() and not FUN.exists():
        print("  (sin CSV de planilla; se omite)")
        return
    t0 = time.monotonic()
    with conn.cursor() as cur:
        print("▶ planilla: recarga completa (TRUNCATE + COPY + normalización)…")
        cur.execute("TRUNCATE historico.planilla")
        cur.execute("DROP TABLE IF EXISTS historico._stg_planilla")
        cur.execute("CREATE UNLOGGED TABLE historico._stg_planilla ("
                    + ", ".join(f"{c} text" for c in PLANILLA_COLS) + ")")
        copy_sql = ("COPY historico._stg_planilla FROM STDIN "
                    "WITH (FORMAT csv, HEADER true)")
        for path in [p for p in (HIST, FUN) if p.exists()]:
            print(f"    COPY {path} ({path.stat().st_size / 1e6:.0f} MB)…", flush=True)
            copy_csv(cur, copy_sql, path)
        cur.execute("SELECT count(*) FROM historico._stg_planilla")
        leidas = cur.fetchone()[0]
        # numérico tolerante: deja NULL si viene vacío o no-numérico.
        num = lambda c: (f"NULLIF(regexp_replace({c}, '[^0-9.\\-]', '', 'g'), '')::numeric")  # noqa: E731
        cur.execute(f"""
            INSERT INTO historico.planilla
                (id_entidad, entidad, anio, mes, regimen, persona, persona_norm,
                 cargo, cargo_norm, dependencia, remuneracion, honorarios, incentivo,
                 aguinaldo, otros, total, fuente_url, captured_at)
            SELECT
                coalesce(id_entidad, ''),
                coalesce(entidad, ''),
                coalesce(NULLIF(regexp_replace(anio, '[^0-9]', '', 'g'), ''), '0')::smallint,
                coalesce(NULLIF(regexp_replace(mes,  '[^0-9]', '', 'g'), ''), '0')::smallint,
                coalesce(regimen, ''),
                coalesce(apellidos_nombres, ''),
                historico.norm(apellidos_nombres),
                coalesce(cargo, ''),
                historico.norm(cargo),
                coalesce(dependencia, ''),
                {num('remuneracion')}, {num('honorarios')}, {num('incentivo')},
                {num('aguinaldo')}, {num('otros')}, {num('total_ingreso_mensual')},
                NULLIF(fuente_url, ''),
                NULLIF(captured_at, '')::timestamptz
            FROM historico._stg_planilla
            WHERE coalesce(apellidos_nombres, '') <> ''
        """)
        cargadas = cur.rowcount
        cur.execute("DROP TABLE historico._stg_planilla")
        cur.execute("INSERT INTO historico.carga (fuente, archivo, filas_leidas, filas_carga, fin) "
                    "VALUES ('planilla', %s, %s, %s, now())",
                    (f"{HIST.name}+{FUN.name}", leidas, cargadas))
    conn.commit()
    print(f"  ✔ planilla: {cargadas:,} filas ({leidas:,} leídas) en {time.monotonic() - t0:.0f}s")


def cargar_designaciones(conn) -> None:
    if not DESIG.exists():
        print("  (sin data/designaciones.csv; se omite)")
        return
    t0 = time.monotonic()
    with conn.cursor() as cur:
        print("▶ designaciones: upsert incremental por fuente_url…")
        cur.execute("DROP TABLE IF EXISTS historico._stg_desig")
        cur.execute("CREATE UNLOGGED TABLE historico._stg_desig ("
                    + ", ".join(f"{c} text" for c in DESIG_COLS) + ")")
        copy_csv(cur, "COPY historico._stg_desig FROM STDIN WITH (FORMAT csv, HEADER true)", DESIG)
        cur.execute("SELECT count(*) FROM historico._stg_desig")
        leidas = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO historico.designacion
                (fecha, entidad, cargo, cargo_norm, nombre, nombre_norm,
                 norma, sumilla, fuente_url, captured_at)
            SELECT
                NULLIF(fecha, '')::date,
                coalesce(entidad, ''), coalesce(cargo, ''), historico.norm(cargo),
                coalesce(nombre, ''), historico.norm(nombre),
                coalesce(norma, ''), coalesce(sumilla, ''),
                NULLIF(fuente_url, ''), NULLIF(captured_at, '')::timestamptz
            FROM historico._stg_desig
            WHERE NULLIF(fuente_url, '') IS NOT NULL
            ON CONFLICT (fuente_url) DO UPDATE SET
                fecha = EXCLUDED.fecha, entidad = EXCLUDED.entidad,
                cargo = EXCLUDED.cargo, cargo_norm = EXCLUDED.cargo_norm,
                nombre = EXCLUDED.nombre, nombre_norm = EXCLUDED.nombre_norm,
                norma = EXCLUDED.norma, sumilla = EXCLUDED.sumilla,
                captured_at = EXCLUDED.captured_at
        """)
        cargadas = cur.rowcount
        cur.execute("DROP TABLE historico._stg_desig")
        cur.execute("INSERT INTO historico.carga (fuente, archivo, filas_leidas, filas_carga, fin) "
                    "VALUES ('designaciones', %s, %s, %s, now())",
                    (DESIG.name, leidas, cargadas))
    conn.commit()
    print(f"  ✔ designaciones: {cargadas:,} upsert ({leidas:,} leídas) en {time.monotonic() - t0:.0f}s")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--database-url", default=None)
    ap.add_argument("--apply-schema", action="store_true", help="ejecuta 04_historico.sql primero")
    ap.add_argument("--planilla", action="store_true", help="recarga la planilla histórica")
    ap.add_argument("--designaciones", action="store_true", help="upsert de designaciones")
    ap.add_argument("--dry-run", action="store_true", help="cuenta/normaliza sin tocar Postgres")
    args = ap.parse_args()

    if args.dry_run:
        dry_run()
        return

    if not (args.apply_schema or args.planilla or args.designaciones):
        print("nada que hacer: pasa --apply-schema, --planilla y/o --designaciones "
              "(o --dry-run). Ver --help.")
        sys.exit(2)

    try:
        import psycopg
    except ModuleNotFoundError:
        sys.exit("falta psycopg: pip install 'psycopg[binary]'")

    url = db_url(args.database_url)
    print(f"▶ conectando a {re.sub(r'://[^@]+@', '://***@', url)}")
    with psycopg.connect(url, autocommit=False) as conn:
        if args.apply_schema:
            with conn.cursor() as cur:
                aplicar_esquema(cur)
            conn.commit()
        if args.planilla:
            cargar_planilla(conn)
        if args.designaciones:
            cargar_designaciones(conn)
    print("✅ listo.")


if __name__ == "__main__":
    main()
