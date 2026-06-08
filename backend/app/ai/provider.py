"""Interfaz de proveedor LLM intercambiable (Claude / OpenAI / Gemini).

La capa de IA se usa para: resolución de entidades (árbitro), resúmenes de perfil
con *grounding* estricto y embeddings para búsqueda semántica. Toda salida que
infiera vínculos debe etiquetarse como hipótesis (anti-overclaiming).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.config import get_settings

settings = get_settings()


class LLMProvider(ABC):
    @abstractmethod
    async def summarize(self, prompt: str, *, grounding: str) -> str:
        """Genera un resumen anclado SOLO a `grounding` (datos verificados)."""

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Devuelve el embedding del texto para búsqueda semántica."""


class ClaudeProvider(LLMProvider):
    """Proveedor por defecto. Modelo recomendado: claude-opus-4-8 / claude-sonnet-4-6."""

    model = "claude-sonnet-4-6"

    async def summarize(self, prompt: str, *, grounding: str) -> str:
        from anthropic import AsyncAnthropic  # import diferido

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        system = (
            "Eres un asistente de transparencia pública. Resume USANDO EXCLUSIVAMENTE "
            "los datos proporcionados. No inventes ni infieras irregularidades. "
            "Si un dato no está, dilo. Cita la fuente cuando exista."
        )
        msg = await client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": f"DATOS:\n{grounding}\n\nTAREA:\n{prompt}"}],
        )
        return "".join(b.text for b in msg.content if b.type == "text")

    async def embed(self, text: str) -> list[float]:  # pragma: no cover
        raise NotImplementedError("Usar un proveedor de embeddings dedicado (p. ej. OpenAI/Voyage).")


def get_provider() -> LLMProvider:
    # Punto de extensión: registrar OpenAIProvider / GeminiProvider aquí.
    return ClaudeProvider()
