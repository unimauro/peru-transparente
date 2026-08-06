"""Descarga el dataset abierto de Declaraciones Juradas de INTERESES (Ley 31227) de la CGR.

Fuente: Plataforma Nacional de Datos Abiertos (CKAN). Es un ARCHIVO JSON público
(~34 MB) con el listado de declaraciones de intereses presentadas ante la Contraloría.
No requiere captcha ni cookies; solo un User-Agent de navegador (el CDN responde 418 a
clientes "no navegador"). Cobertura: instantánea inicial del sistema (jul–dic 2022),
cuando entró en vigor la Ley 31227 — NO es histórico completo. Sin número de DNI (solo
tipo de documento), por eso el cruce con la planilla es por NOMBRE.

Uso: python scrapers/download_dj_intereses.py
Salida: data/dj_intereses.csv (apellidos, nombres, entidad, cargo, fechas, codigo).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import httpx

URL = "https://www.datosabiertos.gob.pe/sites/default/files/DJIC_FUNCIONARIOS_21122022.json"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
OUT = Path("data/dj_intereses.csv")
FIELDS = ["codigo", "ap_paterno", "ap_materno", "nombres", "entidad", "cargo",
          "fecha_presentacion", "fecha_inicio_cargo", "fecha_fin_cargo"]


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=180, headers={"User-Agent": UA}, follow_redirects=True) as cl:
        r = cl.get(URL)
        r.raise_for_status()
        data = r.json()
    n = 0
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for d in data:
            w.writerow({
                "codigo": d.get("CODIGO_DDJJ", ""),
                "ap_paterno": d.get("APELLIDO_PATERNO", ""),
                "ap_materno": d.get("APELLIDO_MATERNO", ""),
                "nombres": d.get("NOMBRES", ""),
                "entidad": d.get("ENTIDAD", ""),
                "cargo": d.get("CARGO", ""),
                "fecha_presentacion": (d.get("FECHA_PRESENTACION_DDJJ", "") or "")[:10],
                "fecha_inicio_cargo": (d.get("FECHA_INICIO_CARGO", "") or "")[:10],
                "fecha_fin_cargo": (d.get("FECHA_FIN_CARGO", "") or "")[:10],
            })
            n += 1
    print(f"✔ {n:,} declaraciones de intereses → {OUT}")


if __name__ == "__main__":
    main()
