# Modelo de datos — Perú Transparente

PostgreSQL es la **fuente de verdad**. Tres esquemas lógicos:

- `staging` — registros crudos tipados que llegan de los connectors (efímeros, re-creables).
- `core` — entidades canónicas historizadas (SCD2).
- `meta` — procedencia (provenance) a nivel de campo y registro.
- `analytics` — vistas materializadas para dashboards.

## 1. Diagrama entidad-relación (canónico)

```
            ┌─────────────┐        ┌──────────────┐
            │  sector     │1      *│   entity     │*      1┌────────────┐
            │             │────────│ (entidad)    │────────│ entity_type│
            └─────────────┘        └──────┬───────┘        └────────────┘
                                          │1
                                          │
                   ┌──────────────────────┼───────────────────────┐
                  *│                      *│                       *│
            ┌──────┴──────┐        ┌───────┴───────┐        ┌───────┴────────┐
            │ appointment │*      1│    position    │        │ budget_line    │
            │ (designación)────────│ (cargo)        │        │ (presupuesto)  │
            └──────┬──────┘        └────────────────┘        └────────────────┘
                  *│
                  1│
            ┌──────┴──────┐                              ┌──────────────────┐
            │   person    │1                            *│ asset_declaration │
            │ (persona)   │──────────────────────────────│ (declaración jur.)│
            └──────┬──────┘                               └──────────────────┘
                   │1
          ┌────────┼─────────┐
         *│                  *│
   ┌──────┴──────┐    ┌───────┴────────┐         ┌──────────────┐      ┌────────────┐
   │ company_role │    │  contract       │*      1│  supplier    │      │  contract  │
   │ (empresa rol)│    │ (contrato OSCE) │────────│ (proveedor)  │      │   _award   │
   └──────┬───────┘    └───────┬─────────┘        └──────────────┘      └────────────┘
         *│                   *│
          │1                   │1
   ┌──────┴──────┐      (entity contratante)
   │ company     │
   │ (empresa    │
   │  estatal)   │
   └─────────────┘
```

## 2. Tablas principales (resumen)

### `core.entity` — Entidad pública
| Campo | Tipo | Nota |
|---|---|---|
| id | uuid PK | |
| ruc | varchar(11) | clave natural cuando existe |
| name | text | nombre oficial |
| acronym | text | sigla |
| entity_type_id | fk | ministerio, OPD, GR, municipalidad, empresa, organismo constitucional… |
| sector_id | fk | |
| level | enum | nacional / regional / local |
| ubigeo | char(6) | INEI |
| website | text | portal institucional |
| transparency_url | text | portal de transparencia estándar |
| parent_entity_id | fk self | jerarquía (organigrama sectorial/nacional) |
| valid_from / valid_to | tstzrange | SCD2 |

### `core.person` — Persona
| id uuid PK · full_name · normalized_name · doc_type · doc_number_public (solo si la fuente lo publica) · birth_year? · canonical_key |
Nota: `canonical_key` lo asigna Entity Resolution; agrupa variaciones del mismo individuo.

### `core.position` — Cargo
| id · entity_id fk · title · normalized_title · hierarchy_level (1=titular … n) · regime (DL276/728/CAS/FAG/confianza) · is_confianza bool |

### `core.appointment` — Designación / nombramiento (SCD2, el corazón del historial)
| id · person_id · position_id · entity_id · start_date · end_date? · appointment_resolution (nº + url) · cessation_resolution? · remuneration_amount? · remuneration_currency · status (vigente/cesado/encargatura/rotación) |

### `core.asset_declaration` — Declaración Jurada
| id · person_id · entity_id · period · presented_at · assets_total? · income_total? · interests (jsonb) · source_url · raw_pdf_ref |
Sub-tabla `core.declaration_item` para bienes/rentas/intereses individuales y su evolución histórica.

### `core.company` — Empresa del Estado (FONAFE)
| id · entity_id fk · fonafe_classification · sector · directors (vía company_role) · financials_ref |
`core.company_role` liga `person ↔ company` con rol (director, gerente general, etc.) y vigencia.

### `core.budget_line` — Presupuesto
| id · entity_id · fiscal_year · pia · pim · devengado · source (MEF Consulta Amigable/SIAF) |

### `core.contract` + `core.supplier` — Contrataciones (OSCE/OECE, OCDS)
| contract: id · ocid · entity_id (contratante) · supplier_id · title · amount · currency · sign_date · process_type |
| supplier: id · ruc · name · is_state_owned bool · risk_flags jsonb |

### `meta.provenance` — Procedencia (1:N contra cualquier registro)
| id · target_table · target_id · field? · source · source_url · captured_at · updated_at · confidence (0–1) · method (api/scrape/manual) · raw_ref |
**Regla:** ningún `core.*` se publica sin al menos una fila de provenance.

## 3. Historización (SCD2)
`appointment`, `position`, `entity` y `budget_line` usan rangos `tstzrange` + columna `is_current`. Esto permite reconstruir "¿quién era ministro de X el 2021-07-28?" y graficar rotaciones/ceses.

## 4. Diccionario de datos
Diccionario completo campo a campo en `db/postgres/DATA_DICTIONARY.md` (generado desde los comentarios `COMMENT ON COLUMN`).

## 5. Niveles de confianza (`confidence`)
| Valor | Significado |
|---|---|
| 1.00 | Dato de API oficial estructurada (OCDS, SIAF) |
| 0.90 | Scrape de portal oficial con parser estable |
| 0.75 | Extraído de PDF oficial (OCR/regex) |
| 0.60 | Resuelto/inferido por IA (entity resolution) |
| < 0.5 | Cuarentena — no se publica, requiere revisión humana |

## 6. Serie histórica diaria

Serie temporal de las cifras agregadas del portal, para graficar cómo se mueven en el tiempo. La genera `scripts/snapshot_historico.py` (solo stdlib) al final de cada corrida de `actualizar.sh`; también admite `--fecha YYYY-MM-DD` para forzar la fecha y `--backfill` para reconstruirla desde el historial git (`git log HEAD -- frontend/public/data`, último commit de cada día, filas con `funcionarios` vacío o 0 se descartan).

### `data/historico/serie_diaria.csv` — una fila por fecha (UPSERT, orden ascendente)
| Columna | Origen (`frontend/public/data/`) |
|---|---|
| `fecha` | YYYY-MM-DD del snapshot (o del commit en backfill) |
| `funcionarios` | `national_kpis.json → total_funcionarios` |
| `entidades_con_datos` | `national_kpis.json → entities_with_data` |
| `cargos_clave` | `national_kpis.json → total_cargos_clave` |
| `contratos_n` | `contratos.json → resumen.n_adjudicaciones` (fallback `_meta`) |
| `contratos_monto` | `contratos.json → resumen.monto_total` (S/, adjudicado) |
| `ordenes_n` | `ordenes_servicio.json → total_ordenes` |
| `ordenes_monto` | `ordenes_servicio.json → monto_total` (S/) |
| `designaciones_total` | `nuevos_funcionarios.json → total` |
| `designaciones_oficiales` | `nuevos_funcionarios.json → oficiales` |
| `sanciones_n` | `sanciones.json → total_sanciones` |
| `dj_n` | `dj.json → total_declaraciones` |
| `autoridades_n` | `autoridades.json → len(items)` |

Celda vacía = el archivo o la clave no existía ese día (`null` en el JSON). Cabecera fija en ese orden.

### `data/historico/snapshots/YYYY-MM-DD/` — copia cruda del día
Copia de `national_kpis.json`, `meta.json`, `contratos.json`, `sanciones.json`, `dj.json` y `bot_context.json` tal como se publicaron ese día. Los archivos > 1 MB no se copian. Sirve para auditar una cifra puntual de la serie o recalcular métricas nuevas hacia atrás sin pasar por git.

### `frontend/public/data/historico_serie.json` — contrato para el front
```json
{
  "generated_at": "2026-10-24T22:21:00+00:00",
  "campos": {"funcionarios": "Servidores públicos nominales (PTE)", "...": "etiqueta en español por métrica"},
  "serie": [
    {"fecha": "2026-06-09", "funcionarios": 213101, "entidades_con_datos": 646, "cargos_clave": 9448,
     "contratos_n": null, "contratos_monto": null, "ordenes_n": null, "ordenes_monto": null,
     "designaciones_total": null, "designaciones_oficiales": null, "sanciones_n": null, "dj_n": null,
     "autoridades_n": 5637}
  ]
}
```
`serie` va ordenada ascendente por `fecha`; los valores son enteros/float o `null`. `campos` trae la etiqueta de cada métrica para leyendas y tooltips. Se regenera completo en cada corrida a partir del CSV.
