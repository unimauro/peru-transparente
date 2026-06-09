# Funcionarios del Estado peruano — dataset

`funcionarios.csv` — descarga progresiva del **Portal de Transparencia Estándar**
(transparencia.gob.pe), rubro *Personal*. Una fila = una persona-cargo en un período.

## Columnas
| columna | descripción |
|---|---|
| id_entidad | id de la entidad en el PTE |
| entidad | nombre oficial |
| anio, mes | **período** del listado (mapea la persona a la fecha) |
| regimen | CAS, 276, 728/OTROS, FAG, PAC, PNUD, Altos Funcionarios, Ley Servir |
| apellidos_nombres | nombre del funcionario/servidor |
| cargo | cargo (de dirección a jefaturas a servidores) |
| dependencia | oficina/dependencia |
| total_ingreso_mensual | ingreso mensual total (S/) |
| fuente_url | **URL exacta** de la página fuente (trazabilidad) |
| captured_at | fecha/hora de captura (UTC) |

`funcionarios_clave.csv` — solo alta dirección + jefaturas (ministros, viceministros,
secretarios generales, directores, gerentes, jefes) para dimensionar personas clave.

## Cómo se llena
- Local: `python scripts/scrape_funcionarios.py --ids 1-700 --year 2026 --resume`
- CI: workflow `Scrape Funcionarios (progresivo)` — resumable, commitea el avance.
- Análisis: `python scripts/analizar_funcionarios.py`

> Solo datos públicos. Trazabilidad total (fuente + URL + fecha). Anti-overclaiming.
