"""Rastreo de CONTRATOS/ADJUDICACIONES del Estado vía BULK DOWNLOAD OCDS del OECE.

El OECE (ex-OSCE) publica un volcado mensual de todas las adjudicaciones SEACE v3
en formato OCDS (CSV dentro de un ZIP). Es mucho más eficiente que paginar el API
de releases. Este scraper:

  1. Lee el índice de meses disponibles (…/api/v1/file/?page=N, source seace_v3).
  2. Por cada mes pedido descarga el ZIP CSV, lo descomprime en un tmp (NO deja
     ZIP ni CSV crudos en el repo) y arma una fila por adjudicación×proveedor.
  3. Checkpoint incremental data/contratos.checkpoint.json = {"AAAA-MM": "<sha>"}.
     Re-descarga un mes solo si su SHA (endpoint /sha/) cambió — los meses recientes
     se re-publican con más datos.

Salida: data/contratos.csv (una fila por award×supplier).
Columnas: ocid, anio, mes, fecha, monto, moneda, comprador, comprador_ruc,
          comprador_sector, proveedor, proveedor_ruc, tipo_proveedor, objeto.

Uso:
  python scrapers/scrape_contratos.py                 # últimos 6 meses (prueba)
  python scrapers/scrape_contratos.py --meses 24
  python scrapers/scrape_contratos.py --desde 2024-01 --hasta 2026-06

OJO: el ZIP de un mes con muchos años puede pesar ~10 MB. Requiere IP residencial
peruana (el API OECE bloquea rangos de datacenter). UA de navegador + timeout amplio.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import tempfile
import time
import zipfile
from collections import defaultdict
from pathlib import Path

import httpx

API = "https://contratacionesabiertas.oece.gob.pe/api/v1"
INDEX = API + "/files"
SOURCE = "seace_v3"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

OUT = Path("data/contratos.csv")
CKPT = Path("data/contratos.checkpoint.json")
FIELDS = ["ocid", "anio", "mes", "fecha", "monto", "moneda", "comprador",
          "comprador_ruc", "comprador_sector", "proveedor", "proveedor_ruc",
          "tipo_proveedor", "objeto",
          # 'src' = mes-archivo (AAAA-MM del volcado del que salió la fila). Interno:
          # es la partición por la que se reemplaza un mes al re-descargarse (el ZIP
          # de un mes trae adjudicaciones con fechas de varios meses, así que anio/mes
          # de la fila NO sirve como clave de reemplazo). build_contratos lo ignora.
          "src"]

# columnas OCDS (prefijo compiledRelease/)
CR = "compiledRelease/"
RE_AWARD = re.compile(r"awards/(\d+)/id$")
RE_SUPP = re.compile(r"awards/(\d+)/suppliers/(\d+)/id$")


def tipo_ruc(ruc: str) -> str:
    """natural (10…, 11 díg = persona, DNI embebido) / juridica (20…) / consorcio."""
    if len(ruc) == 11 and ruc.startswith("10"):
        return "natural"
    if len(ruc) == 11 and ruc.startswith("20"):
        return "juridica"
    return "consorcio"  # código interno OECE de un consorcio, no un RUC real


def csv_rows(text: str):
    """DictReader tolerante a NUL sobre un CSV ya en memoria (texto)."""
    return csv.DictReader(line.replace("\x00", "") for line in text.splitlines())


def read_zip_member(zf: zipfile.ZipFile, name: str) -> str:
    for n in zf.namelist():
        if n.endswith(name):
            return zf.read(n).decode("utf-8", errors="ignore")
    return ""


def parse_month(zbytes: bytes) -> list[dict]:
    """Descomprime un ZIP mensual y devuelve filas award×supplier."""
    zf = zipfile.ZipFile(io.BytesIO(zbytes))

    # 1) entidad compradora por ocid (role buyer/procuringEntity)
    buyers: dict[str, tuple[str, str, str]] = {}
    for r in csv_rows(read_zip_member(zf, "com_parties.csv")):
        roles = r.get(CR + "parties/0/roles", "") or ""
        if "buyer" not in roles and "procuringEntity" not in roles:
            continue
        oc = r.get("ocid")
        if oc and oc not in buyers:
            buyers[oc] = (
                r.get(CR + "parties/0/name", "") or "",
                r.get(CR + "parties/0/identifier/id", "") or "",  # código CONSUCODE OECE
                r.get(CR + "parties/0/address/department", "") or "",
            )

    # 2) título/objeto del tender por ocid (primer no vacío)
    titles: dict[str, str] = {}
    for r in csv_rows(read_zip_member(zf, "releases.csv")):
        oc = r.get("ocid")
        t = r.get("releases/0/details/tender/title", "") or ""
        if oc and t and oc not in titles:
            titles[oc] = t

    # 3) valor de cada award: (ocid, award_id) -> (monto, moneda, fecha)
    awards: dict[tuple[str, str], tuple[str, str, str]] = {}
    for r in csv_rows(read_zip_member(zf, "com_awards.csv")):
        oc = r.get("ocid")
        for col in list(r):
            m = RE_AWARD.search(col)
            if not m:
                continue
            i = m.group(1)
            aid = r.get(col) or ""
            if not aid:
                continue
            awards[(oc, aid)] = (
                r.get(f"{CR}awards/{i}/value/amount", "") or "",
                r.get(f"{CR}awards/{i}/value/currency", "") or "",
                r.get(f"{CR}awards/{i}/date", "") or "",
            )

    # 4) proveedores por award (maneja índices dinámicos award/i · supplier/j)
    out: list[dict] = []
    for r in csv_rows(read_zip_member(zf, "com_awa_suppliers.csv")):
        oc = r.get("ocid")
        buyer = buyers.get(oc, ("", "", ""))
        objeto = titles.get(oc, "")
        for col in list(r):
            m = RE_SUPP.search(col)
            if not m:
                continue
            i, j = m.group(1), m.group(2)
            sid = r.get(col) or ""
            if not sid:
                continue
            aid = r.get(f"{CR}awards/{i}/id") or ""
            monto, moneda, fecha = awards.get((oc, aid), ("", "", ""))
            ruc = sid.replace("PE-RUC-", "").strip()
            anio = fecha[:4] if len(fecha) >= 4 else ""
            mes = fecha[5:7] if len(fecha) >= 7 else ""
            out.append({
                "ocid": oc,
                "anio": anio,
                "mes": mes,
                "fecha": fecha,
                "monto": monto,
                "moneda": moneda,
                "comprador": buyer[0],
                "comprador_ruc": buyer[1],
                "comprador_sector": buyer[2],
                "proveedor": r.get(f"{CR}awards/{i}/suppliers/{j}/name", "") or "",
                "proveedor_ruc": ruc,
                "tipo_proveedor": tipo_ruc(ruc),
                "objeto": objeto[:120],
            })
    return out


def fetch_index(cl: httpx.Client) -> list[dict]:
    """Todos los meses seace_v3 disponibles (recorre la paginación)."""
    items: list[dict] = []
    page = 1
    while True:
        d = cl.get(INDEX, params={"format": "json", "page": page,
                                  "paginateBy": 1000, "source": SOURCE}).json()
        res = d.get("results", [])
        items += [x for x in res if x.get("source") == SOURCE]
        nxt = (d.get("pagination") or {}).get("next_page_number")
        if not res or not nxt:
            break
        page = nxt
        time.sleep(1)
    # dedup por (year, month), más reciente primero
    seen, uniq = set(), []
    for it in sorted(items, key=lambda x: (x.get("year", ""), x.get("month", "")), reverse=True):
        key = (it.get("year"), it.get("month"))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(it)
    return uniq


def load_existing() -> dict[str, list[dict]]:
    """Filas ya guardadas, agrupadas por 'AAAA-MM' (para reemplazar meses re-procesados)."""
    by_month: dict[str, list[dict]] = defaultdict(list)
    if not OUT.exists():
        return by_month
    fh = OUT.open(encoding="utf-8", errors="ignore", newline="")
    for r in csv.DictReader(line.replace("\x00", "") for line in fh):
        # partición = mes-archivo de procedencia (col 'src'); compat con CSV viejos sin 'src'
        key = r.get("src") or f"{r.get('anio','')}-{r.get('mes','')}"
        by_month[key].append(r)
    fh.close()
    return by_month


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--meses", type=int, default=6, help="últimos N meses (default 6)")
    ap.add_argument("--desde", help="AAAA-MM inclusive (ignora --meses)")
    ap.add_argument("--hasta", help="AAAA-MM inclusive")
    args = ap.parse_args()

    ckpt = json.loads(CKPT.read_text()) if CKPT.exists() else {}
    cl = httpx.Client(timeout=180, headers={"User-Agent": UA}, follow_redirects=True)

    print("· leyendo índice de meses OECE…", flush=True)
    index = fetch_index(cl)
    print(f"  {len(index)} meses seace_v3 disponibles "
          f"({index[-1]['year']}-{index[-1]['month']} … {index[0]['year']}-{index[0]['month']})",
          flush=True)

    def ym(it):
        return f"{it['year']}-{it['month']}"

    if args.desde or args.hasta:
        lo = args.desde or "0000-00"
        hi = args.hasta or "9999-99"
        target = [it for it in index if lo <= ym(it) <= hi]
    else:
        target = index[: args.meses]
    target.sort(key=ym)  # cronológico

    procesados: list[str] = []
    all_months = load_existing()  # dict AAAA-MM -> filas
    total_new = 0

    for it in target:
        mkey = ym(it)
        sha_url = it["files"].get("sha")
        try:
            sha = cl.get(sha_url).text.strip()[:80] if sha_url else ""
        except Exception as e:
            print(f"  ! {mkey}: no pude leer sha ({e}); lo salto", flush=True)
            continue
        if ckpt.get(mkey) == sha and mkey in all_months:
            print(f"  = {mkey}: sin cambios (sha en checkpoint), salto", flush=True)
            continue

        csv_url = it["files"].get("csv")
        try:
            r = cl.get(csv_url)
            r.raise_for_status()
            rows = parse_month(r.content)
        except Exception as e:
            print(f"  ! {mkey}: fallo descarga/parseo ({e}); reintento en 5s", flush=True)
            time.sleep(5)
            try:
                r = cl.get(csv_url)
                r.raise_for_status()
                rows = parse_month(r.content)
            except Exception as e2:
                print(f"  ! {mkey}: fallo definitivo ({e2}); lo salto", flush=True)
                continue

        for row in rows:
            row["src"] = mkey
        all_months[mkey] = rows        # reemplaza la partición completa de ese mes-archivo
        ckpt[mkey] = sha
        procesados.append(mkey)
        total_new += len(rows)
        print(f"  ✔ {mkey}: {len(rows):,} filas", flush=True)
        time.sleep(1)  # cortesía entre descargas

    cl.close()

    # reescribe data/contratos.csv completo, ordenado por mes y ocid
    OUT.parent.mkdir(parents=True, exist_ok=True)
    n_total = 0
    tmp = OUT.with_suffix(".csv.tmp")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for mkey in sorted(all_months):
            for row in all_months[mkey]:
                w.writerow(row)
                n_total += 1
    tmp.replace(OUT)
    CKPT.write_text(json.dumps(ckpt, ensure_ascii=False, indent=0))

    print(f"\n✔ meses procesados: {', '.join(procesados) or '(ninguno nuevo)'}", flush=True)
    print(f"✔ filas nuevas: {total_new:,} · data/contratos.csv total: {n_total:,} filas "
          f"({len(all_months)} meses)", flush=True)


if __name__ == "__main__":
    main()
