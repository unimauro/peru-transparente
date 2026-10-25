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
