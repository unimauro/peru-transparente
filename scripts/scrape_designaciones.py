"""Rastreo de DESIGNACIONES/NOMBRAMIENTOS publicados en El Peruano (Normas Legales).

Es la fuente REAL con *fecha de designación*: cada Resolución Suprema / Ministerial /
Directoral que designa a alguien en un cargo público se publica en el Diario Oficial con
fecha, entidad y norma. Se consume la API JSON del buscador oficial:

    GET https://busquedas.elperuano.pe/api/v1/normas
        ?fechaIni=AAAAMMDD&fechaFin=AAAAMMDD&tipoPublicacion=NL&ci=ONLY&start=<offset>
    → { totalHits, start, hasNext, paginatedBy, hits:[{fechaPublicacion, sumilla,
        tipoDispositivo, numeroDispositivo, op, urlPDF, ...}] }

IMPORTANTE (verificado contra la fuente): la *sumilla* resume el CARGO y la ENTIDAD, pero
casi nunca trae el NOMBRE de la persona (ese dato vive solo en el PDF). Por eso se registra
el hecho publicado —cargo, entidad, fecha, norma y enlace al dispositivo— y el nombre queda
en blanco cuando la sumilla no lo expone. Trazabilidad (principio #1): cada fila guarda la
URL al dispositivo. Anti-overclaiming (principio #2): solo el hecho publicado.

Resumable por offset (data/designaciones.checkpoint.json). Reescribe data/designaciones.csv
(la ventana de fechas se re-consulta completa en cada corrida; se deduplica por `op`).
Uso:
  python scripts/scrape_designaciones.py --desde 2026-07-21
  python scripts/scrape_designaciones.py --desde 2026-07-21 --hasta 2026-08-16 --max-minutes 20
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import time
import unicodedata
from pathlib import Path

import httpx

API = "https://busquedas.elperuano.pe/api/v1/normas"
DISPOSITIVO = "https://busquedas.elperuano.pe/dispositivo/NL/{op}"
UA = "Mozilla/5.0 PeruTransparente/1.0 (+https://github.com/unimauro/peru-transparente)"
OUT = Path("data/designaciones.csv")
CKPT = Path("data/designaciones.checkpoint.json")
FIELDS = ["fecha", "entidad", "cargo", "nombre", "norma", "sumilla", "fuente_url", "captured_at"]

# Nombramientos (altas), excluyendo ceses/renuncias/viajes (que no son "nuevos").
INCLUYE = re.compile(r"\b(design[ao]n?|nombr[ao]n?|formaliz[ao]n?\s+.*designaci|encarg[ao]n?)\b", re.I)
EXCLUYE = re.compile(r"\b(termin|conclu|renuncia|cese|cesan|viaje|dejar?\s+sin\s+efecto|rectific)\w*", re.I)
# Cargo: "... en el cargo de <CARGO>" o "Designan <CARGO> de <ENTIDAD>".
CARGO_A = re.compile(r"cargo de\s+(.+?)(?:\s+de la\s+|\s+del\s+|\s+en la\s+|,|\.|$)", re.I)
CARGO_B = re.compile(r"^\s*(?:design[ao]n?|nombr[ao]n?|encarg[ao]n?)\s+(?:a\s+)?(.+?)(?:\s+de la\s+|\s+del\s+|\s+en\s+|,|\.|$)", re.I)
# Entidad: primer organismo público nombrado en la sumilla.
ENTIDAD = re.compile(r"(Ministerio[^,.;]+|Gobierno Regional[^,.;]+|Municipalidad[^,.;]+|"
                     r"Organismo[^,.;]+|Superintendencia[^,.;]+|Instituto[^,.;]+|"
                     r"Servicio Nacional[^,.;]+|Autoridad[^,.;]+|Programa[^,.;]+|"
                     r"Consejo[^,.;]+|Comisi[oó]n[^,.;]+|Universidad[^,.;]+)", re.I)
# Nombre (raro en la sumilla): "a don/doña/el señor NN".
NOMBRE = re.compile(r"\ba\s+(?:don|do[ñn]a|el se[ñn]or|la se[ñn]ora)\s+"
                    r"([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑñáéíóú.\s]{5,55}?)\s+(?:en|como|para|,)")


def limpiar(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def titlecase_nombre(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s or "")).strip().title()


def parse_hit(h: dict) -> dict | None:
    sumilla = limpiar(h.get("sumilla", ""))
    if not sumilla or not INCLUYE.search(sumilla) or EXCLUYE.search(sumilla):
        return None
    f = h.get("fechaPublicacion", "")
    fecha = f"{f[:4]}-{f[4:6]}-{f[6:8]}" if len(f) == 8 else ""
    cargo = ""
    mc = CARGO_A.search(sumilla) or CARGO_B.search(sumilla)
    if mc:
        cargo = limpiar(mc.group(1))[:90]
    ent = ""
    me = ENTIDAD.search(sumilla)
    if me:
        ent = limpiar(me.group(1))[:90]
    nombre = ""
    mn = NOMBRE.search(sumilla)
    if mn:
        nombre = titlecase_nombre(mn.group(1))
    tipo = limpiar(h.get("tipoDispositivo", ""))
    num = limpiar(str(h.get("numeroDispositivo") or ""))
    norma = f"{tipo} {num}".strip()[:80]
    op = h.get("op", "")
    return {
        "fecha": fecha, "entidad": ent, "cargo": cargo, "nombre": nombre,
        "norma": norma, "sumilla": sumilla[:240],
        "fuente_url": DISPOSITIVO.format(op=op) if op else "",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", default="2026-07-21", help="aaaa-mm-dd (por defecto 2026-07-21)")
    ap.add_argument("--hasta", default="", help="aaaa-mm-dd (por defecto hoy)")
    ap.add_argument("--max-minutes", type=float, default=0)
    args = ap.parse_args()

    fi = args.desde.replace("-", "")
    ff = (args.hasta or time.strftime("%Y-%m-%d")).replace("-", "")
    start = json.loads(CKPT.read_text()).get("start", 0) if CKPT.exists() else 0
    if start == 0 and OUT.exists():
        OUT.unlink()   # corrida desde el inicio → reescribe la ventana completa
    deadline = time.monotonic() + args.max_minutes * 60 if args.max_minutes else None
    cl = httpx.Client(timeout=30, headers={"User-Agent": UA}, follow_redirects=True)
    seen: set = set()
    total = kept = 0
    write_header = not OUT.exists() or OUT.stat().st_size == 0
    with OUT.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if write_header:
            w.writeheader()
        ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        completo = False
        while True:
            if deadline and time.monotonic() > deadline:
                break   # se cortó por tiempo: se guarda `start` para reanudar
            params = {"fechaIni": fi, "fechaFin": ff, "tipoPublicacion": "NL",
                      "ci": "ONLY", "start": start}
            try:
                d = cl.get(API, params=params).json()
            except Exception as e:  # noqa: BLE001
                print(f"  aviso: fallo start={start} ({e}); reintento en 5s", flush=True)
                time.sleep(5)
                continue
            hits = d.get("hits", [])
            if not hits:
                completo = True
                break
            for h in hits:
                total += 1
                op = h.get("op")
                if op in seen:
                    continue
                rec = parse_hit(h)
                if not rec:
                    continue
                seen.add(op)
                rec["captured_at"] = ts
                w.writerow(rec)
                kept += 1
            start += d.get("paginatedBy", 20)
            if (start // 20) % 20 == 0:
                CKPT.write_text(json.dumps({"start": start}))
                fh.flush()
                print(f"  offset {start} · {kept}/{total} designaciones (de {d.get('totalHits','?')} normas)", flush=True)
            if not d.get("hasNext"):
                completo = True
                break
    # solo al terminar la ventana se resetea a 0 (la próxima corrida la rehace completa);
    # si se cortó por tiempo, se conserva `start` para continuar donde quedó.
    CKPT.write_text(json.dumps({"start": 0 if completo else start}))
    cl.close()
    print(f"✔ {kept} designaciones de nombramiento · de {total} normas revisadas ({fi}→{ff})")
    if kept == 0:
        print("  (0: revisa el rango de fechas o si la API de El Peruano cambió)")


if __name__ == "__main__":
    main()
