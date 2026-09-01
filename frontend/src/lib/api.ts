// Capa de datos: estático-primero.
// Por defecto se consume JSON estático generado por el pipeline (data/public),
// servido junto al SPA en GitHub Pages. Si se configura VITE_API_URL, las vistas
// dinámicas (grafo en vivo, búsqueda semántica) llaman al backend FastAPI.

const API_URL = import.meta.env.VITE_API_URL as string | undefined;
const STATIC_BASE = `${import.meta.env.BASE_URL}data`;

async function getJSON<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${url}`);
  return res.json() as Promise<T>;
}

/** Datos pre-renderizados (listados, perfiles, KPIs). */
export const staticData = {
  nationalKpis: () => getJSON(`${STATIC_BASE}/national_kpis.json`),
  meta: () => getJSON(`${STATIC_BASE}/meta.json`),
  entidades: () => getJSON(`${STATIC_BASE}/entidades.json`),
  funcionariosSample: () => getJSON(`${STATIC_BASE}/funcionarios_sample.json`),
  funcionariosClave: () => getJSON(`${STATIC_BASE}/funcionarios_clave.json`),
  entidad: (id: string) => getJSON(`${STATIC_BASE}/entidad/${id}.json`),
  regiones: () => getJSON(`${STATIC_BASE}/regiones.json`),
  airhsp: () => getJSON(`${STATIC_BASE}/airhsp.json`),
  personasRed: () => getJSON(`${STATIC_BASE}/personas_red.json`),
  personasShard: (l: string) => getJSON(`${STATIC_BASE}/personas/${l}.json`),
  redesEntidades: () => getJSON(`${STATIC_BASE}/redes_entidades.json`),
  salarios: () => getJSON(`${STATIC_BASE}/salarios.json`),
  jerarquia: () => getJSON(`${STATIC_BASE}/jerarquia_estado.json`),
  ordenes: () => getJSON(`${STATIC_BASE}/ordenes_servicio.json`),
  nuevosFuncionarios: () => getJSON(`${STATIC_BASE}/nuevos_funcionarios.json`),
  contratos: () => getJSON(`${STATIC_BASE}/contratos.json`),
  contratosPorEntidad: () => getJSON(`${STATIC_BASE}/contratos_por_entidad.json`),
  contratosPorProveedor: () => getJSON(`${STATIC_BASE}/contratos_por_proveedor.json`),
  sanciones: () => getJSON(`${STATIC_BASE}/sanciones.json`),
  sancionesShard: (l: string) => getJSON(`${STATIC_BASE}/sanciones/${l}.json`),
  dj: () => getJSON(`${STATIC_BASE}/dj.json`),
  djShard: (l: string) => getJSON(`${STATIC_BASE}/dj/${l}.json`),
  autoridades: () => getJSON(`${STATIC_BASE}/autoridades.json`),
  trayectorias: () => getJSON(`${STATIC_BASE}/trayectorias_poder.json`),
  botContext: () => getJSON<{ context: string }>(`${STATIC_BASE}/bot_context.json`),
};

// ── Asistente (gateway IA ai.tunky.net → OpenRouter) ──────────────────────
// El token de cliente solo habilita el ORIGEN del portal; la API key de
// OpenRouter vive server-side en el gateway y NUNCA llega al navegador.
const GATEWAY_URL = "https://ai.tunky.net/v1/chat";
const GATEWAY_TOKEN = "pte_1f2f2f2ab628a3dac4e83871b17d0ae9";

export interface ChatMsg {
  role: "system" | "user" | "assistant";
  content: string;
}

export async function askGateway(messages: ChatMsg[]): Promise<string> {
  const res = await fetch(GATEWAY_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Client-Token": GATEWAY_TOKEN },
    body: JSON.stringify({ project: "peru-transparente", messages }),
  });
  const data = (await res.json().catch(() => ({}))) as { reply?: string; error?: string };
  if (!res.ok || !data.reply) throw new Error(data.error || `error ${res.status}`);
  return data.reply;
}

// ── Histórico en vivo (VPS Postgres vía api.tunky.net) ──────────────────────
// Serie temporal demasiado grande para pre-renderizar estáticamente (1.6M filas de
// planilla 2015–2026 + designaciones de El Peruano). La sirve el backend FastAPI del
// VPS; misma convención que el gateway ai.tunky.net (endpoint público, solo lectura).
const HISTORICO_BASE = "https://api.tunky.net/peru/api/v1/historico";

export interface HistPersona {
  persona_norm: string; persona: string; id_entidad: string; entidad: string;
  cargo: string; regimen: string; total: number | null; anio: number; mes: number;
}
export interface HistPeriodo {
  anio: number; mes: number; id_entidad: string; entidad: string;
  regimen: string; cargo: string; dependencia: string; total: number | null;
}
export interface HistCambio {
  periodo: string; entidad_prev: string; entidad_actual: string;
  cargo_prev: string; cargo_actual: string; total_prev: number | null;
  total_actual: number | null; cambio_cargo: boolean; cambio_entidad: boolean;
}
export interface HistTrayectoria {
  nombre: string; periodos: HistPeriodo[]; cambios_puesto: HistCambio[];
}
export interface HistEstado {
  resumen: { planilla_filas: number; personas: number; anio_min: number; anio_max: number; designaciones: number };
  ultimas_cargas: { fuente: string; archivo: string; filas_leidas: number; filas_carga: number; inicio: string; fin: string; estado: string }[];
}

export const historicoApi = {
  base: HISTORICO_BASE,
  estado: () => getJSON<HistEstado>(`${HISTORICO_BASE}/estado`),
  personas: (q: string, limit = 30) =>
    getJSON<{ items: HistPersona[] }>(`${HISTORICO_BASE}/personas?q=${encodeURIComponent(q)}&limit=${limit}`),
  persona: (nombre: string) =>
    getJSON<HistTrayectoria>(`${HISTORICO_BASE}/persona?nombre=${encodeURIComponent(nombre)}`),
};

/** Vistas dinámicas que requieren backend. */
export const liveApi = {
  available: () => Boolean(API_URL),
  neighborhood: (nodeId: string, depth = 2) =>
    getJSON(`${API_URL}/api/v1/graph/neighborhood/${nodeId}?depth=${depth}`),
  path: (a: string, b: string) => getJSON(`${API_URL}/api/v1/graph/path?a=${a}&b=${b}`),
};
