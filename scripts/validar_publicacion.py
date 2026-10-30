#!/usr/bin/env python3
"""Validador de PUBLICACIÓN: integridad + privacidad de frontend/public/data antes del git add.

Solo stdlib. Falla (exit 1) y NO debe publicarse nada si:
  1. Algún JSON no parsea, o contiene NaN/Infinity (JSON inválido para el navegador).
  2. Algún archivo clave está vacío/degradado: métrica < umbral ABSOLUTO (ver UMBRALES) o
     < 70 % del último snapshot en data/historico/snapshots/<fecha>/ (el commit e9ae5ed
     publicó "0 funcionarios" y nadie lo detectó).
  2b. Valores degradados en la planilla publicada: < 95 % de `total` numérico en
     funcionarios_sample/funcionarios_clave, algún nombre con el texto incrustado de SUNAT
     ("Para ver la información…"), o < 1 % de personal 276/728 (suma de `regimenes` de
     entidad/*.json) cuando meta.planilla_capturada ≥ 2026-10-30 (conector corregido).
  3. Hay PII en campos de texto: DNI (8 dígitos aislados), RUC de persona natural completo
     (10 + 9 dígitos), correos de dominios personales, celulares (9xxxxxxxx) o un campo
     llamado `dni`. Los RUC de empresa (11 dígitos, 20…), montos y URLs no cuentan.

Uso:
  .venv/bin/python scripts/validar_publicacion.py            # valida y sale 0/1
  .venv/bin/python scripts/validar_publicacion.py --informe  # además imprime conteos PII por archivo
  PT_FORCE=1 …                                               # degrada los fallos a avisos (exit 0)

Se integra en actualizar.sh ANTES de `git add` y debería ser un step en los workflows que
publiquen datos (deploy-pages.yml / scrape-*.yml), justo antes del commit.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "frontend/public/data"
SNAPS = REPO / "data/historico/snapshots"
FRACCION_SNAPSHOT = 0.70

# ───────────────────────── umbrales absolutos ─────────────────────────
# (archivo, descripción, extractor(json) -> número, mínimo)
UMBRALES: list[tuple[str, str, object, int]] = [
    ("national_kpis.json", "total_funcionarios", lambda d: d.get("total_funcionarios", 0), 150_000),
    ("national_kpis.json", "entities_with_data", lambda d: d.get("entities_with_data", 0), 500),
    ("entidades.json", "entidades con datos",
     lambda d: sum(1 for e in d.get("items", []) if e.get("funcionarios")), 500),
    ("ordenes_servicio.json", "total_ordenes", lambda d: d.get("total_ordenes", 0), 3_000),
    ("contratos.json", "n_adjudicaciones", lambda d: (d.get("_meta") or {}).get("n_adjudicaciones", 0), 10_000),
    ("sanciones.json", "total_sanciones", lambda d: d.get("total_sanciones", 0), 20_000),
    ("dj.json", "total_declaraciones", lambda d: d.get("total_declaraciones", 0), 60_000),
    ("autoridades.json", "autoridades", lambda d: len(d.get("items", [])), 5_000),
    ("nuevos_funcionarios.json", "total publicado", lambda d: d.get("total", 0), 1_000),
    ("nuevos_funcionarios.json", "items con nombre",
     lambda d: sum(1 for x in d.get("items", []) if (x.get("nombre") or "").strip()), 1),
    ("bot_context.json", "chars de contexto", lambda d: len(d.get("context", "")), 3_000),
]
# personas/*.json se suma aparte (shards)
MIN_PERSONAS = 400_000
# Guard de valores (misma regla que build_site_data.guard_valores)
CONECTOR_CORREGIDO_DESDE = "2026-10-30"
MIN_NUMERICOS = 0.95
MIN_276_728 = 0.01
SUNAT_BOILERPLATE = "para ver la informaci"
RE_276_728 = re.compile(r"\b(276|728)\b")


def _num(v) -> bool:
    try:
        float(str(v).replace(",", ""))
        return True
    except (TypeError, ValueError):
        return False


# Claves del snapshot a comparar (≥ 70 % del último snapshot) — mismos archivos que
# copia snapshot_historico.py.
SNAPSHOT_KEYS: dict[str, list[tuple[str, object]]] = {
    "national_kpis.json": [("total_funcionarios", lambda d: d.get("total_funcionarios", 0)),
                           ("entities_with_data", lambda d: d.get("entities_with_data", 0))],
    "contratos.json": [("n_adjudicaciones", lambda d: (d.get("_meta") or {}).get("n_adjudicaciones", 0))],
    "sanciones.json": [("total_sanciones", lambda d: d.get("total_sanciones", 0))],
    "dj.json": [("total_declaraciones", lambda d: d.get("total_declaraciones", 0))],
    "meta.json": [("funcionarios_descargados", lambda d: d.get("funcionarios_descargados", 0)),
                  ("entidades_con_datos", lambda d: d.get("entidades_con_datos", 0))],
}

# ───────────────────────── PII ─────────────────────────
DNI_SUELTO = re.compile(r"(?<!\d)(?<!\d\.)\d{8}(?!\d)(?!\.\d)")
RUC_NATURAL = re.compile(r"(?<!\d)10\d{9}(?!\d)")
# (no confundir con montos "S/985 234 123": los separadores de miles son espacios)
CELULAR = re.compile(r"(?<!\d)(?<!\d )(?<!S/)(?<!S/ )(?<!\$)(?<!\$ )(?:\+?51[\s.-]?)?9\d{2}[\s.-]?\d{3}[\s.-]?\d{3}(?!\d)")
CORREO = re.compile(r"[A-Za-z0-9._%+-]+@((?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,})")
DOMINIOS_PERSONALES = ("gmail.", "googlemail.", "hotmail.", "outlook.", "live.", "msn.", "yahoo.",
                       "ymail.", "icloud.", "me.com", "mac.com", "aol.", "protonmail.", "proton.me",
                       "zoho.", "mail.com", "terra.", "speedy.")
# Claves cuyo valor NO es texto libre (URLs, RUC de empresa, códigos) → no se busca DNI ahí.
# `email` institucional puede llevar dígitos en el usuario (af42859392@…edu.pe): se evalúa solo
# con la regla de correo personal.
CLAVES_SIN_DNI = {"url", "fuente_url", "detalle_url", "ruc", "codigo", "norma", "ocid", "id", "email"}
# `telefono` se evalúa solo con la regla de celular (los fijos de 8 dígitos no son DNI).
CLAVES_TELEFONO = {"telefono", "tel", "phone"}
CLAVES_PROHIBIDAS = {"dni", "documento", "nro_documento", "num_documento"}


def parse_strict(path: Path):
    """json.loads que rechaza NaN/Infinity (inválidos en JSON estándar)."""
    def bad(c):
        raise ValueError(f"constante no estándar en JSON: {c}")
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=bad)


def correo_personal(s: str) -> bool:
    dominio = s.rsplit("@", 1)[1].lower()
    return any(dominio.startswith(d) or ("." + d) in dominio for d in DOMINIOS_PERSONALES)


def escanear_pii(obj, hallazgos: dict, ejemplos: list, archivo: str, clave: str = "") -> None:
    """Recorre el JSON; cuenta PII en cadenas (no en números)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in CLAVES_PROHIBIDAS and v not in (None, "", []):
                hallazgos["campo_dni"] += 1
                if len(ejemplos) < 12:
                    ejemplos.append(f"{archivo}: campo `{k}` publicado")
            escanear_pii(v, hallazgos, ejemplos, archivo, k.lower())
    elif isinstance(obj, list):
        for v in obj:
            escanear_pii(v, hallazgos, ejemplos, archivo, clave)
    elif isinstance(obj, (int, float)) and isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        hallazgos["nan"] += 1
    elif isinstance(obj, str):
        s = obj
        if s.startswith(("http://", "https://")):
            return
        if clave in CLAVES_TELEFONO:
            if CELULAR.search(s) or re.fullmatch(r"\D*(\+?51)?\D*9\d{7,8}\D*", s):
                hallazgos["celular"] += 1
                if len(ejemplos) < 12:
                    ejemplos.append(f"{archivo}: celular en `{clave}`: {s[:30]!r}")
            return
        n = len(RUC_NATURAL.findall(s))
        if n:
            hallazgos["ruc_natural"] += n
            if len(ejemplos) < 12:
                ejemplos.append(f"{archivo}: RUC 10… completo en `{clave}`: {s[:60]!r}")
        if clave not in CLAVES_SIN_DNI:
            n = len(DNI_SUELTO.findall(s))
            if n:
                hallazgos["dni8"] += n
                if len(ejemplos) < 12:
                    ejemplos.append(f"{archivo}: 8 dígitos sueltos en `{clave}`: {s[:60]!r}")
        for m in CORREO.finditer(s):
            if correo_personal(m.group(0)):
                hallazgos["correo_personal"] += 1
                if len(ejemplos) < 12:
                    ejemplos.append(f"{archivo}: correo personal en `{clave}`: {m.group(0)[:50]!r}")
        n = len(CELULAR.findall(s))
        if n:
            hallazgos["celular"] += n
            if len(ejemplos) < 12:
                ejemplos.append(f"{archivo}: celular en `{clave}`: {s[:60]!r}")


def ultimo_snapshot() -> Path | None:
    if not SNAPS.is_dir():
        return None
    dirs = sorted(d for d in SNAPS.iterdir() if d.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", d.name))
    return dirs[-1] if dirs else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--informe", action="store_true", help="imprime conteos PII por archivo")
    ap.add_argument("--data", default=str(DATA), help="carpeta de JSON publicados")
    args = ap.parse_args()
    data = Path(args.data)
    errores: list[str] = []
    avisos: list[str] = []

    if not data.is_dir():
        print(f"✖ no existe {data}")
        return 1

    # 1) JSON válido (todos los archivos) + 3) PII
    archivos = sorted(data.rglob("*.json"))
    cargados: dict[str, object] = {}
    pii_total = {"dni8": 0, "ruc_natural": 0, "correo_personal": 0, "celular": 0, "campo_dni": 0, "nan": 0}
    pii_por_archivo: dict[str, dict] = {}
    ejemplos: list[str] = []
    for p in archivos:
        rel = str(p.relative_to(data))
        try:
            d = parse_strict(p)
        except (ValueError, OSError) as exc:
            errores.append(f"JSON inválido {rel}: {exc}")
            continue
        if p.stat().st_size == 0 or d in ({}, [], None):
            errores.append(f"JSON vacío: {rel}")
        if p.parent == data or p.parent.name in ("sanciones", "dj", "entidad"):
            cargados[rel] = d
        h = {k: 0 for k in pii_total}
        escanear_pii(d, h, ejemplos, rel)
        if any(h.values()):
            pii_por_archivo[rel] = {k: v for k, v in h.items() if v}
            for k, v in h.items():
                pii_total[k] += v
    if any(pii_total.values()):
        errores.append("PII en JSON publicados: " + ", ".join(f"{k}={v}" for k, v in pii_total.items() if v))
        errores.extend("  · " + e for e in ejemplos)

    # 2) umbrales absolutos
    for nombre, desc, fn, minimo in UMBRALES:
        d = cargados.get(nombre)
        if d is None:
            errores.append(f"falta {nombre}")
            continue
        try:
            v = fn(d)
        except Exception as exc:  # noqa: BLE001
            errores.append(f"{nombre}: no se pudo leer {desc} ({exc})")
            continue
        if v < minimo:
            errores.append(f"{nombre}: {desc} = {v:,} < mínimo {minimo:,} (vacío/degradado)")
    personas = 0
    for p in sorted((data / "personas").glob("*.json")):
        d = cargados.get(f"personas/{p.name}")
        if d is None:
            try:
                d = parse_strict(p)
            except ValueError:
                continue
        personas += len(d.get("items", [])) if isinstance(d, dict) else 0
    if personas < MIN_PERSONAS:
        errores.append(f"personas/*.json: {personas:,} personas < mínimo {MIN_PERSONAS:,}")

    # 2a) valores de la planilla publicada (no solo conteos)
    items_pl = [x for n in ("funcionarios_sample.json", "funcionarios_clave.json")
                for x in (cargados.get(n) or {}).get("items", [])]
    if items_pl:
        numericos = sum(1 for x in items_pl if _num(x.get("total")))
        if numericos < len(items_pl) * MIN_NUMERICOS:
            errores.append(f"funcionarios_*.json: solo {numericos:,}/{len(items_pl):,} filas con total numérico "
                           f"(< {int(MIN_NUMERICOS * 100)} %)")
        sunat = sum(1 for x in items_pl if SUNAT_BOILERPLATE in (x.get("nombre") or "").lower())
        if sunat:
            errores.append(f"funcionarios_*.json: {sunat} nombres con texto incrustado de SUNAT")
    reg_tot = reg_276 = 0
    for rel, d in cargados.items():
        if rel.startswith("entidad/") and isinstance(d, dict):
            for reg, n in d.get("regimenes", []):
                reg_tot += n
                if RE_276_728.search(str(reg)):
                    reg_276 += n
    captura = str((cargados.get("meta.json") or {}).get("planilla_capturada") or "")[:10]
    if reg_tot and reg_276 < reg_tot * MIN_276_728:
        msg = (f"entidad/*.json: solo {reg_276:,}/{reg_tot:,} personas en régimen 276/728 "
               f"(< {MIN_276_728 * 100} %); planilla capturada {captura or '?'}")
        (errores if captura >= CONECTOR_CORREGIDO_DESDE else avisos).append(msg)

    # 2b) ≥ 70 % del último snapshot
    snap = ultimo_snapshot()
    if snap:
        for nombre, claves in SNAPSHOT_KEYS.items():
            prev_p, cur = snap / nombre, cargados.get(nombre)
            if not prev_p.exists() or cur is None:
                continue
            try:
                prev = parse_strict(prev_p)
            except ValueError:
                continue
            for desc, fn in claves:
                try:
                    a, b = fn(prev), fn(cur)
                except Exception:  # noqa: BLE001
                    continue
                if a and b < a * FRACCION_SNAPSHOT:
                    errores.append(f"{nombre}: {desc} cayó de {a:,} (snapshot {snap.name}) a {b:,} "
                                   f"(< {int(FRACCION_SNAPSHOT * 100)} %)")
    else:
        avisos.append("sin snapshots en data/historico/snapshots: no se comparó con el día anterior")

    # ───────── salida ─────────
    if args.informe:
        print("── PII por archivo ──")
        for rel, h in sorted(pii_por_archivo.items(), key=lambda x: -sum(x[1].values()))[:40]:
            print(f"  {rel}: {h}")
        print(f"  TOTAL: {pii_total} en {len(pii_por_archivo)} archivos")
    print(f"validar_publicacion: {len(archivos)} JSON · personas={personas:,} · snapshot={snap.name if snap else '—'}")
    for a in avisos:
        print(f"  ⚠ {a}")
    if errores:
        forzado = os.environ.get("PT_FORCE") == "1"
        print(("⚠ FORZADO con PT_FORCE=1, se publica igual:" if forzado else "✖ NO PUBLICAR:"), file=sys.stderr)
        for e in errores:
            print(f"  {e}", file=sys.stderr)
        return 0 if forzado else 1
    print("✔ publicación válida: JSON íntegros, sin regresión, sin PII")
    return 0


if __name__ == "__main__":
    sys.exit(main())
