# Roadmap — 12 meses

Cada trimestre cierra con un release navegable y datos publicados. Las fuentes se priorizan por **valor/esfuerzo**: primero las que ya exponen API (OCDS, Datos Abiertos) y los portales con HTML estable.

## Q1 (Meses 1–3) — Fundaciones + MVP
- [ ] Monorepo, CI/CD, Docker Compose, esquemas Postgres + Neo4j.
- [ ] Connectors: **FONAFE** (empresas + directorios), **OSCE/OECE OCDS** (contratos), **Datos Abiertos** (catálogo de entidades).
- [ ] Entity Resolution v1 (reglas + fuzzy).
- [ ] API REST v1: entidades, funcionarios, empresas, contratos, búsqueda básica.
- [ ] Frontend: directorio de entidades, perfil de entidad, perfil de funcionario, grafo básico (Cytoscape).
- [ ] **MVP de 90 días** publicado en GitHub Pages (ver `MVP_90_DIAS.md`).

## Q2 (Meses 4–6) — Funcionarios y designaciones a escala
- [ ] Connector **Portal de Transparencia Estándar (PTE)**: funcionarios, remuneraciones, organigramas.
- [ ] Connector **MEF Consulta Amigable / SIAF**: presupuestos PIA/PIM/devengado por entidad.
- [ ] Dashboards: Ejecutivo Nacional, Funcionarios, Salarial, Designaciones.
- [ ] Organigramas automáticos (institucional + sectorial) con D3.
- [ ] SCD2 completo: historial de cargos y rotaciones.
- [ ] Búsqueda semántica (pgvector) + perfiles auto-generados (IA con grounding).

## Q3 (Meses 7–9) — Declaraciones, grafo profundo e IA
- [ ] Connector **Contraloría**: declaraciones juradas (bienes/rentas/intereses) + evolución histórica.
- [ ] Connector **SMV / SBS / BCRP** (datos financieros públicos).
- [ ] Link Detection v2: personas repetidas, variaciones de nombre, co-ocurrencias, *posibles* conflictos de interés (hipótesis con confianza).
- [ ] Grafo de poder completo navegable (rutas, vecindarios, centralidad).
- [ ] GraphQL API pública.
- [ ] Dashboard de Contrataciones (por entidad/proveedor/región).

## Q4 (Meses 10–12) — Cobertura nacional + ecosistema
- [ ] Connectors **Gobiernos Regionales y Municipalidades** (cobertura territorial vía ubigeo).
- [ ] Connectors **Congreso, JNE, Poder Judicial, Ministerio Público** (datos públicos).
- [ ] API de exportación masiva (CSV/JSON/Parquet) + datasets en datosabiertos.
- [ ] Alertas (suscripción a cambios de un funcionario/entidad).
- [ ] Programa de contribución open data (validación comunitaria, correcciones).
- [ ] Auditoría de calidad de datos pública (dashboard de cobertura y confianza).

## Métricas de éxito a 12 meses
- ≥ 100,000 funcionarios indexados con historial.
- ≥ todas las entidades del sector público nacional + regional.
- Millones de registros históricos de contratos (OCDS desde 2017+).
- Cobertura ≥ 80% de entidades con presupuesto vinculado.
- Trazabilidad 100%: ningún dato sin fuente.
