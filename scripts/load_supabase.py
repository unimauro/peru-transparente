"""Carga los CSV (entidades + funcionarios + autoridades) a Supabase/Postgres.

Requiere la cadena de conexión en la variable de entorno PT_PG_DSN, p.ej.:
  export PT_PG_DSN="postgresql://postgres:[PASSWORD]@db.xxxx.supabase.co:5432/postgres"
(la obtienes en Supabase → Project Settings → Database → Connection string → URI)

Uso:
  python db/supabase/schema.sql  (ejecútalo primero en el SQL Editor de Supabase)
  python scripts/load_supabase.py
"""
from __future__ import annotations

import csv
import os
import re
import sys
import unicodedata
from pathlib import Path

import psycopg

DSN = os.environ.get("PT_PG_DSN")
if not DSN:
    sys.exit("Falta PT_PG_DSN (cadena de conexión de Supabase).")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKD", s or "")
                  .encode("ascii", "ignore").decode().upper()).strip()


def num(s: str):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def load_entidades(cur) -> None:
    rows = list(csv.DictReader(open("data/entidades.csv", encoding="utf-8")))
    # estado/funcionarios desde el JSON del sitio si existe
    import json
    cat = {}
    p = Path("frontend/public/data/entidades.json")
    if p.exists():
        for e in json.loads(p.read_text())["items"]:
            cat[e["id"]] = (e.get("estado"), e.get("funcionarios", 0))
    with cur.copy("COPY entidad (id_entidad,nombre,categoria,tipo_label,estado,funcionarios) FROM STDIN") as cp:
        for r in rows:
            est, nf = cat.get(r["id_entidad"], (None, 0))
            cp.write_row((r["id_entidad"], r["nombre"], r.get("categoria"), r.get("tipo_label"), est, nf))
    print(f"  entidad: {len(rows)}")


def load_funcionarios(cur) -> None:
    from build_site_data import nivel  # reutiliza la clasificación
    n = 0
    with cur.copy("COPY funcionario (id_entidad,entidad,apellidos_nombres,nombre_norm,cargo,dependencia,"
                  "nivel,regimen,anio,mes,remuneracion,otros,total_ingreso_mensual,fuente_url,captured_at) FROM STDIN") as cp:
        for r in csv.DictReader(open("data/funcionarios.csv", encoding="utf-8")):
            cp.write_row((
                r["id_entidad"], r["entidad"], r["apellidos_nombres"], norm(r["apellidos_nombres"]),
                r["cargo"], r["dependencia"], nivel(r.get("cargo", "")), r["regimen"],
                int(r["anio"]) if r["anio"] else None, int(r["mes"]) if r["mes"] else None,
                num(r.get("remuneracion")), num(r.get("otros")), num(r["total_ingreso_mensual"]),
                r["fuente_url"], r["captured_at"],
            ))
            n += 1
    print(f"  funcionario: {n}")


def load_autoridades(cur) -> None:
    p = Path("data/autoridades.csv")
    if not p.exists():
        return
    n = 0
    with cur.copy("COPY autoridad (id_entidad,institucion,nombre,nombre_norm,cargo,email,telefono,detalle_url) FROM STDIN") as cp:
        for r in csv.DictReader(p.open(encoding="utf-8")):
            cp.write_row((r["id_entidad"], r["institucion_pte"], r["nombre"], norm(r["nombre"]),
                          r["cargo"], r["email"], r["telefono"], r["detalle_url"]))
            n += 1
    print(f"  autoridad: {n}")


def main() -> None:
    sys.path.insert(0, os.path.dirname(__file__))
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        print("Truncando e insertando…")
        cur.execute("TRUNCATE funcionario, autoridad, entidad RESTART IDENTITY CASCADE")
        load_entidades(cur)
        load_funcionarios(cur)
        load_autoridades(cur)
        conn.commit()
    print("✔ Carga completa. Prueba: select * from buscar_persona('sanchez ferrer');")


if __name__ == "__main__":
    main()
