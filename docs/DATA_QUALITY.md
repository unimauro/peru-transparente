# Calidad de datos, trazabilidad y confianza

## 1. Procedencia obligatoria (provenance)
Ningún registro `core.*` se publica sin al menos una fila en `meta.provenance`. Cada campo crítico puede tener su propia procedencia (a nivel de columna). El frontend **siempre** muestra: fuente, URL original, fecha de captura, fecha de actualización y nivel de confianza.

## 2. Pipeline de validación
Se usa **Great Expectations** (o checks Pydantic + asserts) en la etapa `validate`:
- Tipos y formatos (RUC 11 dígitos, fechas válidas, montos ≥ 0).
- Integridad referencial (un appointment apunta a entity/person existentes).
- Rangos plausibles (remuneración dentro de bandas del régimen).
- Unicidad y no-duplicación (entity por RUC, contract por OCID).
- Registros que fallan → **cuarentena** (`staging.quarantine`), no entran al canónico.

## 3. Entity Resolution (deduplicación de personas/entidades)
Problema central: la misma persona aparece como "Juan Pérez", "Juan A. Pérez García", "PEREZ GARCIA, JUAN". Estrategia:
1. **Normalización**: mayúsculas, sin tildes, orden de apellidos, limpieza de cargos.
2. **Blocking**: agrupar candidatos por bloques (iniciales + soundex/metaphone, DNI parcial si público).
3. **Scoring**: RapidFuzz (Jaro-Winkler/token-set) + similitud de embeddings.
4. **Árbitro IA**: en casos límite, un LLM compara contextos (entidades, fechas) y decide, con confianza.
5. **Clave canónica**: se asigna `canonical_key`; las variaciones se enlazan, no se borran (auditable y reversible).
Toda fusión queda registrada en `meta.entity_merge` con evidencia.

## 4. Niveles de confianza
| Confianza | Origen |
|---|---|
| 1.00 | API oficial estructurada (OCDS, SIAF, CKAN) |
| 0.90 | Scrape de portal oficial, parser estable |
| 0.75 | Extracción de PDF oficial (OCR/regex) |
| 0.60 | Inferencia/resolución por IA |
| <0.50 | Cuarentena — revisión humana |

## 5. Anti-overclaiming (regla de oro)
- Las relaciones inferidas (conflictos de interés, vínculos entre personas) se etiquetan `POSSIBLE_*` con `confidence` y `evidence`.
- La UI las muestra con lenguaje de hipótesis ("posible vínculo", "a verificar") y nunca como hecho probado.
- Se separa visualmente *dato verificado* (de fuente) de *inferencia* (de IA).

## 6. Corrección y participación comunitaria
- Botón "reportar dato" en cada registro → issue/PR con la corrección y su fuente.
- Cola de revisión humana para cuarentena y disputas.
- Historial de correcciones público (todo cambio es auditable).

## 7. Monitoreo de calidad
- Dashboard público de cobertura: % de entidades con presupuesto, % de funcionarios con resolución, distribución de confianza.
- Métricas por corrida de scraper (`meta.scrape_run`).
- Detección de regresiones: si un parser produce 0 registros donde antes producía miles → alerta.
