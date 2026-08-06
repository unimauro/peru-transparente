"""Dump completo del RNSSC (Registro Nacional de Sanciones contra Servidores Civiles) de SERVIR.

El buscador ciudadano (https://www.sanciones.gob.pe/rnssc/) golpea una API REST JSON
pública SIN captcha. La búsqueda por apellido usa match "CONTIENE" (substring) y el
servidor NO limita resultados (el tope de 50 es solo del cliente Angular). Por eso,
barriendo TODOS los bigramas (aa..zz + Ñ) sobre apellidoPaterno y deduplicando por
sancionId se captura el registro completo: todo apellido de >=2 letras contiene al
menos un bigrama del alfabeto.

Solo devuelve sanciones VIGENTES (foto del momento, no histórico). El 100% trae DNI.

Cortés con el .gob.pe: 1 req/s, UA de navegador, Referer correcto. Reanudable por
bigrama (data/rnssc.checkpoint.json). Append a data/sanciones_rnssc.csv.
Uso: python scrapers/scrape_rnssc.py            (barrido completo)
     python scrapers/scrape_rnssc.py --bigramas AB,QU,GA   (prueba)
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from itertools import product
from pathlib import Path

import httpx

URL = "https://www.sanciones.gob.pe/rnssc-rest/rest/sancion/consultar"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
OUT = Path("data/sanciones_rnssc.csv")
CKPT = Path("data/rnssc.checkpoint.json")
ALFABETO = "ABCDEFGHIJKLMNOPQRSTUVWXYZÑ"
FIELDS = ["sancion_id", "dni", "ap_paterno", "ap_materno", "nombres", "nombre_completo",
          "entidad", "siglas", "ruc", "sector", "nivel_gobierno", "tipo_sancion",
          "categoria", "causa", "cargo", "regimen", "fecha_inicio", "fecha_fin", "estado"]


def bigramas() -> list[str]:
    return ["".join(p) for p in product(ALFABETO, ALFABETO)]


def parse(rec: dict) -> dict:
    """Aplana un registro del JSON a las columnas del CSV."""
    s = rec.get("servidorSancionado") or {}
    e = rec.get("entidadSancionadora") or {}
    return {
        "sancion_id": rec.get("sancionId", ""),
        "dni": s.get("numeroDocumento", ""),
        "ap_paterno": s.get("apellidoPaterno", ""),
        "ap_materno": s.get("apellidoMaterno", ""),
        "nombres": s.get("nombres", ""),
        "nombre_completo": s.get("nombreCompleto", ""),
        "entidad": e.get("razonSocial", ""),
        "siglas": e.get("abreviaturaSiglas", ""),
        "ruc": e.get("nroRuc", ""),
        "sector": (e.get("sector") or {}).get("sectorNombre", ""),
        "nivel_gobierno": (e.get("nivelGobierno") or {}).get("nombreParametro", ""),
        "tipo_sancion": (rec.get("tipoSancion") or {}).get("nombreParametro", ""),
        "categoria": (rec.get("categoriaSancion") or {}).get("nombreParametro", ""),
        "causa": (rec.get("causaSancion") or {}).get("nombreParametro", ""),
        "cargo": rec.get("cargoLaboralServidor", ""),
        "regimen": rec.get("nombreRegimenLaboral", ""),
        "fecha_inicio": rec.get("fechaInicio", ""),
        "fecha_fin": rec.get("fechaFin", ""),
        "estado": rec.get("estadoSancion", ""),
    }


def consultar(cl: httpx.Client, bigrama: str) -> list[dict]:
    """POST al RNSSC por apellidoPaterno=bigrama. Reintenta ante fallos de red."""
    payload = {"jsonEntrada": {"ipCliente": "1.1.1.1", "tipoDocumento": "",
                               "numeroDocumento": "", "nombres": "",
                               "apellidoPaterno": bigrama, "apellidoMaterno": "",
                               "tipoConsulta": "EXT_TRANS"}}
    for intento in range(4):
        try:
            r = cl.post(URL, json=payload)
            if r.status_code != 200 or not r.text.strip():
                return []
            return (r.json() or {}).get("data") or []
        except Exception:
            time.sleep(5 * (intento + 1))
    return []


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bigramas", default="", help="lista separada por comas (prueba); por defecto barre todo")
    ap.add_argument("--pausa", type=float, default=1.0, help="segundos entre requests (cortesía)")
    args = ap.parse_args()

    objetivo = [b.upper() for b in args.bigramas.split(",") if b.strip()] if args.bigramas else bigramas()
    hechos: set = set(json.loads(CKPT.read_text()).get("done", [])) if CKPT.exists() else set()
    if args.bigramas:            # en modo prueba ignoramos el checkpoint acumulado
        hechos = set()

    seen: set = set()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    write_header = not OUT.exists() or OUT.stat().st_size == 0
    if not write_header:         # repoblar seen desde el CSV para no duplicar entre corridas
        for row in csv.DictReader(OUT.open(encoding="utf-8", errors="ignore")):
            seen.add(row.get("sancion_id"))

    cl = httpx.Client(timeout=90, headers={
        "User-Agent": UA,
        "Content-Type": "application/json; charset=UTF-8",
        "Origin": "https://www.sanciones.gob.pe",
        "Referer": "https://www.sanciones.gob.pe/rnssc/",
    })
    nuevos = 0
    with OUT.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if write_header:
            w.writeheader()
        for i, bg in enumerate(objetivo, 1):
            if bg in hechos:
                continue
            data = consultar(cl, bg)
            for rec in data:
                sid = str(rec.get("sancionId", ""))
                if not sid or sid in seen:
                    continue
                seen.add(sid)
                w.writerow(parse(rec))
                nuevos += 1
            hechos.add(bg)
            if not args.bigramas and (i % 20 == 0 or i == len(objetivo)):
                CKPT.write_text(json.dumps({"done": sorted(hechos)}))
                fh.flush()
                print(f"  {i}/{len(objetivo)} bigramas · {len(seen)} sanciones únicas", flush=True)
            time.sleep(args.pausa)
    if not args.bigramas:
        CKPT.write_text(json.dumps({"done": sorted(hechos)}))
    cl.close()
    print(f"✔ {len(seen)} sanciones únicas en total ({nuevos} nuevas esta corrida) → {OUT}")


if __name__ == "__main__":
    main()
