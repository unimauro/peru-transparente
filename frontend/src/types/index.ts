export interface NationalKpis {
  total_entities: number;
  entities_processed?: number;
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
