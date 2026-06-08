# ADR-001 — PostgreSQL como fuente de verdad, Neo4j derivado

**Estado:** aceptado · **Fecha:** 2026-06

## Contexto
Necesitamos consultas relacionales/analíticas (dashboards, agregaciones, SCD2) y consultas de grafo (rutas de poder, vecindarios). Ninguna base sirve bien a ambas a escala.

## Decisión
PostgreSQL es la **fuente de verdad canónica**. Neo4j es una **proyección derivada** (vía CDC/batch) optimizada para exploración de redes. El grafo se puede reconstruir 100% desde Postgres.

## Consecuencias
- (+) Integridad, transacciones, analytics y pgvector en un solo lugar.
- (+) El grafo es desechable/recomputable; sin riesgo de divergencia de verdad.
- (−) Mantener la sincronización Postgres→Neo4j (mitigado con `MERGE` idempotente).
