# Roadmap — Perú Transparente

> Estado vivo del proyecto. Se prioriza por **valor/esfuerzo** y se mantiene el principio **estático-primero**:
> cada entrega cierra con un release navegable en GitHub Pages y datos trazables a la fuente.
> Última actualización: junio 2026.

---

## ✅ Logrado (estado actual)

La meta original de "≥100k funcionarios indexados con historial" ya se superó.

- **213 101 servidores nominales** (PTE 2026, deduplicados) de 646 entidades con datos / 2 308 del catálogo (99% barrido).
- **653 359 filas históricas** (dic 2015/2018/2021/2024) → índice de **403 319 personas con trayectoria** año a año.
- **5 637 autoridades** de gob.pe · **panorama AIRHSP/MEF** de 2 722 207 servidores (dic-2025, incl. docentes y FF.AA./PNP que el PTE no publica).
- **Dashboards live:** Inicio · Entidades (con/sin/compartida) · Funcionarios (por nivel + jerarquía Sector→Pliego) · Personas (buscador 403k + grafo persona↔entidad + red institucional + **trayectoria timeline**) · **Locadores** (órdenes de servicio OCDS por RUC/DNI) · Sueldos (ECharts) · Regiones (choropleth) · Autoridades · FAQ.
- **Asistente IA** (chatbot) anclado a los datos del portal, vía gateway `ai.tunky.net` (key server-side, costo $0 con modelos free).
- **Pipeline reproducible** documentado (`docs/FLUJO.md`) + dedup crítico (planillas padre/hijo) resuelto.

---

## Fase A — Consolidar lo que ya existe (corto plazo · semanas)

Pulir y exponer valor que ya está casi listo en los datos.

- [ ] **Página de Designaciones/Rotación.** `build_rotacion.py` ya genera `rotacion.json` (tasa 26.8%, altas/bajas, cambios de mando) pero **no tiene página**. Crear vista: ranking de entidades por rotación, nombramientos/ceses de cargos clave 2024→2026.
- [ ] **Refresco automático (GitHub Action programada).** Cron mensual que corra el barrido PTE incremental + OCDS y regenere los JSON → datos siempre frescos sin intervención manual.
- [ ] **Bot v1.1.** Panel de consumo (`/admin` del gateway), sugerencias contextuales por sección, y memoria de “no sé” honesto. Medir uso real antes de invertir más.
- [ ] **Calidad/cobertura como dashboard.** Hacer visible qué entidades NO transparentan (hallazgo fuerte): FONAFE, FF.AA., PNP, INPE, 27/35 universidades solo CAS.
- [ ] **OG/SEO por sección** (verificar que cada pestaña tenga su tarjeta social).

## Fase B — Profundidad de datos (mediano plazo)

Cerrar las brechas que convierten el portal en herramienta de **eficiencia del Estado**.

- [ ] **Locadores a escala real.** El OCDS topa en ~página 500 (~10k recientes). Estrategia de barrido por ventanas de fecha / por entidad / enumeración de OCID para cubrir el universo, y **cruce masivo con planilla** (señal de doble percepción — el mayor valor analítico).
- [ ] **Presupuesto MEF vinculado por entidad** (PIA/PIM/devengado vía META, no ejecutora). Permite el ratio **gasto vs. personal** = lectura de eficiencia.
- [ ] **Búsqueda full-text real (Supabase).** El esquema y `load_supabase.py` ya existen; cargar los 403k para `buscar_persona()` con fuzzy, en vez de shards por letra.
- [ ] **Declaraciones juradas (Contraloría):** bienes/rentas/intereses + evolución, como hipótesis con confianza (anti-overclaiming).

## Fase C — Plataforma y escala (largo plazo)

- [ ] **Cobertura territorial:** Gobiernos Regionales y Municipalidades (vía ubigeo).
- [ ] **Grafo de poder profundo:** rutas, vecindarios, centralidad; co-ocurrencias persona↔contrato↔entidad.
- [ ] **Alertas/suscripción:** seguir a un funcionario o entidad y recibir cambios (reusar patrón licitaperu/WhatsApp).
- [ ] **Exportación masiva** (CSV/JSON/Parquet) + publicación en datosabiertos.
- [ ] **Validación comunitaria** (correcciones open data con trazabilidad).

---

## Transversal (no negociable)

- **Trazabilidad 100%:** ningún dato sin fuente, URL, fecha y confianza.
- **Anti-overclaiming:** describir y vincular información pública; nunca imputar irregularidades.
- **Estático-primero:** JSON pre-renderizado; backend solo para grafo/búsqueda/exports.
- **Solo datos públicos** (Ley 29733 / 27806).

## Próximo paso sugerido

**Fase A → Página de Designaciones** (el dato ya está generado, es la entrega de mayor valor con menor esfuerzo).
