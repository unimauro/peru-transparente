"""Agrega los CONTRATOS/ADJUDICACIONES OCDS (data/contratos.csv) a JSON estático.

Genera en frontend/public/data/:
  - contratos.json            : resumen global (monto por año, % natural/jurídica,
                                top 20 entidades compradoras, top 20 proveedores).
  - contratos_por_entidad.json: por entidad compradora → monto, nº, top proveedores.
  - contratos_por_proveedor.json: por proveedor → monto, nº, entidades y
                                concentración (% del monto que viene de su comprador
                                principal = señal de dependencia de un solo cliente).

Anti-overclaiming: los montos son ADJUDICADO (valor de la adjudicación), NO
necesariamente pagado/devengado. Se marca en _meta de cada archivo.

Privacidad: el RUC de una persona natural (10…) embebe el DNI (dígitos 2-9), dato
sensible. NO se publica ese RUC: solo el nombre y el tipo "natural". El RUC de una
persona jurídica (20…) sí es público y se publica completo.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

SRC = Path("data/contratos.csv")
OUTDIR = Path("frontend/public/data")

# límites de tamaño de los shards (bound de los JSON publicados)
TOP_ENTIDADES = 500
TOP_PROVEEDORES = 1500
TOP_PROV_POR_ENTIDAD = 15
TOP_ENT_POR_PROVEEDOR = 15

NOTA = ("Montos = ADJUDICADO (valor de la adjudicación en el SEACE), "
        "no necesariamente pagado ni devengado. Fuente: OECE/SEACE v3 (bulk OCDS).")


def na(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKD", s or "")
                  .encode("ascii", "ignore").decode().upper()).strip()


def rows(path: Path):
    """csv.DictReader tolerante a bytes NUL (líneas corruptas del scraping)."""
    fh = path.open(encoding="utf-8", errors="ignore", newline="")
    return csv.DictReader(line.replace("\x00", "") for line in fh)


def pub_ruc(ruc: str, tipo: str) -> str | None:
    """RUC publicable: completo si jurídica; None si natural (DNI) o consorcio (código interno)."""
    return ruc if tipo == "juridica" and len(ruc) == 11 else None


def monto(v: str) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def main() -> None:
    if not SRC.exists():
        print("aún no hay data/contratos.csv (corre scrapers/scrape_contratos.py)")
        return

    OUTDIR.mkdir(parents=True, exist_ok=True)

    por_anio: dict[str, dict] = defaultdict(lambda: {"monto": 0.0, "n": 0})
    por_tipo: dict[str, dict] = defaultdict(lambda: {"monto": 0.0, "n": 0})
    # entidad compradora (clave = nombre normalizado)
    ent: dict[str, dict] = defaultdict(
        lambda: {"nombre": "", "ruc": "", "sector": "", "monto": 0.0, "n": 0,
                 "prov": defaultdict(lambda: {"nombre": "", "ruc": "", "tipo": "", "monto": 0.0, "n": 0})})
    # proveedor (clave = RUC si válido, si no nombre normalizado)
    prov: dict[str, dict] = defaultdict(
        lambda: {"nombre": "", "ruc": "", "tipo": "", "monto": 0.0, "n": 0,
                 "ent": defaultdict(lambda: {"nombre": "", "monto": 0.0, "n": 0})})

    n_filas = 0
    meses: set[str] = set()
    for r in rows(SRC):
        n_filas += 1
        m = monto(r.get("monto", ""))
        anio = r.get("anio", "") or "?"
        tipo = r.get("tipo_proveedor", "") or "?"
        meses.add(f"{anio}-{r.get('mes','')}")

        por_anio[anio]["monto"] += m
        por_anio[anio]["n"] += 1
        por_tipo[tipo]["monto"] += m
        por_tipo[tipo]["n"] += 1

        ek = na(r.get("comprador", ""))
        if ek:
            e = ent[ek]
            e["nombre"] = e["nombre"] or r.get("comprador", "")
            e["ruc"] = e["ruc"] or r.get("comprador_ruc", "")
            e["sector"] = e["sector"] or r.get("comprador_sector", "")
            e["monto"] += m
            e["n"] += 1

        ruc = (r.get("proveedor_ruc", "") or "").strip()
        pk = ruc if len(ruc) == 11 else "N:" + na(r.get("proveedor", ""))
        if pk and pk != "N:":
            p = prov[pk]
            p["nombre"] = p["nombre"] or r.get("proveedor", "")
            p["ruc"] = p["ruc"] or ruc
            p["tipo"] = p["tipo"] or tipo
            p["monto"] += m
            p["n"] += 1
            if ek:
                pe = p["ent"][ek]
                pe["nombre"] = pe["nombre"] or r.get("comprador", "")
                pe["monto"] += m
                pe["n"] += 1
                ep = ent[ek]["prov"][pk]
                ep["nombre"] = ep["nombre"] or r.get("proveedor", "")
                ep["ruc"] = ep["ruc"] or ruc
                ep["tipo"] = ep["tipo"] or tipo
                ep["monto"] += m
                ep["n"] += 1

    monto_total = sum(v["monto"] for v in por_anio.values())
    meta = {
        "fuente": "OECE / SEACE v3 (bulk download OCDS)",
        "nota": NOTA,
        "generado": dt.date.today().isoformat(),
        "meses": sorted(m for m in meses if m and not m.startswith("?")),
        "n_adjudicaciones": n_filas,
        "monto_total": round(monto_total),
    }

    # ---------- contratos.json (resumen global) ----------
    top_ent = sorted(ent.values(), key=lambda x: -x["monto"])[:20]
    top_prov = sorted(prov.values(), key=lambda x: -x["monto"])[:20]
    resumen = {
        "monto_total": round(monto_total),
        "n_adjudicaciones": n_filas,
        "por_tipo": {t: {"monto": round(v["monto"]), "n": v["n"],
                         "pct_monto": round(100 * v["monto"] / monto_total, 1) if monto_total else 0}
                     for t, v in sorted(por_tipo.items(), key=lambda x: -x[1]["monto"])},
    }
    (OUTDIR / "contratos.json").write_text(json.dumps({
        "_meta": meta,
        "resumen": resumen,
        "por_anio": [{"anio": a, "monto": round(v["monto"]), "n": v["n"]}
                     for a, v in sorted(por_anio.items())],
        "top_entidades": [{"entidad": e["nombre"], "ruc": e["ruc"], "sector": e["sector"],
                           "monto": round(e["monto"]), "n": e["n"]} for e in top_ent],
        "top_proveedores": [{"proveedor": p["nombre"], "ruc": pub_ruc(p["ruc"], p["tipo"]),
                             "tipo": p["tipo"], "monto": round(p["monto"]), "n": p["n"]}
                            for p in top_prov],
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # ---------- contratos_por_entidad.json ----------
    ent_list = sorted(ent.values(), key=lambda x: -x["monto"])[:TOP_ENTIDADES]
    ent_out = []
    for e in ent_list:
        tp = sorted(e["prov"].values(), key=lambda x: -x["monto"])[:TOP_PROV_POR_ENTIDAD]
        ent_out.append({
            "entidad": e["nombre"], "ruc": e["ruc"], "sector": e["sector"],
            "monto_total": round(e["monto"]), "n_adjudicaciones": e["n"],
            "top_proveedores": [{"proveedor": x["nombre"], "ruc": pub_ruc(x["ruc"], x["tipo"]),
                                 "tipo": x["tipo"], "monto": round(x["monto"]), "n": x["n"]} for x in tp],
        })
    (OUTDIR / "contratos_por_entidad.json").write_text(json.dumps({
        "_meta": {**meta, "n_entidades": len(ent), "truncado_top": TOP_ENTIDADES},
        "entidades": ent_out,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # ---------- contratos_por_proveedor.json ----------
    prov_list = sorted(prov.values(), key=lambda x: -x["monto"])[:TOP_PROVEEDORES]
    prov_out = []
    for p in prov_list:
        te = sorted(p["ent"].values(), key=lambda x: -x["monto"])[:TOP_ENT_POR_PROVEEDOR]
        top_ent_monto = max((x["monto"] for x in p["ent"].values()), default=0.0)
        conc = round(100 * top_ent_monto / p["monto"], 1) if p["monto"] else 0.0
        prov_out.append({
            "proveedor": p["nombre"], "ruc": pub_ruc(p["ruc"], p["tipo"]), "tipo": p["tipo"],
            "monto_total": round(p["monto"]), "n": p["n"], "n_entidades": len(p["ent"]),
            "concentracion": conc,  # % del monto que viene de su comprador principal
            "entidades": [{"entidad": x["nombre"], "monto": round(x["monto"]), "n": x["n"]} for x in te],
        })
    (OUTDIR / "contratos_por_proveedor.json").write_text(json.dumps({
        "_meta": {**meta, "n_proveedores": len(prov), "truncado_top": TOP_PROVEEDORES,
                  "privacidad": "RUC de persona natural omitido (embebe DNI); solo se publica RUC de persona jurídica."},
        "proveedores": prov_out,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    print(f"✔ {n_filas:,} adjudicaciones · S/{round(monto_total):,} adjudicado · "
          f"{len(ent):,} entidades · {len(prov):,} proveedores · {len(meta['meses'])} meses")
    for f in ["contratos.json", "contratos_por_entidad.json", "contratos_por_proveedor.json"]:
        kb = (OUTDIR / f).stat().st_size / 1024
        print(f"   {f}: {kb:,.1f} KB")


if __name__ == "__main__":
    main()
