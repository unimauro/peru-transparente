"""Índice estático de personas para el buscador global (sin BD).

- personas/<LETRA>.json : shards por inicial del apellido (carga on-demand al buscar).
- personas_red.json     : personas en 2+ entidades (redes de poder) — destacado.

Cada persona: [nombre, n_entidades, [[id_entidad, entidad_abrev, cargo, regimen, sueldo, anio, mes, cod_regimen], ...]]
Con (id_entidad, anio, mes, cod_regimen) el frontend reconstruye la URL exacta del PTE de cada
aparición (patrón en _meta.patron_url), para que cada dato enlace su fuente (principio 1).
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from pii import enmascarar_pii, nombre_publicable  # noqa: E402

OUT = Path("frontend/public/data")


def na(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKD", s or "")
                  .encode("ascii", "ignore").decode().upper()).strip()


def ab(e: str) -> str:
    m = re.search(r"\(([^)]{2,12})\)\s*$", e)
    return m.group(1) if m else e[:24]


RE_REG = re.compile(r"ch_tipo_regimen=(\d+)")
PATRON_URL = ("https://www.transparencia.gob.pe/personal/pte_transparencia_personal.aspx?id_entidad={id_entidad}"
              "&in_anno_consulta={anio}&ch_mes_consulta={mes}&vc_nombre_funcionario=&vc_dni_funcionario="
              "&ch_tipo_regimen={cod_regimen}&id_tema=32&Ver=")
META = {"fuente": "Portal de Transparencia Estándar (PTE) · planilla nominal 2015-2026",
        "fuente_url": "https://www.transparencia.gob.pe/personal/pte_transparencia_personal.aspx",
        "patron_url": PATRON_URL,
        "aparicion": ["id_entidad", "abrev", "cargo", "regimen", "sueldo", "anio", "mes", "cod_regimen"],
        "datos_personales": "Nombre, cargo y remuneración tal como los publica el PTE; cada aparición reconstruye su URL. Rectificaciones: carlos@cardenas.pe"}


def rows(fn: str):
    """csv.DictReader tolerante a bytes NUL (líneas corruptas del scraping)."""
    fh = open(fn, encoding="utf-8", errors="ignore", newline="")
    return csv.DictReader(line.replace("\x00", "") for line in fh)


def main() -> None:
    pers: dict[str, list] = defaultdict(list)
    fuentes = ["data/funcionarios.csv"]
    if Path("data/funcionarios_historico.csv").exists():
        fuentes.append("data/funcionarios_historico.csv")
    vistos: set = set()  # dedup por (nombre, entidad, cargo, año)
    for fn in fuentes:
        for r in rows(fn):
            if not r.get("apellidos_nombres"):
                continue
            try:
                s = round(float(r["total_ingreso_mensual"]))
            except (TypeError, ValueError):
                s = 0
            nm = na(nombre_publicable(r["apellidos_nombres"]))
            anio = r.get("anio", "")
            cargo = enmascarar_pii(r["cargo"])[:38]
            k = (nm, r["id_entidad"], cargo, anio)
            if k in vistos:
                continue
            vistos.add(k)
            # aparición: [id_entidad, abrev, cargo, regimen, sueldo, año, mes, cod_regimen]
            mreg = RE_REG.search(r.get("fuente_url", "") or "")
            mes = (r.get("mes", "") or "").zfill(2)
            pers[nm].append([r["id_entidad"], ab(r["entidad"]), cargo, r["regimen"], s, anio,
                             mes, int(mreg.group(1)) if mreg else 0])

    shards: dict[str, list] = defaultdict(list)
    red: list = []
    for nombre, aps in pers.items():
        n_ent = len(set(a[0] for a in aps))
        rec = [nombre, n_ent, aps]
        letra = nombre[0] if nombre and nombre[0].isalpha() else "_"
        shards[letra].append(rec)
        if n_ent >= 2:
            red.append(rec)

    (OUT / "personas").mkdir(parents=True, exist_ok=True)
    for letra, recs in shards.items():
        recs.sort(key=lambda x: x[0])
        (OUT / "personas" / f"{letra}.json").write_text(
            json.dumps({"_meta": META, "items": recs}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # Vista por defecto liviana: solo el TOP por nº de entidades (el resto se encuentra
    # buscando por apellido, que carga el shard de esa letra). Antes se publicaba la lista
    # completa (48k personas ≈ 17 MB) y colgaba la página en móvil.
    red.sort(key=lambda x: -x[1])
    (OUT / "personas_red.json").write_text(
        json.dumps({"_meta": META, "total": len(red), "items": red[:500]},
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    print(f"✔ {len(pers):,} personas en {len(shards)} shards · {len(red):,} en 2+ entidades "
          f"(personas_red.json recortado a top 500)")


if __name__ == "__main__":
    main()
