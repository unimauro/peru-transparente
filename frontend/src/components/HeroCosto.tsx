import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { staticData } from "@/lib/api";
import type { CostoEstado } from "@/types";
import { esNum } from "@/components/costo/util";
import { useContadorVivo, solesVivo, solesM, solesEntero, enteroMiles, solesPorSegundo } from "@/lib/useContadorVivo";

const pct1 = new Intl.NumberFormat("es-PE", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

/**
 * Portada: el contador vivo del gasto en remuneraciones es el protagonista.
 * Lee costo_estado.json (AIRHSP activos GN+GR). Si el JSON falta o no trae masa,
 * cae a un titular estático para que la portada nunca quede vacía.
 */
export function HeroCosto() {
  const [d, setD] = useState<CostoEstado | null>(null);
  const [fallo, setFallo] = useState(false);
  useEffect(() => {
    staticData.costoEstado()
      .then((x) => setD(x as CostoEstado))
      .catch(() => setFallo(true));
  }, []);

  const air = d?.planilla_mensual?.airhsp ?? null;
  const act = air?.activos ?? null;
  const conActivos = esNum(act?.masa_mensual);
  const masa = conActivos ? (act!.masa_mensual as number) : esNum(air?.masa_mensual) ? (air!.masa_mensual as number) : null;
  const plazas = conActivos ? act?.registros : air?.servidores;
  const habitantes = esNum(d?.poblacion?.habitantes) ? (d!.poblacion!.habitantes as number) : null;
  const pbiSerie = (d?.pbi?.serie ?? []).filter((p) => esNum(p.remun_pct_pbi));
  const pbi = pbiSerie.length ? pbiSerie[pbiSerie.length - 1] : null;
  const { valor: vivo, pausado, alternar } = useContadorVivo(masa);

  const listo = masa !== null && vivo !== null;

  return (
    <section className="relative overflow-hidden border-b border-surface/[0.08]">
      <div className="relative mx-auto max-w-6xl px-4 pb-14 pt-14 sm:pt-20">
        <p className="reveal text-sm text-ink-mute" style={{ "--i": 0 } as React.CSSProperties}>
          Datos públicos del Estado peruano, trazables a su fuente.
        </p>

        {listo || (!fallo && !d) ? (
          <>
            <h1 className="reveal mt-5 max-w-3xl text-2xl font-medium leading-snug text-ink-soft sm:text-3xl" style={{ "--i": 1 } as React.CSSProperties}>
              Desde que abriste esta página, el Estado peruano gastó en sueldos
            </h1>
            <div className="reveal mt-3 flex flex-wrap items-end gap-x-6 gap-y-3" style={{ "--i": 2 } as React.CSSProperties}>
              <div
                className="display break-all text-oro"
                style={{ fontSize: "clamp(3rem, 11vw, 7.5rem)" }}
                aria-live="off"
                aria-label={listo ? `${solesVivo(vivo)} acumulados desde que abriste la página` : "Calculando"}
              >
                {listo ? solesVivo(vivo) : <span className="skeleton inline-block h-[0.9em] w-[7ch] align-baseline" />}
              </div>
              {listo && (
                <button type="button" onClick={alternar} aria-pressed={pausado} className="btn-ghost mb-2 px-3 py-1.5 text-xs">
                  {pausado ? "Reanudar" : "Pausar"}
                </button>
              )}
            </div>
            {listo && (
              <p className="reveal mt-5 max-w-2xl text-base text-ink-soft sm:text-lg" style={{ "--i": 3 } as React.CSSProperties}>
                <b className="font-semibold text-ink">{solesEntero(solesPorSegundo(masa))} cada segundo</b> en remuneraciones de{" "}
                {esNum(plazas) ? <b className="font-semibold text-ink">{enteroMiles(plazas)} plazas activas</b> : "las plazas activas"} del
                Gobierno Nacional y Regional, al ritmo de {air?.periodo ?? "diciembre 2025"}
                {conActivos ? ". Sin municipalidades, EsSalud ni empresas públicas; pensiones aparte." : "."}
              </p>
            )}
          </>
        ) : (
          <>
            <h1 className="reveal mt-5 max-w-3xl text-4xl font-bold leading-[1.05] tracking-tight text-ink sm:text-6xl" style={{ "--i": 1 } as React.CSSProperties}>
              Quién trabaja para el Estado, cuánto gana y a quién contrata.
            </h1>
            <p className="reveal mt-5 max-w-2xl text-lg text-ink-soft" style={{ "--i": 2 } as React.CSSProperties}>
              Ministerios, reguladores, gobiernos regionales y locales, fuerzas armadas y empresas públicas, en datos públicos con enlace a la fuente.
            </p>
          </>
        )}

        {listo && (
          <dl className="reveal mt-10 grid max-w-3xl grid-cols-1 gap-6 border-t border-surface/[0.12] pt-6 sm:grid-cols-3" style={{ "--i": 4 } as React.CSSProperties}>
            <div>
              <dt className="order-2 text-sm text-ink-mute">cada mes en remuneraciones</dt>
              <dd className="display -order-1 text-2xl text-ink sm:text-3xl">{solesM(masa)}</dd>
            </div>
            <div>
              <dt className="text-sm text-ink-mute">por habitante al mes</dt>
              <dd className="display text-2xl text-ink sm:text-3xl">{habitantes ? solesEntero(masa / habitantes) : "—"}</dd>
            </div>
            <div>
              <dt className="text-sm text-ink-mute">{pbi ? `del PBI en ${pbi.anio}, estable desde 2017` : "del PBI"}</dt>
              <dd className="display text-2xl text-ink sm:text-3xl">{pbi ? `${pct1.format(pbi.remun_pct_pbi as number)} %` : "—"}</dd>
            </div>
          </dl>
        )}

        <div className="reveal mt-8 flex flex-wrap gap-3" style={{ "--i": 5 } as React.CSSProperties}>
          <Link to="/costo" className="btn-primary">Ver el costo completo</Link>
          <Link to="/entidades" className="btn-ghost">Explorar entidades</Link>
          <Link to="/personas" className="btn-ghost">Buscar una persona</Link>
        </div>
      </div>
    </section>
  );
}
