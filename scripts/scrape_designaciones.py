"""Rastreo de DESIGNACIONES/NOMBRAMIENTOS publicados en El Peruano (Normas Legales).

Es la fuente REAL con *fecha de designación*: cada Resolución Suprema / Ministerial /
Directoral que designa a alguien en un cargo público se publica en el Diario Oficial con
fecha, entidad y norma. Se consume la API JSON del buscador oficial:

    GET https://busquedas.elperuano.pe/api/v1/normas
        ?fechaIni=AAAAMMDD&fechaFin=AAAAMMDD&tipoPublicacion=NL&ci=ONLY&start=<offset>
    → { totalHits, start, hasNext, paginatedBy, hits:[{fechaPublicacion, sumilla,
        tipoDispositivo, numeroDispositivo, op, urlPDF, ...}] }

La *sumilla* resume el CARGO y la ENTIDAD pero casi nunca trae el NOMBRE. El nombre, la fecha
real de la norma y los suplentes están en la página del dispositivo
(busquedas.elperuano.pe/dispositivo/NL/<op>, HTML con el texto completo). Por eso, para las
normas de los últimos DETALLE_DIAS días, se descarga esa página (delay ≥ 1 s, cache en
data/peruano_cache/<op>.html, no versionada) y se extrae:
  - nombre(s): "Designar/Nombrar … a la señora NOMBRE APELLIDOS en el cargo de…"
    (una fila por persona; `rol` = titular | suplente cuando la misma norma trae ambos);
  - fecha_norma: "Lima, 4 de agosto de 2026" (la columna `fecha` sigue siendo la de publicación);
  - cargo: desde el verbo de la sumilla hasta la entidad (sin truncar en "del/de la").
Trazabilidad (principio #1): cada fila guarda la URL al dispositivo. Anti-overclaiming
(principio #2): solo el hecho publicado; si el texto no expone el nombre, queda en blanco.

Resumable por offset (data/designaciones.checkpoint.json). Reescribe data/designaciones.csv
(la ventana de fechas se re-consulta completa en cada corrida; se deduplica por `op`).
Uso:
  python scripts/scrape_designaciones.py --desde 2026-07-21
  python scripts/scrape_designaciones.py --desde 2026-07-21 --hasta 2026-08-16 --max-minutes 20
  python scripts/scrape_designaciones.py --probar 10        # extrae 10 normas del CSV y las muestra
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import html as htmlmod
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
CACHE = Path("data/peruano_cache")
FIELDS = ["fecha", "entidad", "cargo", "nombre", "norma", "sumilla", "fuente_url", "captured_at",
          "fecha_norma", "rol"]
DETALLE_DIAS = 90          # solo se descarga el dispositivo de normas de los últimos N días
DETALLE_DELAY = 1.0        # s entre descargas de dispositivos (cortesía)

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


# ───────────── detalle del dispositivo (texto completo de la norma) ─────────────
MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
         "agosto": 8, "setiembre": 9, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
# "Lima, 4 de agosto de 2026" / "La Victoria, 27 de agosto del 2026" / "Jesús María, 11 de setiembre del 2026"
RE_FECHA_NORMA = re.compile(r"\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){0,2}),\s+(\d{1,2}) de (\w+) de(?:l)? (\d{4})")
# "Designar al señor NOMBRE en el cargo de…" / "Nombrar a la abogada NOMBRE, como…"
RE_NOMBRE = re.compile(
    r"(?:DESIGNAR|Designar|NOMBRAR|Nombrar|ENCARGAR|Encargar|RATIFICAR|Ratificar)"
    r"(?:,?\s+(?:temporalmente|a partir de[^,]{0,40},|con eficacia[^,]{0,40},|como\s+\w+(?:\s+\w+){0,3}))?,?\s+"
    r"(?:a\s+)?(?:la\s+|al\s+|el\s+|los\s+|don\s+|do[ñn]a\s+)?"
    r"(?:se[ñn]ora?|abogad[oa]|doctora?|ingenier[oa]|licenciad[oa]|economista|mag[ií]ster|"
    r"contador[a]?|arquitect[oa]|m[eé]dic[oa]|general|coronel|capit[aá]n|almirante|"
    r"profesora?|bachiller|Sr\.|Sra\.|Dr\.|Dra\.|Ing\.|Abog\.|Lic\.)?\s*"
    r"([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ' ]{6,80}?)"
    r"(?:,|\s+en el cargo|\s+en el puesto|\s+como|\s+para|\s+en la plaza|\s+a partir|\s*\(|\s+identificad[oa])"
)
# Listas "1. NOMBRES APELLIDOS 12345678 DISTRITO…" (p. ej. subprefectos): nombre seguido de DNI.
# El DNI NO se guarda (solo sirve de delimitador).
RE_LISTA = re.compile(r"(?<!\d)\d{1,3}\.\s+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ' ]{8,70}?)\s+\d{8}(?!\d)")
RE_RESUELVE = re.compile(r"SE RESUELVE|RESUELVE:|DECRETA:|ACUERDA:", re.I)
PALABRAS_NO_NOMBRE = re.compile(r"\b(cargo|funciones|confianza|servidor|directorio|miembro|comisi[oó]n|"
                                r"responsable|representante|titular|suplente|coordinador|gerente|"
                                r"director|jefe|asesor|secretari[oa]|encargad|vocal|presidente|"
                                r"oficina|unidad|gerencia|despacho|direcci[oó]n|programa|ministerio|"
                                r"municipal|general|comit[eé]|consejo|organismo|instituto|"
                                r"superintendencia|autoridad|procuradur|fiscal[ií]a|gobierno|"
                                r"regional|nacional|entidad|empresa|sociedad)\b", re.I)


def texto_html(raw: str) -> str:
    """Texto plano de la página del dispositivo (sin scripts/estilos/etiquetas)."""
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return limpiar(htmlmod.unescape(t))


def extraer_detalle(texto: str) -> dict:
    """{'nombres': [(nombre, rol), …], 'fecha_norma': 'aaaa-mm-dd'} desde el texto de la norma."""
    fecha_norma = ""
    m = RE_FECHA_NORMA.search(texto)
    if m and m.group(3).lower() in MESES:
        try:
            fecha_norma = dt.date(int(m.group(4)), MESES[m.group(3).lower()], int(m.group(2))).isoformat()
        except ValueError:
            fecha_norma = ""
    # parte resolutiva (si existe); si no, todo el texto
    mr = RE_RESUELVE.search(texto)
    cuerpo = texto[mr.start():] if mr else texto
    nombres: list[tuple[str, str]] = []
    for mn in RE_NOMBRE.finditer(cuerpo):
        nombre = limpiar(mn.group(1))
        # un nombre real: 2-6 palabras, sin vocabulario de cargos
        palabras = nombre.split()
        if not (2 <= len(palabras) <= 7) or PALABRAS_NO_NOMBRE.search(nombre):
            continue
        if sum(1 for p in palabras if p[:1].isupper()) < len(palabras) - 1:
            continue
        contexto = cuerpo[max(0, mn.start() - 80): mn.end() + 60].lower()
        rol = "suplente" if re.search(r"suplente|alterno", contexto) else "titular"
        nombre = titlecase_nombre(nombre)
        if nombre not in [n for n, _ in nombres]:
            nombres.append((nombre, rol))
        if len(nombres) >= 6:
            break
    if not nombres:   # anexo en forma de lista numerada (nombre + DNI + lugar)
        for ml in RE_LISTA.finditer(cuerpo):
            nombre = titlecase_nombre(limpiar(ml.group(1)))
            if 2 <= len(nombre.split()) <= 7 and not PALABRAS_NO_NOMBRE.search(nombre):
                nombres.append((nombre, "titular"))
            if len(nombres) >= 20:
                break
    return {"nombres": nombres, "fecha_norma": fecha_norma}


def cargo_desde_sumilla(sumilla: str, entidad: str) -> str:
    """Cargo = desde el verbo de la sumilla hasta la entidad (sin cortar en 'del'/'de la')."""
    s = limpiar(sumilla)
    mv = re.match(r"^\s*(?:design[ao]n?|nombr[ao]n?|encarg[ao]n?|ratific[ao]n?)\s+(?:a\s+)?", s, re.I)
    if not mv:
        return ""
    resto = s[mv.end():]
    if entidad:
        i = resto.find(entidad)
        if i > 0:
            resto = resto[:i]
    resto = re.sub(r"\s+(?:de la|del|de|en la|en el|en|ante la|ante el|ante)\s*$", "", resto.strip(" ,.;"))
    return limpiar(resto)[:120]


def descargar_dispositivo(cl: httpx.Client, op: str) -> str:
    """HTML del dispositivo, con cache local (no versionada). '' si falla."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{op}.html"
    if f.exists() and f.stat().st_size > 1000:
        return f.read_text(encoding="utf-8", errors="ignore")
    try:
        r = cl.get(DISPOSITIVO.format(op=op))
        time.sleep(DETALLE_DELAY)
        if r.status_code != 200 or len(r.text) < 1000:
            return ""
        f.write_text(r.text, encoding="utf-8")
        return r.text
    except Exception:  # noqa: BLE001
        time.sleep(DETALLE_DELAY)
        return ""


def titlecase_nombre(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s or "")).strip().title()


def parse_hit(h: dict) -> dict | None:
    sumilla = limpiar(h.get("sumilla", ""))
    if not sumilla or not INCLUYE.search(sumilla) or EXCLUYE.search(sumilla):
        return None
    f = h.get("fechaPublicacion", "")
    fecha = f"{f[:4]}-{f[4:6]}-{f[6:8]}" if len(f) == 8 else ""
    ent = ""
    me = ENTIDAD.search(sumilla)
    if me:
        ent = limpiar(me.group(1))[:90]
    cargo = cargo_desde_sumilla(sumilla, ent)
    if not cargo:
        mc = CARGO_A.search(sumilla) or CARGO_B.search(sumilla)
        if mc:
            cargo = limpiar(mc.group(1))[:90]
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
        "fecha_norma": "", "rol": "",
    }


def enriquecer(rec: dict, cl: httpx.Client | None, hoy: dt.date) -> list[dict]:
    """Descarga el dispositivo (si es reciente) y devuelve 1 fila por persona nombrada."""
    op = rec["fuente_url"].rsplit("/", 1)[-1] if rec.get("fuente_url") else ""
    reciente = False
    try:
        reciente = rec["fecha"] and (hoy - dt.date.fromisoformat(rec["fecha"])).days <= DETALLE_DIAS
    except ValueError:
        pass
    if not (cl and op and reciente):
        return [rec]
    raw = descargar_dispositivo(cl, op)
    if not raw:
        return [rec]
    det = extraer_detalle(texto_html(raw))
    rec["fecha_norma"] = det["fecha_norma"]
    if not det["nombres"]:
        return [rec]
    filas = []
    for nombre, rol in det["nombres"]:
        filas.append({**rec, "nombre": nombre, "rol": rol})
    return filas


def probar(n: int) -> None:
    """Extrae el detalle de n normas del CSV actual y lo imprime (no escribe nada)."""
    if not OUT.exists():
        print("no hay data/designaciones.csv")
        return
    rows = list(csv.DictReader(OUT.open(encoding="utf-8")))
    cl = httpx.Client(timeout=30, headers={"User-Agent": UA}, follow_redirects=True)
    hoy = dt.date.today()
    ok = 0
    for r in rows[:n]:
        op = r["fuente_url"].rsplit("/", 1)[-1]
        raw = descargar_dispositivo(cl, op)
        det = extraer_detalle(texto_html(raw)) if raw else {"nombres": [], "fecha_norma": ""}
        ent = r.get("entidad", "")
        cargo = cargo_desde_sumilla(r.get("sumilla", ""), ent) or r.get("cargo", "")
        ok += bool(det["nombres"])
        print(f"· {op} · pub {r['fecha']} · norma {det['fecha_norma'] or '—'}")
        print(f"    sumilla: {r['sumilla'][:110]}")
        print(f"    cargo:   {cargo}  | entidad: {ent or '—'}")
        print(f"    nombres: {det['nombres'] or '— (no expuesto en el texto)'}")
    cl.close()
    print(f"{ok}/{min(n, len(rows))} normas con nombre extraído (hoy {hoy})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", default="2026-07-21", help="aaaa-mm-dd (por defecto 2026-07-21)")
    ap.add_argument("--hasta", default="", help="aaaa-mm-dd (por defecto hoy)")
    ap.add_argument("--max-minutes", type=float, default=0)
    ap.add_argument("--sin-detalle", action="store_true",
                    help="no descargar la página del dispositivo (solo sumilla)")
    ap.add_argument("--probar", type=int, default=0, metavar="N",
                    help="extrae el detalle de N normas del CSV actual y lo muestra")
    args = ap.parse_args()
    if args.probar:
        probar(args.probar)
        return

    fi = args.desde.replace("-", "")
    ff = (args.hasta or time.strftime("%Y-%m-%d")).replace("-", "")
    start = json.loads(CKPT.read_text()).get("start", 0) if CKPT.exists() else 0
    if start and OUT.exists():
        with OUT.open(encoding="utf-8") as fh:
            if fh.readline().strip().split(",") != FIELDS:
                start = 0   # el CSV es de un formato anterior: se rehace la ventana completa
    if start == 0 and OUT.exists():
        OUT.unlink()   # corrida desde el inicio → reescribe la ventana completa
    hoy = dt.date.today()
    cl_det = None if args.sin_detalle else httpx.Client(timeout=30, headers={"User-Agent": UA},
                                                        follow_redirects=True)
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
                for fila in enriquecer(rec, cl_det, hoy):
                    w.writerow(fila)
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
    if cl_det:
        cl_det.close()
    print(f"✔ {kept} designaciones de nombramiento · de {total} normas revisadas ({fi}→{ff})")
    if kept == 0:
        print("  (0: revisa el rango de fechas o si la API de El Peruano cambió)")


if __name__ == "__main__":
    main()
