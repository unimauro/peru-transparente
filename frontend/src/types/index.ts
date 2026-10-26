export interface NationalKpis {
  total_entities: number;
  entities_processed?: number;
  entities_no_data?: number;
  entities_pending?: number;
  entities_with_data: number;
  total_funcionarios: number;
  total_cargos_clave: number;
  por_tipo: [string, number][];
  por_nivel: [string, number][];
  _generated_at: string;
}

export interface Meta {
  entidades_catalogo: number;
  entidades_con_datos: number;
  funcionarios_descargados: number;
  cobertura_pct: number;
  actualizado: string;
}

export interface EntidadCat {
  id: string;
  nombre: string;
  tipo: string;
  funcionarios: number;
  autoridades?: number;
  estado: "con_datos" | "sin_datos" | "pendiente" | "compartida";
  comparte_con?: string | null;
}

export interface FuncionarioItem {
  entidad: string;
  nombre: string;
  cargo: string;
  dependencia: string;
  regimen: string;
  anio: string;
  mes: string;
  total: string;
  url: string;
  nivel: string;
}

/** Serie histórica de las cifras del portal (public/data/historico_serie.json). */
export interface HistoricoPunto {
  fecha: string;
  [metrica: string]: number | string | null;
}

export interface HistoricoSerie {
  generated_at: string;
  /** clave de métrica → etiqueta en español */
  campos: Record<string, string>;
  /** ascendente por fecha; solo fechas de refresco publicadas */
  serie: HistoricoPunto[];
}

/** Costo del Estado en personal (public/data/costo_estado.json). Cualquier campo puede venir null o ausente. */
export interface CostoRegimen { regimen: string; n: number | null; prom: number | null; masa: number | null }
export interface CostoNivel { nivel: string; n: number | null; masa: number | null; prom: number | null }
export interface CostoSector { sector: string; n: number | null; masa: number | null; prom: number | null }

export interface CostoActivos {
  registros?: number | null;
  masa_mensual?: number | null;
  costo_anual?: number | null;
  prom?: number | null;
  por_regimen?: CostoRegimen[] | null;
  por_nivel?: CostoNivel[] | null;
  por_sector?: CostoSector[] | null;
}

export interface CostoPensiones {
  registros?: number | null;
  masa_mensual?: number | null;
  costo_anual?: number | null;
  prom?: number | null;
  detalle?: { tipo: string; n: number | null; masa: number | null }[] | null;
}

export interface CostoAirhsp {
  periodo?: string | null;
  fuente?: string | null;
  cobertura?: string | null;
  total_registros?: number | null;
  /** total mezclado (activos + pensionistas); contrato v1 */
  servidores?: number | null;
  masa_mensual?: number | null;
  por_regimen?: CostoRegimen[] | null;
  activos?: CostoActivos | null;
  pensiones?: CostoPensiones | null;
  formativa?: { registros?: number | null; masa_mensual?: number | null } | null;
  vacantes?: { plazas?: number | null; masa_mensual?: number | null } | null;
}

export interface CostoSerieMef {
  anio: number;
  personal_pia: number | null;
  personal_pim: number | null;
  personal_devengado: number | null;
  pensiones_pia?: number | null;
  pensiones_pim?: number | null;
  pensiones_devengado: number | null;
  total_pim: number | null;
  total_devengado: number | null;
  personal_real_2025: number | null;
  personal_per_capita: number | null;
  personal_pct_total: number | null;
  poblacion?: number | null;
  cas_23_devengado?: number | null;
  locacion_23_devengado?: number | null;
  servicios_prof_23_devengado?: number | null;
  /** serie homogénea: 2.1 + CAS (2.3.2.8) antes de 2024 */
  personal_incl_cas?: number | null;
  personal_incl_cas_real_2025?: number | null;
  quiebre_cas?: boolean | null;
  parcial: boolean | null;
  fuente_url?: string | null;
}

export interface CostoHeadcount {
  anio: number;
  mes?: number | null;
  activos: number | null;
  masa_mensual?: number | null;
  prom?: number | null;
  prom_real_2025?: number | null;
}

export interface CostoFuente { nombre: string; url?: string | null; nota?: string | null }

export interface CostoEstado {
  generated_at: string;
  planilla_mensual: {
    airhsp?: CostoAirhsp | null;
    pte?: { periodo?: string | null; servidores_con_sueldo?: number | null; masa_mensual?: number | null; fuente?: string | null } | null;
    locadores?: {
      ordenes?: number | null; monto_total?: number | null; locadores?: number | null;
      periodo?: string | null; nota?: string | null; fuente?: string | null; cobertura?: string | null;
    } | null;
  };
  poblacion?: { anio?: number | null; habitantes?: number | null; fuente?: string | null; serie?: { anio: number; habitantes: number | null }[] | null } | null;
  /** 2015..2026 ascendente; puede venir vacía si el scraping MEF falló */
  serie_mef?: CostoSerieMef[] | null;
  inflacion?: { base?: number | null; indice?: { anio: number; ipc: number | null }[] | null; fuente?: string | null; nota?: string | null } | null;
  headcount_airhsp?: CostoHeadcount[] | null;
  pbi?: { fuente?: string | null; url?: string | null; serie?: { anio: number; remun_pct_pbi: number | null; gn_pct_pbi?: number | null; gl_pct_pbi?: number | null }[] | null } | null;
  conciliacion?: {
    airhsp_activos_anual?: number | null; mef_21_devengado_2025?: number | null;
    airhsp_pensiones_anual?: number | null; mef_22_devengado_2025?: number | null; nota?: string | null;
  } | null;
  notas_metodologicas?: string[] | null;
  fuentes?: CostoFuente[] | null;
}
