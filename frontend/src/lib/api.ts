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
  autoridades: () => getJSON(`${STATIC_BASE}/autoridades.json`),
};

/** Vistas dinámicas que requieren backend. */
export const liveApi = {
  available: () => Boolean(API_URL),
  neighborhood: (nodeId: string, depth = 2) =>
    getJSON(`${API_URL}/api/v1/graph/neighborhood/${nodeId}?depth=${depth}`),
  path: (a: string, b: string) => getJSON(`${API_URL}/api/v1/graph/path?a=${a}&b=${b}`),
};
