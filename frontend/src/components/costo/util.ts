import type { CostoEstado, CostoSerieMef } from "@/types";

export const esNum = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);

/** Escapa texto que va dentro del HTML de un tooltip ECharts (nombres de régimen/sector vienen de datos). */
export const esc = (s: unknown) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c] as string));

export const pct1 = (v: number) => `${v.toLocaleString("es-PE", { maximumFractionDigits: 1 })} %`;

// Mismos tonos que Salarios/Evolución para coherencia visual.
export const ink = "#aab6c6", grid = "rgba(255,255,255,0.06)";
export const baseAxis = { axisLine: { lineStyle: { color: grid } }, axisLabel: { color: ink, fontSize: 10 }, splitLine: { lineStyle: { color: grid } } };
export const AMBAR = "#d97706", CIAN = "#1aa3c0", VIOLETA = "#8b5cf6";

/** IPC del año (índice re-basado) o null. */
export function ipcDe(d: CostoEstado, anio: number | null | undefined): number | null {
  if (!esNum(anio)) return null;
  const v = (d.inflacion?.indice ?? []).find((i) => i.anio === anio)?.ipc;
  return esNum(v) && v > 0 ? v : null;
}

/** Deflacta un monto nominal del año `anio` a soles del año base del JSON. */
export function deflactar(d: CostoEstado, v: number | null | undefined, anio: number): number | null {
  const base = d.inflacion?.base;
  const ipcA = ipcDe(d, anio), ipcB = ipcDe(d, base);
  return esNum(v) && ipcA !== null && ipcB !== null ? (v * ipcB) / ipcA : null;
}

/** Población del año: fila MEF → serie INEI → implícita en per cápita → null. */
export function poblacionDe(d: CostoEstado, p: CostoSerieMef): number | null {
  if (esNum(p.poblacion) && p.poblacion > 0) return p.poblacion;
  const s = (d.poblacion?.serie ?? []).find((x) => x.anio === p.anio)?.habitantes;
  if (esNum(s) && s > 0) return s;
  if (esNum(p.personal_devengado) && esNum(p.personal_per_capita) && p.personal_per_capita > 0) return p.personal_devengado / p.personal_per_capita;
  return null;
}
