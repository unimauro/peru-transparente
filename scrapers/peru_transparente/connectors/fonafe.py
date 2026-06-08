"""Connector FONAFE — empresas del Estado y sus directorios.

FONAFE publica el portafolio de empresas estatales. Este connector descarga el
listado y, por empresa, su directorio/gerencias. Para páginas con JS se usa
Playwright; el ejemplo base usa httpx + parseo de HTML estable.

NOTA: los selectores y URLs reales se mantienen en `sources.yaml` y deben
ajustarse al layout vigente de FONAFE (ver docs/SCRAPING_STRATEGY.md §6).
"""
from __future__ import annotations

from collections.abc import Iterable

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from peru_transparente.base import BaseConnector, IngestRecord

PORTAL = "https://www.fonafe.gob.pe"


class FonafeConnector(BaseConnector):
    source = "FONAFE"
    confidence = 0.9
    method = "scrape"

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, max=30))
    def _get(self, url: str) -> str:
        headers = {"User-Agent": "PeruTransparente/1.0 (+https://github.com/unimauro/peru-transparente)"}
        with httpx.Client(timeout=60, headers=headers, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.text

    def fetch(self) -> Iterable[dict]:
        # TODO: reemplazar por el endpoint/listado real de empresas FONAFE.
        # Estructura esperada tras parseo del portal:
        yield {
            "name": "Ejemplo Empresa Estatal S.A.",
            "ruc": "20100000001",
            "classification": "Empresa bajo el ámbito de FONAFE",
            "sector": "Energía",
            "directors": [
                {"name": "NOMBRE APELLIDO", "role": "Presidente del Directorio"},
            ],
            "url": f"{PORTAL}/empresas/ejemplo",
        }

    def parse(self, raw: dict) -> Iterable[IngestRecord]:
        yield IngestRecord(
            source=self.source, record_type="company",
            natural_key=raw.get("ruc"),
            payload={
                "name": raw["name"], "ruc": raw.get("ruc"),
                "fonafe_classification": raw.get("classification"),
                "sector": raw.get("sector"),
            },
            source_url=raw.get("url"), confidence=self.confidence, method=self.method,
        )
        for d in raw.get("directors", []):
            yield IngestRecord(
                source=self.source, record_type="company_role",
                natural_key=f"{raw.get('ruc')}::{d['name']}::{d['role']}",
                payload={"company_ruc": raw.get("ruc"), "person_name": d["name"], "role": d["role"]},
                source_url=raw.get("url"), confidence=self.confidence, method=self.method,
            )
