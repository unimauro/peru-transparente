import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { staticData } from "@/lib/api";
import type { CostoEstado } from "@/types";
import { SectionTitle } from "@/components/ui";
import { useContadorVivo, solesVivo, solesM, enteroMiles } from "@/lib/useContadorVivo";

const esNum = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);

/**
 * Tarjeta compacta para Home: contador vivo de remuneraciones AIRHSP (activos) + masa mensual.
 * Si el JSON no trae `activos`, usa la masa total con leyenda. Null si falta el JSON.
 */
export function CostoResumen() {
  const [d, setD] = useState<CostoEstado | null>(null);
  useEffect(() => {
    staticData.costoEstado()
      .then((x) => setD(x as CostoEstado))
      .catch(() => { /* sin JSON todavía: la tarjeta no aparece */ });
  }, []);

  const air = d?.planilla_mensual?.airhsp ?? null;
  const act = air?.activos ?? null;
  const conActivos = esNum(act?.masa_mensual);
  const masa = conActivos ? (act!.masa_mensual as number) : esNum(air?.masa_mensual) ? (air!.masa_mensual as number) : null;
  const plazas = conActivos ? act?.registros : air?.servidores;
  const { valor: vivo } = useContadorVivo(masa);

  if (!d || masa === null || vivo === null) return null;

  return (
    <section className="mt-8">
      <SectionTitle kicker="Costo">¿Cuánto cuesta el Estado en personal?</SectionTitle>
      <div className="glass p-6">
        <div className="text-[11px] font-medium uppercase tracking-wider text-ink-mute">Desde que abriste esta página, las remuneraciones públicas costaron</div>
        <div className="tabular mt-1 text-3xl font-bold tracking-tight text-accent-amber sm:text-4xl" aria-live="off">{solesVivo(vivo)}</div>
        <div className="mt-4 grid grid-cols-2 gap-3">
          <div>
            <div className="text-[11px] font-medium uppercase tracking-wider text-ink-mute">Al mes</div>
            <div className="tabular mt-0.5 font-semibold text-ink">{solesM(masa)}</div>
          </div>
          <div>
            <div className="text-[11px] font-medium uppercase tracking-wider text-ink-mute">{conActivos ? "Plazas activas AIRHSP (GN+GR)" : "Registros AIRHSP"}</div>
            <div className="tabular mt-0.5 font-semibold text-ink">{esNum(plazas) ? enteroMiles(plazas) : "—"}</div>
          </div>
        </div>
        <p className="mt-3 text-xs text-ink-faint">
          {air?.fuente ?? "AIRHSP — MEF"}{air?.periodo ? `, ${air.periodo}` : ""}.{" "}
          {conActivos
            ? "Solo personal activo con plaza ocupada en Gobierno Nacional y Regional; no incluye municipalidades, EsSalud ni empresas públicas. Pensiones aparte."
            : "Incluye pensionistas y sobrevivientes registrados en AIRHSP."}{" "}
          Masa mensual prorrateada por segundo.
        </p>
        <Link to="/costo" className="btn-ghost mt-4 inline-block">Ver el costo completo →</Link>
      </div>
    </section>
  );
}
