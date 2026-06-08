"""Schemas Pydantic compartidos, incluyendo el envoltorio de procedencia."""
from datetime import datetime

from pydantic import BaseModel, Field


class Provenance(BaseModel):
    source: str
    source_url: str | None = None
    captured_at: datetime
    updated_at: datetime | None = None
    confidence: float = Field(ge=0, le=1)
    method: str | None = None


class WithProvenance(BaseModel):
    """Todo recurso público expone su procedencia (regla de trazabilidad)."""
    provenance: list[Provenance] = []


class GraphNode(BaseModel):
    id: str
    label: str
    name: str | None = None
    confidence: float | None = None


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str
    hypothesis: bool = False


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
