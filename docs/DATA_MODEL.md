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

## Costo del Estado en personal

Sección "¿Cuánto cuesta el Estado en personal?" (contador de años + costo mensual en todas sus variantes). Tres scripts y cuatro salidas; todo con fuente y período por cifra, `null` donde no hay dato.

### `scrapers/scrape_mef_personal.py` → `data/mef_personal_anual.csv`
Fuente: **Consulta Amigable del MEF** (`https://apps5.mineco.gob.pe/transparencia/Navegador/`), nivel nacional (Gobierno Nacional + Regional + Local), Actividades + Proyectos, soles corrientes. El API de datos abiertos del MEF (`api.datosabiertos.mef.gob.pe/.../datastore_search_sql`) devolvía 404 el 26-oct-2026, por eso se scrapea el navegador ASP.NET (cookie jar vía `default.aspx` por el WAF Incapsula, luego `Navegar.aspx?y=AÑO&ap=ActProy` y postbacks con `__VIEWSTATE`/`__EVENTVALIDATION`; botón `BtnGenerica` y, con `--detalle`, `BtnSubGenerica` → `BtnSubGenericaDetalle`). Cada fila de la tabla `ctl00_CPH1_Mt0` trae un radio `grp1` cuyo `value` codifica `codigo/PIA/PIM/CompromisoAnual/CompromisoMensual/Devengado/Girado/Certificación` (orden validado contra el `aria-label` cuando existe; 2015 no lo trae). Chequeo de consistencia: la suma de devengado por genérica debe cuadrar con el TOTAL del año (±0,5 %); se usa devengado y no PIM porque "Reserva de contingencia" a veces no trae radio parseable.

Columnas: `anio,generica,pia,pim,devengado,total_pim_anio,total_devengado_anio,capturado_en,fuente_url`. Una fila por año y concepto:

| `generica` | Qué es |
|---|---|
| `2.1 PERSONAL Y OBLIGACIONES SOCIALES` | genérica 2.1 |
| `2.2 PENSIONES Y OTRAS PRESTACIONES SOCIALES` | genérica 2.2 |
| `2.3.2.7 SERVICIOS PROFESIONALES Y TECNICOS` | específica dentro de 2.3 (incluye empresas) |
| `2.3.2.8 CONTRATO ADMINISTRATIVO DE SERVICIOS (dentro de 2.3, hasta 2023)` | CAS hasta 2023 |
| `2.3.2.9 LOCACION DE SERVICIOS REALIZADOS POR PERSONA NATURAL` | honorarios de locadores (la específica existe desde 2021) |
| `2.1.1.13 CONTRATO ADMINISTRATIVO DE SERVICIOS (dentro de 2.1, desde 2024)` | CAS desde 2024 |

`total_*_anio` = presupuesto público total del año (todas las genéricas). Reanudable: salta los años ya presentes (`--force` para rehacer). Si un año falla tras los reintentos, no aparece en el CSV y el script sale con código 2.

**Quiebre de serie 2024.** Con la Ley 31953 (Presupuesto 2024) y el Clasificador Económico de Gastos 2024 (Anexo II), el CAS pasó de 2.3 "Bienes y servicios" (2.3.2.8) a 2.1 "Personal y obligaciones sociales" (2.1.1.13). En la Consulta Amigable, 2.3 devengado pasa de S/ 50,4 mil M (2023) a S/ 39,0 mil M (2024) mientras 2.1 sube de S/ 58,9 a S/ 79,2 mil M; el CAS devengado fue S/ 13,1 mil M en 2023 y S/ 12,5 mil M en 2024. La serie comparable es **`personal_incl_cas`** = 2.1 + 2.3.2.8 hasta 2023 y = 2.1 desde 2024 (`quiebre_cas: true` en 2024).

### `scripts/procesar_airhsp.py` → `data/airhsp_*.csv`, `data/airhsp_resumen.json`, `frontend/public/data/airhsp.json`, `data/airhsp_headcount_anual.csv`
Fuente: dataset **"Personal activo y pensionista del sector público registrado en el AIRHSP"** (datosabiertos.gob.pe/MEF; `fs.datosabiertos.mef.gob.pe/datastorefiles/PERSONALSP_AAAA.csv`, ~600 MB/año, en `~/salariosperu-data/mef_airhsp/`). Cobertura: Gobierno Nacional y Regional; **sin municipalidades, EsSalud, FONAFE, BCRP, SBS ni SUNAT**. Un registro por plaza o pensión, agregado por unidad ejecutora × régimen × cargo (columna `CANTIDAD`).

**Hallazgo (revisión adversarial 26-oct-2026):** el "total" de 2 722 207 registros (dic-2025) **no es headcount**: mezcla activos con pensionistas y sobrevivientes, modalidad formativa y plazas vacantes. El script separa por `DESC_TIPO_REGISTRO` y `ESTADO_REGISTRO`:

| Grupo | `DESC_TIPO_REGISTRO` | Dic-2025 |
|---|---|---|
| `activos` | Activos, Contrato Administrativo de Servicios, Convenio de Administración (solo `OCUPADO`) | 1 334 972 · S/ 5 844 M/mes · S/ 77 216 M/año · prom S/ 4 378 |
| `pensiones` | Pensionistas, Sobrevivientes, CPMP, Palmas Magisteriales, Reconocimientos Estatales | 1 285 318 · S/ 1 382 M/mes · S/ 17 905 M/año · prom S/ 1 075 |
| `formativa` | Modalidad Formativa, Promotoras | 45 753 · S/ 29 M/mes |
| `vacantes` | cualquier tipo con `ESTADO_REGISTRO = VACANTE` (fuera del headcount) | 56 164 plazas · S/ 194 M/mes |

`masa_mensual` = `ING_IMPONIBLE_PERM_MENSUAL + ING_NO_IMPONIBLE_PERM_MENSUAL + INCENTIVO_UNICO_MENSUAL` (ingreso permanente del mes, **sin** aguinaldos, escolaridad ni aportes del empleador); `costo_anual` = `COSTO_TOTAL_ANUAL` (sí los incluye), por eso `costo_anual > masa_mensual × 12`. El antiguo "Sin Régimen Laboral: 1 034 274 a S/ 659" eran sobre todo pensionistas ONP (≈607 mil), sobrevivientes (≈332 mil), tropa, cadetes y practicantes; entre los activos quedan 36 313 sin régimen.

`airhsp.json` conserva sus campos legado (`periodo`, `total`, `masa_mensual`, `por_regimen`, `por_grupo`, que otras páginas leen y siguen contando todos los registros) y añade `total_registros`, `cobertura`, `fuente_url`, `activos` (con `por_regimen`, `por_nivel`, `por_sector` top 12 por masa, `por_tipo_registro`), `pensiones` (con `detalle` por tipo), `formativa`, `vacantes`. `airhsp_resumen.json` es el mismo contenido completo. Con `--serie` recorre todos los `PERSONALSP_*.csv` y escribe `airhsp_headcount_anual.csv` (snapshot del último mes de cada archivo: mes 12; **2020 solo llega a mes 11**).

### `scripts/build_costo.py` → `frontend/public/data/costo_estado.json`
Entradas: los archivos anteriores, `data/funcionarios.csv` (PTE), `frontend/public/data/ordenes_servicio.json`, más tres fuentes externas con copia estática de respaldo (`--offline` las fuerza):

- **IPC**: BCRPData `PN38705PM` (Índice de precios Lima Metropolitana, índice Dic.2021=100, mensual, vivo hasta Sep-2026). Promedio anual re-basado a **2025 = 100**; el año en curso promedia solo los meses publicados. `PN01270PM` (base 2009) está descontinuada en Dic-2021, no usar. Último recurso: inflación dic/dic encadenada (rotulada "fallback estático").
- **Remuneraciones % PBI**: BCRPData `PM05920FA` (gobierno general) y `PM05921FA`/`PM05922FA`/`PM05923FA` (GN/GR/GL), anuales 2015-2025.
- **Población**: INEI, *Población estimada y proyectada por sexo y tasa de crecimiento promedio anual, según año calendario, 1980-2026* (`proy_01_3.xlsx`, al 30 de junio; 2025 = 34 350 244). Es la **única** fuente de población del JSON; el Censo 2025 preliminar (34 157 732, 0,6 % menor) queda solo como cross-check en `fuentes`.

Contrato del JSON (el front programa contra esto):

```json
{
  "generated_at": "ISO",
  "planilla_mensual": {
    "airhsp": {"periodo": "Dic 2025", "fuente": "AIRHSP — MEF (datos abiertos)", "url": "...", "cobertura": "...", "total_registros": 2722207,
               "masa_mensual_todos_los_registros": 7449266162,
               "activos":   {"registros": 1334972, "masa_mensual": 5844313564, "costo_anual": 77215910915, "prom": 4378,
                             "por_regimen": [{"regimen": "", "n": 0, "prom": 0, "masa": 0}], "por_nivel": [{"nivel": "", "n": 0, "masa": 0, "prom": 0}],
                             "por_sector": [{"sector": "", "n": 0, "masa": 0, "prom": 0}], "por_tipo_registro": [{"tipo": "", "n": 0, "masa": 0, "prom": 0}]},
               "pensiones": {"registros": 1285318, "masa_mensual": 1381948055, "costo_anual": 17904541297, "prom": 1075, "detalle": [{"tipo": "Pensionistas", "n": 0, "masa": 0}]},
               "formativa": {"registros": 45753, "masa_mensual": 0}, "vacantes": {"plazas": 56164, "masa_mensual": 0},
               "servidores": 2722207, "masa_mensual": 7449266162, "por_regimen": [...], "nota": "..."},
    "pte":       {"periodo": "último mes publicado por entidad (may-2025 a jun-2026)", "servidores_con_sueldo": 204926, "masa_mensual": 870632660, "servidores_publicados": 213101, "meses_mas_frecuentes": [{"mes": "2026-04", "n": 0}], "fuente": "PTE, planilla nominal publicada por entidades", "nota": "..."},
    "locadores": {"ordenes": 4934, "monto_total": 572062518, "locadores": 4022, "periodo": "2013-12 a 2026-10", "cobertura": "muestra OCDS, 4934 órdenes acumuladas desde 2013-12; no es el universo", "nota": "...", "fuente": "OECE/OCDS"}
  },
  "headcount_airhsp": [{"anio": 2017, "mes": 12, "activos": 0, "masa_mensual": 0, "costo_anual": 0, "prom": 0, "prom_real_2025": 0, "pensiones": 0, "pensiones_masa_mensual": 0, "formativa": 0, "vacantes": 0, "total_registros": 0, "nota": null}],
  "pbi": {"fuente": "BCRP, PM05920FA", "url": "...", "codigos": {...}, "nota": "...", "serie": [{"anio": 2015, "remun_pct_pbi": 5.72, "gn_pct_pbi": 3.53, "gr_pct_pbi": 1.86, "gl_pct_pbi": 0.33}]},
  "poblacion": {"anio": 2025, "habitantes": 34350244, "fuente": "INEI ...", "serie": [{"anio": 2015, "habitantes": 0}]},
  "serie_mef": [{"anio": 2015, "personal_pia": 0, "personal_pim": 0, "personal_devengado": 0,
                 "pensiones_pia": 0, "pensiones_pim": 0, "pensiones_devengado": 0, "total_pim": 0, "total_devengado": 0,
                 "personal_real_2025": 0, "personal_per_capita": 0.0, "personal_pct_total": 0.0, "poblacion": 0,
                 "cas_23_devengado": 0, "cas_21_devengado": null, "cas_devengado": 0, "locacion_23_devengado": null, "servicios_prof_23_devengado": 0,
                 "personal_incl_cas": 0, "personal_incl_cas_real_2025": 0, "personal_incl_cas_per_capita": 0.0, "quiebre_cas": false,
                 "parcial": false, "capturado_en": "ISO", "fuente_url": "..."}],
  "inflacion": {"base": 2025, "indice": [{"anio": 2015, "ipc": 0.0}], "fuente": "...", "nota": "..."},
  "conciliacion": {"airhsp_activos_anual": 0, "airhsp_activos_masa_x12": 0, "mef_21_devengado_2025": 0, "airhsp_pensiones_anual": 0, "mef_22_devengado_2025": 0, "nota": "..."},
  "notas_metodologicas": ["..."],
  "fuentes": [{"nombre": "...", "url": "...", "nota": "..."}]
}
```

Reglas de cálculo: `personal_real_2025 = devengado × IPC_2025 / IPC_año` (ídem `personal_incl_cas_real_2025` y `prom_real_2025`); `personal_per_capita = devengado / población INEI del mismo año`; `personal_pct_total = devengado 2.1 / total_devengado × 100`; `parcial = true` si el año es el actual, o el anterior y estamos en el primer trimestre. Números siempre int/float, nunca strings; `null` si falta el dato. Al final el script relee el JSON con `json.load` y aborta si no valida.

Cómo no leerlo: AIRHSP (GN+GR, registro oficial) y PTE (lo que cada entidad publica; sin docentes ni FF.AA.; no comparable entre años) miden universos distintos y **no se suman**; las órdenes de servicio son montos totales de contrato de una muestra, no mensuales. MEF 2.1 sí incluye municipalidades; AIRHSP no. Ambos excluyen FONAFE y EsSalud.

### `scripts/build_bot_context.py`
Desde la ronda 2 el bloque TAMAÑO del contexto del bot separa activos / pensionistas / formativa / vacantes a partir de `airhsp.activos` etc., lista los regímenes de los **activos**, y advierte que los conteos por sector de `jerarquia_estado.json` incluyen pensionistas (Economía y Finanzas ≈ 777 mil pensionistas ONP).
