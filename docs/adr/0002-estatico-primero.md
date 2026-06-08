# ADR-002 — Estático-primero para servir desde GitHub Pages

**Estado:** aceptado · **Fecha:** 2026-06

## Contexto
El requisito es que el frontend funcione **completamente desde GitHub Pages** y el costo de backend sea gratuito o muy bajo, soportando tráfico de lectura potencialmente alto.

## Decisión
El pipeline genera **JSON estático** (listados, perfiles, KPIs, datasets por región) que se commitea a `frontend/public/data/` y se publica con el SPA. El backend dinámico (FastAPI) solo atiende: grafo en vivo, búsqueda semántica y exportaciones grandes.

## Consecuencias
- (+) ~90% del tráfico se sirve por Pages + CDN: costo ~US$0 y alta disponibilidad.
- (+) Datos versionados y auditables (cada deploy es un snapshot).
- (−) Latencia de actualización = cadencia del cron (aceptable para datos de transparencia).
- (−) Tamaño del repo crece; mitigado publicando datasets grandes en Releases/R2.
