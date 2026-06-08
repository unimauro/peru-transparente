# Estrategia de scraping y actualización

## 1. Modelo de connector

Todo connector hereda de `BaseConnector` y expone:

```
fetch()  → descarga RAW (HTML/PDF/JSON) y lo guarda inmutable con hash + timestamp
parse()  → convierte RAW en registros Pydantic tipados (contrato de ingesta)
diff()   → compara contra el último snapshot; emite solo deltas (nuevo/cambiado/eliminado)
emit()   → escribe a staging + registra provenance
```

Familias:
- **API connectors** (preferidos): OCDS OSCE/OECE, Datos Abiertos (CKAN), MEF SIAF/Consulta Amigable, BCRP (API estadística).
- **Scraping connectors**: PTE, Contraloría, FONAFE, portales institucionales — Scrapy para HTML estable, **Playwright** para JS pesado / formularios.

## 2. Catálogo de fuentes y método

| Fuente | Método | Frecuencia | Dato |
|---|---|---|---|
| OSCE/OECE (contratacionesabiertas.oece.gob.pe) | API OCDS | Diaria | Contratos, proveedores |
| Datos Abiertos (datosabiertos.gob.pe) | API CKAN | Semanal | Catálogo entidades, datasets |
| FONAFE | Scrapy/Playwright | Semanal | Empresas, directorios |
| Portal de Transparencia Estándar | Playwright | Diaria | Funcionarios, remuneraciones, organigrama |
| Contraloría | Playwright + OCR PDF | Mensual | Declaraciones juradas |
| MEF Consulta Amigable / SIAF | API/scrape | Mensual | Presupuestos PIA/PIM/devengado |
| SERVIR | Scrapy | Mensual | Régimen laboral, planillas |
| Congreso / JNE / ONPE | API/scrape | Según evento | Autoridades, hojas de vida |
| Poder Judicial / Min. Público | Scrapy | Mensual | Autoridades públicas |
| SMV / SBS / BCRP | API | Mensual | Datos financieros públicos |

> El estado real de cada fuente (URL, robots.txt, formato, estabilidad) se versiona en `scrapers/peru_transparente/sources.yaml`.

## 3. Buenas prácticas y ética de scraping
- Respetar `robots.txt` y términos de uso; identificarse con User-Agent honesto (`PeruTransparente/1.0 (+repo)`).
- Rate-limit y backoff exponencial; concurrencia conservadora.
- Cache de RAW: no re-descargar lo que no cambió (ETag / Last-Modified / hash).
- Reintentos con jitter; circuit breaker si la fuente cae.
- Logs estructurados por corrida en `meta.scrape_run` (registros nuevos/cambiados/fallidos, duración, errores).
- Preferir **descargas masivas/datasets oficiales** sobre scraping página a página cuando existan.

## 4. Detección de cambios y versionado histórico
- Cada `fetch()` guarda RAW con `sha256`. Si el hash coincide con el último, se omite el parse.
- `diff()` produce eventos de cambio → alimenta el historial SCD2 (un cese o un cambio de remuneración crea una nueva versión, no sobreescribe).
- Snapshots RAW se conservan (R2/Releases) para auditoría y reproceso.

## 5. Actualización diaria (orquestación)
- **GitHub Actions cron** dispara los DAGs diarios (OCDS, PTE).
- Pipeline: `extract → validate → resolve → upsert → project_graph → build_static → commit data/public`.
- Si hay deltas, el build estático se *commitea* a `data/public/` y Pages se redespliega solo.
- DAGs semanales/mensuales para fuentes menos volátiles.
- Backfill histórico: comando `pt-etl backfill --source osce --from 2017-01-01`.

## 6. Resiliencia
- Cada fuente es independiente: si una cae, las demás siguen.
- Cuarentena para registros que fallan validación; no contaminan el canónico.
- Issue automático cuando un parser deja de producir registros (señal de cambio de layout en la fuente).
