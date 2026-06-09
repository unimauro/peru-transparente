"""Connector gob.pe — Directorio de funcionarios/autoridades por institución.

Fuente: https://www.gob.pe/institucion/<slug>/funcionarios
Complementa al PTE: trae a las AUTORIDADES (rector, vicerrectores, ministros,
jefes, gerentes, directores) con su cargo, correo y teléfono institucional —
justo lo que muchas entidades NO publican en el rubro Personal del PTE.

Devuelve registros (nombre, cargo, email, telefono, detalle_url) por institución.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"


@dataclass
class Autoridad:
    slug: str
    institucion: str
    nombre: str
    cargo: str
    email: str
    telefono: str
    detalle_url: str
    fuente_url: str
    captured_at: str


def _strip(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


class GobpeDirectorioConnector:
    source = "GOBPE_DIRECTORIO"

    def __init__(self, timeout: float = 30.0):
        self._client = httpx.Client(
            timeout=timeout, headers={"User-Agent": UA}, follow_redirects=True, verify=False
        )

    def close(self) -> None:
        self._client.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=20))
    def _get(self, slug: str) -> httpx.Response:
        return self._client.get(f"https://www.gob.pe/institucion/{slug}/funcionarios")

    def fetch(self, slug: str) -> list[Autoridad]:
        try:
            r = self._get(slug)
        except Exception:
            return []
        if r.status_code != 200:
            return []
        t = r.text
        url = f"https://www.gob.pe/institucion/{slug}/funcionarios"
        # nombre de la institución (title) para etiquetar
        mt = re.search(r"<title>([^<|]+)", t)
        inst = _strip(mt.group(1)) if mt else slug

        out: list[Autoridad] = []
        # Cada autoridad: <a class="institution__higher-official-name" href="…/funcionarios/ID">NOMBRE</a>
        # seguido del cargo (siguiente texto). Partimos por ese anchor.
        parts = re.split(r'institution__higher-official-name', t)
        for seg in parts[1:]:
            mh = re.search(
                r'href="([^"]*funcionarios/[^"]+)"[^>]*>\s*<h3[^>]*>(.*?)</h3>\s*</a>\s*<p>(.*?)</p>',
                seg, re.S,
            )
            if not mh:
                continue
            detalle = "https://www.gob.pe" + html.unescape(mh.group(1))
            nombre = _strip(mh.group(2))
            cargo = _strip(mh.group(3))
            tail = seg[:1500]
            email = ""
            em = re.search(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", tail, re.I)
            if em:
                email = em.group(0)
            tel = ""
            tm = re.search(r"\(?\d{2,3}\)?[\s-]?\d{3,4}[\s-]?\d{3,4}", tail)
            if tm:
                tel = tm.group(0).strip()
            if nombre and len(nombre) > 4:
                out.append(Autoridad(
                    slug=slug, institucion=inst, nombre=nombre, cargo=cargo,
                    email=email, telefono=tel, detalle_url=detalle, fuente_url=url,
                    captured_at=datetime.now(timezone.utc).isoformat(),
                ))
        return out


if __name__ == "__main__":
    c = GobpeDirectorioConnector()
    for slug in ["uni", "minam", "sunat"]:
        rows = c.fetch(slug)
        print(f"\n=== {slug}: {len(rows)} autoridades ===")
        for a in rows[:6]:
            print(f"  {a.cargo[:34]:34} | {a.nombre[:28]:28} | {a.email}")
    c.close()
