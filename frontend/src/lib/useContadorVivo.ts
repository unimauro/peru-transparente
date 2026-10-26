import { useCallback, useEffect, useRef, useState } from "react";

/** Segundos de un año civil no bisiesto (365 × 24 × 3600). */
export const SEGUNDOS_ANIO = 31_536_000;

/** Soles por segundo a partir de una masa mensual (masa × 12 / segundos del año). */
export const solesPorSegundo = (masaMensual: number) => (masaMensual * 12) / SEGUNDOS_ANIO;

/**
 * Acumulado en soles desde que se montó el componente que lo usa, con pausa/reanudar.
 * El acumulado y el instante del último tick viven en refs: los re-renders no lo reinician.
 * `valor` es null mientras `masaMensual` no sea un número válido.
 */
export function useContadorVivo(masaMensual: number | null | undefined, intervaloMs = 100) {
  const acumRef = useRef(0);
  const ultimoRef = useRef<number | null>(null);
  const [valor, setValor] = useState(0);
  const [pausado, setPausado] = useState(false);
  const valido = typeof masaMensual === "number" && Number.isFinite(masaMensual) && masaMensual > 0;

  useEffect(() => {
    if (!valido || pausado) { ultimoRef.current = null; return; }
    const porSegundo = solesPorSegundo(masaMensual);
    const tick = () => {
      const ahora = performance.now();
      if (ultimoRef.current !== null) acumRef.current += ((ahora - ultimoRef.current) / 1000) * porSegundo;
      ultimoRef.current = ahora;
      setValor(acumRef.current);
    };
    tick();
    const id = window.setInterval(tick, intervaloMs);
    return () => window.clearInterval(id);
  }, [valido, pausado, masaMensual, intervaloMs]);

  const alternar = useCallback(() => setPausado((p) => !p), []);
  return { valor: valido ? valor : null, pausado, alternar };
}

// ── Formateadores de soles ───────────────────────────────────────────────────
const NBSP = " "; // espacio fino no separable: "7 449"
const conMiles = (n: number) => Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, NBSP);

/** S/ con separadores de miles y 2 decimales fijos (para el contador). */
export const solesVivo = (v: number) => {
  const [ent, dec] = Math.abs(v).toFixed(2).split(".");
  return `${v < 0 ? "-" : ""}S/ ${ent.replace(/\B(?=(\d{3})+(?!\d))/g, NBSP)},${dec}`;
};

/** Soles enteros con miles: "S/ 2 224". */
export const solesEntero = (v: number) => `${v < 0 ? "-" : ""}S/ ${conMiles(Math.abs(v))}`;

/** Millones con miles: "S/ 7 449 M", "S/ 89 391 M". Por debajo de un millón, soles enteros. */
export const solesM = (v: number) => (Math.abs(v) < 1e6 ? solesEntero(v) : `${v < 0 ? "-" : ""}S/ ${conMiles(Math.abs(v) / 1e6)} M`);

/** Entero con miles sin moneda: "1 330 000". */
export const enteroMiles = (v: number) => `${v < 0 ? "-" : ""}${conMiles(Math.abs(v))}`;

/** Compacto para ejes: "7 449 M" / "2 224". */
export const ejeSoles = (v: number) => (Math.abs(v) < 1e6 ? conMiles(v) : `${conMiles(v / 1e6)} M`);
