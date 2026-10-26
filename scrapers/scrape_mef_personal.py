#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Serie anual MEF 2015-2026 del gasto en personal (genéricas 2.1 y 2.2) a nivel nacional.

Fuente: Consulta Amigable del MEF (https://apps5.mineco.gob.pe/transparencia/Navegador/),
corte "Genérica" sobre el TOTAL (todos los niveles de gobierno, Actividades + Proyectos).
El API de datos abiertos (api.datosabiertos.mef.gob.pe) devolvía 404 el 26-oct-2026, por eso
se scrapea el navegador ASP.NET.

Mecánica (misma que qhaway-dashboard/etl/scraper_consulta_amigable.py, sin bs4/requests):
  - httpx.Client con cookie jar; GET default.aspx primero (WAF Incapsula).
  - GET default.aspx?y=AÑO&ap=ActProy y luego Navegar.aspx?y=AÑO&ap=ActProy.
  - La fila TOTAL viene auto-seleccionada en el radio `grp1`; su value codifica los montos:
      /PIA/PIM/CompromisoAnual/CompromisoMensual/Devengado/Girado/Certificación
  - POST del form (action Navegar_7.aspx) con __VIEWSTATE/__EVENTVALIDATION y SOLO el botón
    ctl00$CPH1$BtnGenerica -> tabla ctl00_CPH1_Mt0 con una fila por genérica; cada fila tiene
    un radio grp1 cuyo aria-label trae PIA/PIM/CERTIFICACION/.../DEVENGADO/GIRADO.
  - Lento a propósito (pausas) y con reintentos; reanuda saltando años ya en el CSV.

Salida: data/mef_personal_anual.csv con columnas
  anio,generica,pia,pim,devengado,total_pim_anio,total_devengado_anio,capturado_en,fuente_url
(una fila por año y genérica: "2.1 PERSONAL Y OBLIGACIONES SOCIALES", "2.2 PENSIONES Y OTRAS
PRESTACIONES SOCIALES"). Montos en soles corrientes, float. Nunca se inventa un número: si un
año falla tras los reintentos, simplemente no aparece en el CSV y se reporta en stderr.

Uso:
  .venv/bin/python scrapers/scrape_mef_personal.py [--years 2015-2026] [--max-minutes 40] [--force]
"""
import argparse
import csv
import html as H
import os
import re
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser

import httpx

BASE = "https://apps5.mineco.gob.pe/transparencia/Navegador/"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "data", "mef_personal_anual.csv")
COLS = ["anio", "generica", "pia", "pim", "devengado", "total_pim_anio",
        "total_devengado_anio", "capturado_en", "fuente_url"]
GENERICAS = {
    "2.1 PERSONAL Y OBLIGACIONES SOCIALES": re.compile(r"PERSONAL\s+Y\s+OBLIGACIONES\s+SOCIALES", re.I),
    "2.2 PENSIONES Y OTRAS PRESTACIONES SOCIALES": re.compile(r"PENSIONES\s+Y\s+OTRAS\s+PRESTACIONES", re.I),
}


class FormFields(HTMLParser):
    """Recoge los campos del form ASP.NET (hidden/text/select/radios marcados) y el action."""

    def __init__(self):
        super().__init__()
        self.fields, self.action = {}, None
        self._sel = self._first = self._chosen = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form" and self.action is None:
            self.action = a.get("action")
        elif tag == "input":
            n, t = a.get("name"), (a.get("type") or "text").lower()
            if not n or t in ("submit", "button", "image", "reset"):
                return
            if t in ("radio", "checkbox"):
                if "checked" in a:
                    self.fields[n] = a.get("value", "on")
            else:
                self.fields[n] = a.get("value", "")
        elif tag == "select":
            self._sel, self._first, self._chosen = a.get("name"), None, None
        elif tag == "option" and self._sel:
            v = a.get("value", "")
            if self._first is None:
                self._first = v
            if "selected" in a:
                self._chosen = v

    def handle_endtag(self, tag):
        if tag == "select" and self._sel:
            self.fields[self._sel] = self._chosen if self._chosen is not None else (self._first or "")
            self._sel = None


def num(s):
    s = (s or "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def parse_grp1_value(value):
    """'/PIA/PIM/CompAnual/CompMensual/Devengado/Girado/Cert' (orden validado con aria-label)."""
    parts = value.split("/")
    if len(parts) < 7:
        return None
    nums = [num(p) for p in parts[1:8]]
    if any(n is None for n in nums[:6]):
        return None
    return {"pia": nums[0], "pim": nums[1], "devengado": nums[4], "girado": nums[5]}


def parse_generica_rows(page):
    """Cada <tr id="trN"> de la tabla Mt0 tiene un radio grp1 (value con los montos) y una celda
    <td align="left"> con 'CODIGO: NOMBRE'. Desde ~2016 el radio trae además aria-label con los
    montos formateados; cuando existe se usa para validar el orden del value (2015 no lo trae)."""
    rows = []
    for tr in re.finditer(r'<tr[^>]*id="tr\d+"[^>]*>(.*?)</tr>', page, re.S):
        block = tr.group(1)
        radio = re.search(r'<input[^>]*name="grp1"[^>]*>', block, re.S)
        if not radio:
            continue
        val = re.search(r'value="([^"]*)"', radio.group(0))
        if not val:
            continue
        amounts = parse_grp1_value(val.group(1))
        if not amounts:
            continue
        cell = re.search(r'<td align="left"[^>]*>\s*(.*?)<', block, re.S)
        name = H.unescape(cell.group(1)).strip() if cell else ""
        name = re.sub(r"^[\d\-]+:\s*", "", name)  # '5-21: PERSONAL...' -> 'PERSONAL...'
        lab = re.search(r'aria-label="([^"]*)"', radio.group(0), re.S)
        if lab:
            label = H.unescape(lab.group(1))
            if not name:
                name = label.split(",")[0].strip()
            lab_pia = num((re.search(r"PIA:\s*([\d,\.]+)", label) or [None, None])[1])
            lab_dev = num((re.search(r"DEVENGADO:\s*([\d,\.]+)", label) or [None, None])[1])
            if lab_pia is not None and abs(lab_pia - amounts["pia"]) > 1:
                raise RuntimeError(f"PIA no cuadra con aria-label en '{name}': {lab_pia} vs {amounts['pia']}")
            if lab_dev is not None and abs(lab_dev - amounts["devengado"]) > 1:
                raise RuntimeError(f"Devengado no cuadra con aria-label en '{name}': {lab_dev} vs {amounts['devengado']}")
        if not name:
            continue
        rows.append({"nombre": name, "codigo": val.group(1).split("/")[0], **amounts})
    return rows


def postback(c, page, url, btn, grp1=None):
    """Re-envía el form ASP.NET con el radio grp1 elegido y SOLO el botón indicado."""
    f = FormFields()
    f.feed(page)
    data = dict(f.fields)
    if grp1:
        data["grp1"] = grp1
    data[btn] = btn.split("$")[-1]
    return c.post(BASE + H.unescape(f.action), data=data, headers={"Referer": url}).text


# Detalle de sub-genérica (nivel 2.x.y.z) que importa para "todas las variantes" del costo en personal.
# Códigos del clasificador tal como los codifica el radio grp1 ('2-3-2-8').
DETALLE = {
    "2-3-2-7": "2.3.2.7 SERVICIOS PROFESIONALES Y TECNICOS",
    "2-3-2-8": "2.3.2.8 CONTRATO ADMINISTRATIVO DE SERVICIOS (dentro de 2.3, hasta 2023)",
    "2-3-2-9": "2.3.2.9 LOCACION DE SERVICIOS REALIZADOS POR PERSONA NATURAL",
}
CAS_EN_21 = re.compile(r"CONTRATO\s+ADMINISTRATIVO\s+DE\s+SERVICIOS", re.I)


def scrape_detalle(c, year, pause=2.0):
    """Drill-down: Genérica -> Sub-Genérica -> Sub-Genérica Detalle.
    a) 2.3 Bienes y servicios -> 2.3.2 Contratación de servicios -> 2.3.2.7 / 2.3.2.8 / 2.3.2.9
    b) 2.1 Personal -> 2.1.1 Retribuciones y complementos -> fila CAS (2.1.1.13 desde 2024)
    Devuelve filas CSV; si una ruta no existe ese año, simplemente no aporta filas (no se inventa)."""
    url = f"{BASE}Navegar.aspx?y={year}&ap=ActProy"
    c.get(f"{BASE}default.aspx?y={year}&ap=ActProy")
    page = c.get(url).text
    g = re.search(r'name="grp1"[^>]*value="([^"]*)"', page)
    if not g:
        raise RuntimeError("sin radio grp1 (fila TOTAL)")
    total = parse_grp1_value(g.group(1))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    p1 = postback(c, page, url, "ctl00$CPH1$BtnGenerica", g.group(1))
    gen = {r["codigo"]: r for r in parse_generica_rows(p1)}
    found = []

    def drill(gen_code, sub_code, want):
        if gen_code not in gen:
            return
        time.sleep(pause)
        # el value del radio trae code/montos; hay que mandar el value completo
        gv = re.search(r'name="grp1"[^>]*value="(%s/[^"]*)"' % gen_code, p1).group(1)
        p2 = postback(c, p1, url, "ctl00$CPH1$BtnSubGenerica", gv)
        sv = re.search(r'name="grp1"[^>]*value="(%s/[^"]*)"' % sub_code, p2)
        if not sv:
            return
        time.sleep(pause)
        p3 = postback(c, p2, url, "ctl00$CPH1$BtnSubGenericaDetalle", sv.group(1))
        for r in parse_generica_rows(p3):
            label = want(r)
            if label:
                found.append({"anio": year, "generica": label, "pia": r["pia"], "pim": r["pim"],
                              "devengado": r["devengado"], "total_pim_anio": total["pim"],
                              "total_devengado_anio": total["devengado"], "capturado_en": now,
                              "fuente_url": url})

    drill("5-2-3", "2-3-2", lambda r: DETALLE.get(r["codigo"]))
    drill("5-2-1", "2-1-1", lambda r: (f"{r['codigo'].replace('-', '.')} CONTRATO ADMINISTRATIVO DE SERVICIOS "
                                      f"(dentro de 2.1, desde 2024)") if CAS_EN_21.search(r["nombre"]) else None)
    return found


def new_client():
    c = httpx.Client(headers={"User-Agent": UA}, timeout=90, follow_redirects=True)
    c.get(BASE + "default.aspx")
    return c


def scrape_year(c, year):
    url = f"{BASE}Navegar.aspx?y={year}&ap=ActProy"
    c.get(f"{BASE}default.aspx?y={year}&ap=ActProy")
    page = c.get(url).text
    sel = re.search(r'<select[^>]*name="ctl00\$CPH1\$DrpYear".*?</select>', page, re.S)
    chosen = re.search(r'<option selected="selected" value="(\d+)"', sel.group(0)) if sel else None
    if not chosen or chosen.group(1) != str(year):
        raise RuntimeError(f"año no fijado (got {chosen.group(1) if chosen else '?'})")
    g = re.search(r'name="grp1"[^>]*value="([^"]*)"', page)
    if not g:
        raise RuntimeError("sin radio grp1 (fila TOTAL)")
    total = parse_grp1_value(g.group(1))
    if not total:
        raise RuntimeError("fila TOTAL ilegible")
    f = FormFields()
    f.feed(page)
    data = dict(f.fields)
    data["grp1"] = g.group(1)
    data["ctl00$CPH1$BtnGenerica"] = "Genérica"
    resp = c.post(BASE + H.unescape(f.action), data=data, headers={"Referer": url}).text
    rows = parse_generica_rows(resp)
    if len(rows) < 5:
        raise RuntimeError(f"solo {len(rows)} genéricas")
    found = {}
    for gen, pat in GENERICAS.items():
        hit = [r for r in rows if pat.search(r["nombre"])]
        if len(hit) != 1:
            raise RuntimeError(f"{gen}: {len(hit)} coincidencias")
        found[gen] = hit[0]
    # consistencia: la suma de devengado por genérica debe cuadrar con el TOTAL (tolerancia 0.5 %).
    # Se usa devengado y no PIM porque la fila "Reserva de contingencia" (nunca devenga) a veces
    # no trae radio parseable (p. ej. 2020) y descuadra el PIM en ~1 %.
    s_dev = sum(r["devengado"] for r in rows)
    if total["devengado"] > 0 and abs(s_dev - total["devengado"]) / total["devengado"] > 0.005:
        raise RuntimeError(f"suma genéricas devengado {s_dev:.0f} != total {total['devengado']:.0f}")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = []
    for gen, r in found.items():
        out.append({"anio": year, "generica": gen, "pia": r["pia"], "pim": r["pim"],
                    "devengado": r["devengado"], "total_pim_anio": total["pim"],
                    "total_devengado_anio": total["devengado"], "capturado_en": now,
                    "fuente_url": url})
    return out, len(rows)


def load_existing():
    if not os.path.exists(OUT):
        return {}
    data = {}
    with open(OUT, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            data.setdefault(int(r["anio"]), []).append(r)
    return data


def save(data):
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        for y in sorted(data):
            for r in data[y]:
                w.writerow({k: r.get(k, "") for k in COLS})
    os.replace(tmp, OUT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="2015-2026")
    ap.add_argument("--max-minutes", type=float, default=40)
    ap.add_argument("--retries", type=int, default=4)
    ap.add_argument("--force", action="store_true", help="re-scrapear años ya presentes")
    ap.add_argument("--detalle", action="store_true",
                    help="además de 2.1/2.2, drill-down a CAS, locación de servicios y servicios profesionales")
    a = ap.parse_args()
    y0, y1 = (int(x) for x in a.years.split("-"))
    years = list(range(y1, y0 - 1, -1))
    data = {} if a.force else load_existing()
    is_det = lambda r: r["generica"][:7].count(".") >= 2  # '2.3.2.8 ...' / '2.1.1.13 ...'
    def done(y):
        rows = data.get(y, [])
        if not any(not is_det(r) for r in rows):
            return False
        return (not a.detalle) or any(is_det(r) for r in rows)
    print(f"reanudando: años hechos {sorted(y for y in data if done(y))}", flush=True)
    t0 = time.time()
    c = new_client()
    failed = []
    for y in years:
        if done(y):
            continue
        if (time.time() - t0) / 60 > a.max_minutes:
            print(f"tiempo agotado ({a.max_minutes} min); faltan {[x for x in years if x not in data]}", flush=True)
            break
        ok = False
        for attempt in range(a.retries):
            try:
                base = [r for r in data.get(y, []) if not is_det(r)]
                if not base:
                    base, n = scrape_year(c, y)
                    print(f"  {y}: {n} genéricas; 2.1 devengado {base[0]['devengado']/1e9:.2f} mil M, "
                          f"total PIM {base[0]['total_pim_anio']/1e9:.1f} mil M", flush=True)
                det = []
                if a.detalle:
                    time.sleep(2)
                    det = scrape_detalle(c, y)
                    print(f"  {y}: detalle " + "; ".join(f"{r['generica'][:7]} dev {r['devengado']/1e9:.2f}" for r in det), flush=True)
                data[y] = base + det
                save(data)
                print(f"  {y}: escrito", flush=True)
                ok = True
                break
            except Exception as e:  # noqa: BLE001
                print(f"  {y}: error {repr(e)[:120]} (reintento {attempt + 1}/{a.retries})", flush=True)
                time.sleep(8 + 6 * attempt)
                try:
                    c = new_client()
                except Exception as e2:  # noqa: BLE001
                    print(f"  sesión: {repr(e2)[:80]}", flush=True)
        if not ok:
            failed.append(y)
        time.sleep(3)
    print(f"LISTO: {len(data)} años en {OUT}; fallidos: {failed}", flush=True)
    if failed:
        print(f"ADVERTENCIA: años sin dato (no se inventan): {failed}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
