# UI / UX — Mockups y guía de diseño

Inspiración: OpenCorporates · Aleph (OCCRP) · Data Commons · Transparency International · World Bank Data · USASpending · GovTrack. Estética: sobria, institucional, alta densidad de datos pero legible, accesible (WCAG AA), responsive, modo claro/oscuro.

## Sistema de diseño
- **Tipografía:** Inter / IBM Plex Sans. Números tabulares para cifras.
- **Color:** base neutra (grises) + acento institucional (rojo/blanco peruano usado con sobriedad). Escalas semánticas para confianza (verde alta → ámbar media → gris baja).
- **Componentes:** tarjetas de entidad/persona, tablas con facetas, chips de fuente/confianza, badges de procedencia, breadcrumbs.
- **Regla visual anti-overclaiming:** dato verificado (sólido) vs. inferencia IA (punteado / etiqueta "hipótesis").

## Pantallas (mockups ASCII)

### 1. Home / Búsqueda nacional
```
┌──────────────────────────────────────────────────────────────┐
│ 🇵🇪 PERÚ TRANSPARENTE         [ Entidades ▾ Funcionarios ▾ … ] │
├──────────────────────────────────────────────────────────────┤
│        Busca un funcionario, entidad, empresa o contrato       │
│      ┌──────────────────────────────────────────────┐  [🔍]   │
│      │ ej. "Ministerio de Economía", "Juan Pérez"   │         │
│      └──────────────────────────────────────────────┘         │
│   KPIs:  [3,012 entidades] [128,440 funcionarios]              │
│          [35 empresas FONAFE] [2.1M contratos] [S/ 240 MM]     │
│   Accesos: Dashboards · Grafo de Poder · Datos Abiertos · API  │
└──────────────────────────────────────────────────────────────┘
```

### 2. Perfil de Entidad
```
┌──────────────────────────────────────────────────────────────┐
│ Ministerio de Economía y Finanzas (MEF)   RUC 20131370645     │
│ Sector: Economía · Nivel: Nacional · [Portal] [Transparencia] │
├───────────────┬──────────────────────────────────────────────┤
│ Presupuesto   │ PIA S/ … · PIM S/ … · Devengado S/ … (2026)   │
│ Funcionarios  │ 1,240 · [ver directorio]                      │
│ Organigrama   │ [árbol D3 ▼]                                   │
│ Contratos     │ 4,512 · S/ … · [ver]                          │
│ Empresas      │ — · Normativa relevante: [DS …]               │
│ Fuente        │ datosabiertos.gob.pe · captura 2026-06-01 ●0.9│
└───────────────┴──────────────────────────────────────────────┘
```

### 3. Perfil de Funcionario
```
┌──────────────────────────────────────────────────────────────┐
│ JUAN PÉREZ GARCÍA                          [exportar ▾]       │
│ Cargo actual: Viceministro de Hacienda — MEF (desde 2025-03)  │
├──────────────────────────────────────────────────────────────┤
│ Historial de cargos        │ Remuneración │ Declaraciones      │
│ • 2025– Viceministro MEF   │ S/ 30,000    │ DJ 2025 [bienes…]  │
│ • 2021–24 Director SUNAT   │ R.M. 123-… ↗ │ DJ 2021            │
│ • 2018–21 Asesor PCM       │              │ evolución [▁▃▅]    │
├──────────────────────────────────────────────────────────────┤
│ Red de vínculos (grafo) ── [Cytoscape: persona↔entidades…]    │
│ ⚠ posibles vínculos (hipótesis IA, confianza 0.6) [ver]       │
│ Fuentes: PTE, Contraloría · captura 2026-06-01                │
└──────────────────────────────────────────────────────────────┘
```

### 4. Grafo Nacional de Poder
```
┌──────────────────────────────────────────────────────────────┐
│ [buscar nodo…]  filtros: [Persona][Entidad][Empresa][Contrato]│
│                                                                │
│        (Persona)───HOLDS──▶(Cargo)──IN──▶(Entidad)             │
│            │                                  │AWARDED          │
│         DIRECTS                               ▼                 │
│            ▼                              (Contrato)──TO──▶(Prov)│
│        (Empresa)                                               │
│  ── click un nodo: expandir vecindario · ruta entre 2 nodos ── │
│  Leyenda: ─ verificado   ┈ hipótesis IA                        │
└──────────────────────────────────────────────────────────────┘
```

### 5. Dashboard Ejecutivo Nacional
```
┌──────────────────────────────────────────────────────────────┐
│ KPIs: Funcionarios · Entidades · Empresas · Contratos · S/    │
├───────────────┬───────────────┬──────────────────────────────┤
│ Funcionarios  │ Presupuesto   │ Contratos por sector (barras) │
│ por sector 🍩 │ por sector 📊 │ ████ ███ ██ █                 │
├───────────────┴───────────────┴──────────────────────────────┤
│ Mapa del Perú (MapLibre): intensidad por región               │
└──────────────────────────────────────────────────────────────┘
```

### 6. Dashboards especializados
- **Funcionarios:** filtros sector/región/cargo/entidad/nivel jerárquico + tabla facetada.
- **Salarial:** top remuneraciones, distribución (boxplot/histograma), comparación entre entidades.
- **Designaciones:** timeline de nuevos nombramientos, ceses, rotaciones, encargaturas.
- **Contrataciones:** por entidad / proveedor / región (barras, treemap, mapa).

## Accesibilidad y rendimiento
- WCAG AA, navegación por teclado, contraste, `prefers-reduced-motion`.
- Listas virtualizadas; grafo y mapas con carga incremental.
- SEO básico (meta + sitemap) pese a ser SPA; páginas de metodología y fuentes indexables.
