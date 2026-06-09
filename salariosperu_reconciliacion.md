# Reconciliación SalariosPerú ↔ Perú Transparente

> Preparado 2026-06-09. **Sin push ni cambios en repos remotos.** Solo investigación + propuesta.
> Nota de acceso: los repos `~/salariosperu` y `~/salariosperu-data` quedan **fuera del directorio de trabajo**
> (`~/Documents/Repos/peru-transparente`) y el sandbox denegó Bash/Read sobre ellos. La descripción de
> SalariosPerú abajo proviene de la nota de memoria `project_salariosperu.md` (12 días, verificar antes de
> ejecutar). El análisis de Perú Transparente sí se computó sobre datos reales.

---

## 1. Estructura de SalariosPerú (según memoria, a confirmar leyendo los repos)

Dos repos, ambos en `~/` (NO en `~/Documents/Repos`):

| Repo | Ruta | Rol |
|---|---|---|
| `unimauro/salariosperu` | `~/salariosperu` | Web (GitHub Pages desde `docs/`), generadores Python, charts |
| `unimauro/salariosperu-data` | `~/salariosperu-data` | Datos crudos + scraper CAS + Action diaria |

**Datasets clave (formato CSV):**
- `cas_vigentes.csv` — convocatorias CAS **vigentes**. Fuente: `convocatoriasdetrabajo.com` (scraper diario,
  Action 11:00 UTC). ~1,123–1,194 registros reales. Granularidad = **una convocatoria** (oferta de empleo),
  con campos ~`institucion, puesto, departamento, salario, fecha, url` (claves cortas `i/p/d/s/f/u` en el
  payload del buscador).
- `cas_historico.csv` — tabla maestra acumulativa, PK = `url`, con `primera_vez_visto, ultima_vez_visto,
  estado (vigente/expirada), veces_vista`. Valores institución/puesto/salario = los del primer avistamiento.
- `salarios_completo.csv` — sector **privado**, ~2,068 registros. Fuente `salariosperu.com` → **CAÍDA**. No tocar.

**Naturaleza:** SalariosPerú NO tiene nombres de personas. Es **oferta** (vacantes/convocatorias) con su
salario anunciado, agregable por institución / rol / departamento / rango. Charts cifrados AES-128-GCM en
`docs/index.html` (clave hardcoded — anti-scraping, no anti-inspección).

> ⚠️ Diferencia conceptual clave: SalariosPerú = **convocatorias/ofertas CAS** (lo que el Estado *busca pagar*
> a futuro). Perú Transparente = **planilla ejecutada** (lo que el Estado *ya paga* a personas concretas).
> Son dos lados del mismo mercado laboral público; se complementan, no se solapan 1:1.

---

## 2. Estructura de Perú Transparente (datos reales analizados)

`data/funcionarios.csv` — **267,413 filas** (no 267k de nombres únicos: una fila = persona-cargo-período).
Columnas reales (más de las que indicaba la tarea):

```
id_entidad, entidad, anio, mes, regimen, apellidos_nombres, cargo, dependencia,
remuneracion, honorarios, incentivo, aguinaldo, otros, total_ingreso_mensual,
fuente_url, captured_at
```

- **674 entidades** distintas, **258,936** filas con `total_ingreso_mensual > 0`.
- Régimen: **CAS 255,544** · Ley Servir 10,047 · Altos Funcionarios 968 · FAG 513 · PAC 341.
- Períodos dominantes: 2026-04 (130,702), 2026-05 (66,316), 2026-03 (28,114). Mezcla de meses → **ojo al
  doble-conteo** si se agrega sin filtrar por período.
- Fuente: Portal de Transparencia Estándar (`transparencia.gob.pe`), rubro Personal. Trazabilidad por `fuente_url`.

Auxiliares: `entidades.csv` (2,308 entidades: id→nombre/categoría/poder), `funcionarios_clave.csv` (alta
dirección + jefaturas, con `nivel`), `autoridades.csv` (titulares con contacto, join por `slug`/`id_entidad`).

---

## 3. Punto de unión y reconciliación

**Join natural = la ENTIDAD.** SalariosPerú identifica por *nombre de institución* (texto libre del scraper);
Perú Transparente por `id_entidad` (numérico, PTE) + `entidad` (nombre oficial). No comparten id, así que el
puente es **normalización del nombre de entidad** (sin tildes, mayúsculas, alias). `entidades.csv` da el
catálogo canónico id↔nombre para esa normalización.

**Dimensión salarial común = el régimen CAS.** Es la única capa donde ambos hablan del mismo universo:
- SalariosPerú: salario *ofertado* en la convocatoria CAS.
- Perú Transparente: `total_ingreso_mensual` de los CAS ya contratados.

### Distribución salarial CAS en Perú Transparente (cuadro estilo SalariosPerú)
CAS con sueldo>0: **247,236** · media **S/ 4,048** · mediana **S/ 3,264** ·
p10 1,664 · p25 2,164 · p75 5,114 · p90 7,639 · máx 67,860.

| Rango (S/) | N | % |
|---|---:|---:|
| < 1.5k | 11,615 | 4.7% |
| 1.5k–2.5k | 72,119 | 29.2% |
| 2.5k–4k | 72,922 | 29.5% |
| 4k–6k | 46,240 | 18.7% |
| 6k–10k | 33,910 | 13.7% |
| > 10k | 10,430 | 4.2% |

Esto es directamente comparable contra el histograma de salarios de las convocatorias CAS de SalariosPerú:
permite **validar** si las ofertas reflejan la planilla real (esperado: las ofertas suelen concentrarse en
2.5k–6k, en línea con la mediana ejecutada de 3,264).

### Cómo se enriquecen mutuamente
- **PT → SalariosPerú:** PT aporta **nombres + cargo + ingreso ejecutado real** que SalariosPerú no tiene.
  Para una institución/rol con vacante, SalariosPerú puede mostrar "qué pagan hoy realmente" (mediana PT del
  mismo cargo/entidad) junto al salario ofertado. Convierte ofertas en *benchmark de mercado verificado*.
- **SalariosPerú → PT:** aporta la dimensión **prospectiva** (demanda: cuántas vacantes y a qué salario por
  entidad) que PT no tiene (PT es planilla histórica, no vacantes).

---

## 4. Discrepancias y hallazgos a vigilar

1. **No acceso directo a los repos SalariosPerú** desde este sandbox (Bash/Read denegados fuera del working
   dir). Confirmar columnas exactas de `cas_vigentes.csv` antes de ejecutar el join.
2. **Sin id compartido.** El join entidad↔entidad es por nombre normalizado → habrá no-matches (alias,
   siglas, regionales). Usar `entidades.csv` como diccionario y dejar un % de no-match medido.
3. **Mezcla de períodos en PT.** 130k filas son de 2026-04 y 66k de 2026-05. Para "cuadro de salarios actual"
   hay que **fijar un período** (recomendado: el más reciente por entidad) o se duplica gente.
4. **Bug de de-duplicación en el scrape PT (12 bloques con (n, masa) idénticos):** distintos `id_entidad`
   comparten exactamente el mismo conteo y masa salarial, p.ej.:
   - `131` (MINJUS) y `49951` (PRONABI): ambos n=3,952, masa S/23,492,723.
   - 13 Cortes Superiores + Poder Judicial (`10051`): todas n=3,865, masa S/14,756,112 idéntica.
   Esto indica que un mismo bloque de personas se está atribuyendo a varios id_entidad (probable copia del
   listado del organismo padre a sus dependencias). **No usar la suma cruda por entidad para ranking** hasta
   corregir; deduplicar por (apellidos_nombres, cargo, anio, mes) o por id canónico.
5. **8,477 filas con total=0** (267,413 − 258,936), p.ej. SUNAT id=83 con masa 0 → entidad presente pero sin
   monto publicado. Excluir del promedio.
6. **Conceptos distintos:** oferta (SalariosPerú) vs ejecución (PT). Nunca presentarlos como el mismo número;
   etiquetar "salario ofertado" vs "ingreso ejecutado (mediana PT)".

---

## 5. Propuesta de armonización y actualización

**Objetivo:** un "cuadro de salarios" reconciliado por entidad+rol que combine oferta CAS (SalariosPerú) e
ingreso ejecutado real (PT), con trazabilidad.

Esquema propuesto (`salariosperu_cuadro.proposed.csv`, ver archivo adjunto):

```
entidad_norm, id_entidad_pt, entidad_pt, regimen,
n_personas_pt, ingreso_mediana_pt, ingreso_p25_pt, ingreso_p75_pt, masa_mensual_pt,
n_convocatorias_cas, salario_oferta_mediana_cas,          # <- de SalariosPeru, a poblar
gap_oferta_vs_ejecutado,                                   # salario_oferta - mediana_pt
periodo_pt, fuente_pt_url
```

Pasos operativos (a correr cuando haya acceso a `~/salariosperu-data`):
1. Cargar `cas_vigentes.csv`; normalizar `institucion` → `entidad_norm` (sin tildes, upper, mapa de siglas).
2. Cargar `data/funcionarios.csv` de PT, **filtrar al período más reciente por id_entidad** y régimen CAS;
   normalizar `entidad` igual. Calcular por entidad: n, mediana, p25, p75 (mediana > media: robusta a outliers).
3. Join por `entidad_norm`. Medir % de match. Para los no-match, fallback por `entidades.csv` (id↔nombre).
4. Calcular `gap_oferta_vs_ejecutado`. Exportar el cuadro.
5. (Opcional UI) En SalariosPerú, junto a cada convocatoria mostrar "mediana ejecutada PT del mismo
   cargo/entidad" como benchmark verificado, citando `fuente_pt_url`.

**Importante:** la actualización del `docs/index.html` de SalariosPerú **no** debe sobrescribir los charts del
sector privado (fuente caída) ni romper el pipeline `scripts_cas/build_cas_charts.py`. La integración PT debe
ser una sección/columna NUEVA, no un reemplazo.

---

## Archivos preparados (en working dir; `/tmp` estaba bloqueado por sandbox)
- `salariosperu_reconciliacion.md` — este documento.
- `data/_funcionarios_por_entidad.csv` — agregado PT por entidad (674 filas): n, masa mensual, promedio.
- `salariosperu_cuadro.proposed.csv` — plantilla del cuadro reconciliado, ya poblada con la mitad PT
  (mediana/p25/p75/masa por entidad-CAS, período más reciente); columnas CAS de SalariosPerú quedan vacías
  a poblar cuando haya acceso al repo de datos.
- Scripts de cómputo: `scripts/_recon_salariosperu.py`, `scripts/_recon_salariosperu2.py`,
  `scripts/_build_cuadro_proposed.py` (reproducibles).
