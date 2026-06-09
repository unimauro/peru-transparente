"""Catálogo de entidades del Estado peruano desde el PTE.

El PTE lista TODAS las entidades por "poder/tipo" en:
    buscador/pte_transparencia_listado_entidades_poder.aspx?Tipo_Pod=N

Tipo_Pod observados: 1..7 (ejecutivo, organismos, gobiernos regionales/locales,
empresas, militares, etc.). Devuelve ~2,300 entidades con su id_entidad real.

Esto da el UNIVERSO sobre el que barrer funcionarios (los id_entidad son dispersos:
88, 107, 10041, 11794, 103006…, no contiguos).
"""
from __future__ import annotations

import html
import re

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

LISTADO = "https://www.transparencia.gob.pe/buscador/pte_transparencia_listado_entidades_poder.aspx"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

# Etiqueta legible de cada Tipo_Pod (aproximada según agrupación del PTE).
TIPO_POD = {
    1: "Poder Legislativo",
    2: "Poder Ejecutivo - Ministerios",
    3: "Organismos Públicos y OPD",
    4: "Organismos Constitucionales Autónomos",
    5: "Gobiernos Regionales y Locales",
    6: "Otros",
    7: "Empresas del Estado y diversos",
}


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, max=30))
def _get(client: httpx.Client, tipo: int) -> str:
    r = client.get(f"{LISTADO}?Tipo_Pod={tipo}")
    r.raise_for_status()
    return r.text


def fetch_catalogo() -> list[dict]:
    """Devuelve [{id_entidad, nombre, tipo_pod, tipo_label}] de todas las entidades."""
    out: dict[int, dict] = {}
    with httpx.Client(timeout=40, headers={"User-Agent": UA}, follow_redirects=True) as client:
        for tipo in range(1, 8):
            try:
                page = _get(client, tipo)
            except Exception:
                continue
            for eid, nombre in re.findall(r"id_entidad=(\d+)[^>]*>\s*([^<]{3,120})", page):
                nombre = html.unescape(re.sub(r"\s+", " ", nombre)).strip()
                if not nombre or nombre.lower().endswith(".png"):
                    continue
                eid = int(eid)
                if eid not in out:
                    out[eid] = {
                        "id_entidad": eid,
                        "nombre": nombre,
                        "tipo_pod": tipo,
                        "tipo_label": TIPO_POD.get(tipo, str(tipo)),
                    }
    return sorted(out.values(), key=lambda r: r["id_entidad"])


if __name__ == "__main__":
    cat = fetch_catalogo()
    print(f"entidades: {len(cat)}")
    for r in cat[:10]:
        print(r["id_entidad"], r["tipo_label"], r["nombre"][:60])
