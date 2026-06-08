"""Connector base: contrato común de ingesta (fetch/parse/diff/emit).

Cada connector concreto produce `IngestRecord`s normalizados. La detección de
cambios se hace por sha256 del payload; solo se emiten deltas. La procedencia es
obligatoria en cada registro.
"""
from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import datetime, timezone

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IngestRecord(BaseModel):
    """Contrato de ingesta: lo que todo connector debe emitir hacia staging.ingest."""
    source: str
    record_type: str            # 'entity' | 'person' | 'contract' | 'company' | ...
    natural_key: str | None     # ruc / ocid / etc. para dedupe
    payload: dict
    source_url: str | None = None
    captured_at: datetime = Field(default_factory=utcnow)
    confidence: float = 0.9
    method: str = "scrape"      # api | scrape | ocr

    @property
    def sha256(self) -> str:
        blob = json.dumps(self.payload, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class BaseConnector(ABC):
    source: str
    confidence: float = 0.9
    method: str = "scrape"

    @abstractmethod
    def fetch(self) -> Iterable[dict]:
        """Descarga RAW desde la fuente (API o scraping)."""

    @abstractmethod
    def parse(self, raw: dict) -> Iterable[IngestRecord]:
        """Convierte RAW en registros tipados del contrato de ingesta."""

    def run(self) -> Iterable[IngestRecord]:
        for raw in self.fetch():
            yield from self.parse(raw)
