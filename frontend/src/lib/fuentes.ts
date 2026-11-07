// Reconstrucción de la URL oficial del PTE para una aparición de la planilla
// (id_entidad, año, mes, código de régimen), mismo patrón que usa el scraper
// (scrapers/peru_transparente/connectors/pte_personal.py). Permite que cada dato
// de personas/*.json y trayectorias_poder.json enlace su fuente sin inflar el JSON.
export const PTE_BASE = "https://www.transparencia.gob.pe/personal/pte_transparencia_personal.aspx";
export const FUENTES_URL = {
  pte: PTE_BASE,
  gobpe: "https://www.gob.pe/",
  oece: "https://contratacionesabiertas.oece.gob.pe/",
  rnssc: "https://www.sanciones.gob.pe/rnssc/",
  dj: "https://www.datosabiertos.gob.pe/dataset/declaraciones-juradas-de-intereses",
  peruano: "https://busquedas.elperuano.pe/",
};

export function pteUrl(idEntidad: string | number, anio: string | number, mes?: string | number, codRegimen?: number): string | null {
  const id = String(idEntidad || "").trim();
  const a = String(anio || "").trim();
  if (!/^\d+$/.test(id) || !/^\d{4}$/.test(a)) return null;
  const m = String(mes ?? "").padStart(2, "0");
  const base = `${PTE_BASE}?id_entidad=${id}&in_anno_consulta=${a}`;
  if (!/^\d{2}$/.test(m) || m === "00") return `${base}&id_tema=32&ver=`;
  const reg = codRegimen && codRegimen > 0 ? `&ch_tipo_regimen=${codRegimen}` : "";
  return `${base}&ch_mes_consulta=${m}&vc_nombre_funcionario=&vc_dni_funcionario=${reg}&id_tema=32&Ver=`;
}
