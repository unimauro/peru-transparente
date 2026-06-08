"""Connector OSCE/OECE — Contrataciones Abiertas (estándar OCDS).

Fuente: https://contratacionesabiertas.oece.gob.pe/api/v1
Trae releases OCDS (procesos, adjudicaciones, contratos y proveedores).
Es la fuente de mayor confianza (API estructurada → confidence 1.0).
"""
from __future__ import annotations

from collections.abc import Iterable

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from peru_transparente.base import BaseConnector, IngestRecord

BASE = "https://contratacionesabiertas.oece.gob.pe/api/v1"


class OsceOcdsConnector(BaseConnector):
    source = "OSCE_OCDS"
    confidence = 1.0
    method = "api"

    def __init__(self, page_size: int = 100, max_pages: int | None = None):
        self.page_size = page_size
        self.max_pages = max_pages

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, max=30))
    def _get(self, url: str, params: dict) -> dict:
        headers = {"User-Agent": "PeruTransparente/1.0 (+https://github.com/unimauro/peru-transparente)"}
        with httpx.Client(timeout=60, headers=headers) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()

    def fetch(self) -> Iterable[dict]:
        page = 1
        while True:
            data = self._get(f"{BASE}/releases", {"page": page, "pageSize": self.page_size})
            releases = data.get("releases", [])
            if not releases:
                break
            for rel in releases:
                yield rel
            page += 1
            if self.max_pages and page > self.max_pages:
                break

    def parse(self, raw: dict) -> Iterable[IngestRecord]:
        ocid = raw.get("ocid")
        buyer = (raw.get("buyer") or {})
        awards = raw.get("awards") or []
        contracts = raw.get("contracts") or []

        # Proveedores adjudicados
        for award in awards:
            for sup in award.get("suppliers", []):
                yield IngestRecord(
                    source=self.source, record_type="supplier",
                    natural_key=sup.get("id"),
                    payload={"ruc": sup.get("id"), "name": sup.get("name")},
                    source_url=f"https://contratacionesabiertas.oece.gob.pe/perfiles/{ocid}",
                    confidence=self.confidence, method=self.method,
                )

        # Contratos
        for c in contracts:
            value = c.get("value") or {}
            yield IngestRecord(
                source=self.source, record_type="contract",
                natural_key=ocid,
                payload={
                    "ocid": ocid,
                    "buyer_name": buyer.get("name"),
                    "buyer_ruc": (buyer.get("id") or "").replace("PE-RUC-", ""),
                    "title": c.get("title") or (raw.get("tender") or {}).get("title"),
                    "amount": value.get("amount"),
                    "currency": value.get("currency", "PEN"),
                    "sign_date": c.get("dateSigned"),
                    "process_type": (raw.get("tender") or {}).get("procurementMethod"),
                },
                source_url=f"https://contratacionesabiertas.oece.gob.pe/perfiles/{ocid}",
                confidence=self.confidence, method=self.method,
            )


if __name__ == "__main__":  # smoke run acotado
    conn = OsceOcdsConnector(max_pages=1)
    for i, rec in enumerate(conn.run()):
        print(rec.record_type, rec.natural_key, rec.sha256[:8])
        if i > 20:
            break
