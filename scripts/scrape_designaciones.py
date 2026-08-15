"""Rastreo de DESIGNACIONES/NOMBRAMIENTOS publicados en El Peruano (Normas Legales).

Es la fuente REAL con *fecha de designación*: cada Resolución Suprema / Ministerial
/ de titular que nombra o designa a una persona en un cargo público se publica en el
Diario Oficial con fecha, entidad emisora y sumilla. Aquí se busca en el buscador
público (busquedas.elperuano.pe) los dispositivos cuyo tenor es "designa/nombra" y se
extrae: fecha, entidad, cargo, persona, número de norma y URL de la fuente.

Trazabilidad (principio #1): cada fila guarda `fuente_url` al dispositivo en El Peruano.
Anti-overclaiming (principio #2): solo se registra el hecho publicado (designación),
no se infiere nada más.

El buscador es HTML server-rendered (no hay API JSON estable), así que el parseo es
por heurística/regex y DEFENSIVO: si el sitio cambia su maquetado, baja el conteo y se
loguea, pero no rompe el pipeline. Igual que el scraper de OECE, conviene correrlo desde
una IP peruana residencial.

Resumable por página (data/designaciones.checkpoint.json). Append a data/designaciones.csv.
Uso:
  python scripts/scrape_designaciones.py --desde 21-07-2026 --max-minutes 20
  python scripts/scrape_designaciones.py --desde 21-07-2026 --hasta 15-08-2026
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import time
import unicodedata
from html import unescape
from pathlib import Path

import httpx

BASE = "https://busquedas.elperuano.pe/"
UA = "PeruTransparente/1.0 (+https://github.com/unimauro/peru-transparente)"
OUT = Path("data/designaciones.csv")
CKPT = Path("data/designaciones.checkpoint.json")
FIELDS = ["fecha", "entidad", "cargo", "nombre", "norma", "sumilla", "fuente_url", "captured_at"]

# Palabras que delatan un nombramiento/designación en la sumilla del dispositivo.
DESIGNA = re.compile(r"\b(design[aó]|nombr[aó]|encarg[aó]|ratific[aó])\b", re.I)
# Cargo típico tras el verbo: "designa a NN en el cargo de <CARGO>".
CARGO_RX = re.compile(r"cargo de ([^,.;]+?)(?:\s+de\s+la|\s+del|,|\.|;|$)", re.I)
# Nombre en mayúsculas (2+ palabras) tras "a/al señor(a)".
NOMBRE_RX = re.compile(r"(?:señor(?:a)?|se[ñn]ores?)\s+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ.\s]{6,60})", re.I)
# Enlaces a la ficha del dispositivo dentro del listado de resultados.
LINK_RX = re.compile(r'href="(/(?:dispositivo|download|cuadernillo)[^"]+)"', re.I)


def na(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKD", s or "")
                  .encode("ascii", "ignore").decode()).strip()


def strip_tags(s: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def parse_resultados(html: str, base_url: str) -> list[dict]:
    """Extrae dispositivos de designación del listado. Heurístico y tolerante."""
    filas: list[dict] = []
    # Cada resultado suele venir en un bloque; partimos por los enlaces a fichas.
    bloques = re.split(r'(?=href="/(?:dispositivo|download|cuadernillo))', html)
    for b in bloques:
        m = LINK_RX.search(b)
        if not m:
            continue
        texto = strip_tags(b)
        if not DESIGNA.search(texto):
            continue
        url = m.group(1)
        if url.startswith("/"):
            url = base_url.rstrip("/") + url
        fecha = ""
        mf = re.search(r"(\d{2})[./-](\d{2})[./-](\d{4})", texto)
        if mf:
            fecha = f"{mf.group(3)}-{mf.group(2)}-{mf.group(1)}"
        cargo = ""
        mc = CARGO_RX.search(texto)
        if mc:
            cargo = strip_tags(mc.group(1))[:80]
        nombre = ""
        mn = NOMBRE_RX.search(texto)
        if mn:
            nombre = na(mn.group(1)).title().strip()
        ent = ""
        me = re.search(r"(MINISTERIO[^,.;]+|GOBIERNO REGIONAL[^,.;]+|MUNICIPALIDAD[^,.;]+|"
                       r"ORGANISMO[^,.;]+|SUPERINTENDENCIA[^,.;]+|INSTITUTO[^,.;]+)", texto, re.I)
        if me:
            ent = strip_tags(me.group(1))[:80]
        norma = ""
        mnl = re.search(r"(RESOLUCI[ÓO]N[^,.;]{0,60}?N[°º.\s-]+[\d\-A-Z/]+)", texto, re.I)
        if mnl:
            norma = strip_tags(mnl.group(1))[:80]
        filas.append({
            "fecha": fecha, "entidad": ent, "cargo": cargo, "nombre": nombre,
            "norma": norma, "sumilla": texto[:240], "fuente_url": url,
        })
    return filas


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", default="21-07-2026", help="dd-mm-aaaa (por defecto 21-07-2026)")
    ap.add_argument("--hasta", default="", help="dd-mm-aaaa (por defecto hoy en el buscador)")
    ap.add_argument("--max-minutes", type=float, default=0)
    ap.add_argument("--max-pages", type=int, default=0)
    args = ap.parse_args()

    page = json.loads(CKPT.read_text())["page"] if CKPT.exists() else 1
    deadline = time.monotonic() + args.max_minutes * 60 if args.max_minutes else None
    cl = httpx.Client(timeout=60, headers={"User-Agent": UA}, follow_redirects=True)
    write_header = not OUT.exists() or OUT.stat().st_size == 0
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    seen: set = set()
    total = 0
    with OUT.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if write_header:
            w.writeheader()
        while True:
            if deadline and time.monotonic() > deadline:
                break
            if args.max_pages and page > args.max_pages:
                break
            params = {
                "palabras": "designa nombra encarga",
                "tipo_publicacion": "1",   # Normas Legales
                "fecha_desde": args.desde,
                "page": page,
            }
            if args.hasta:
                params["fecha_hasta"] = args.hasta
            try:
                r = cl.get(BASE, params=params)
                r.raise_for_status()
            except Exception as e:  # noqa: BLE001
                print(f"  aviso: fallo página {page} ({e}); reintento en 5s", flush=True)
                time.sleep(5)
                continue
            filas = parse_resultados(r.text, str(r.url))
            if not filas:
                # sin más designaciones (o cambió el maquetado): cerramos
                break
            nuevos = 0
            for f in filas:
                k = (f["fuente_url"], f["nombre"])
                if k in seen:
                    continue
                seen.add(k)
                f["captured_at"] = ts
                w.writerow(f)
                total += 1
                nuevos += 1
            if nuevos == 0:
                break
            if page % 10 == 0:
                CKPT.write_text(json.dumps({"page": page}))
                fh.flush()
                print(f"  página {page} · {total} designaciones acumuladas", flush=True)
            page += 1
    CKPT.write_text(json.dumps({"page": page}))
    cl.close()
    print(f"✔ {total} designaciones nuevas · próxima página {page}")
    if total == 0:
        print("  (0 filas: revisa el rango de fechas o el maquetado del buscador de El Peruano)")


if __name__ == "__main__":
    main()
