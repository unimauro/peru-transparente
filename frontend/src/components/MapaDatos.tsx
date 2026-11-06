import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { staticData } from "@/lib/api";
import type { NationalKpis } from "@/types";
import { fmt, SectionTitle } from "@/components/ui";
import { solesM, solesEntero } from "@/lib/useContadorVivo";

interface Fila { to: string; cifra: ReactNode; titulo: string; detalle: string }

const n = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const fechaLarga = (iso: string) => {
  const d = new Date(`${iso}T00:00:00`);
  return isNaN(d.getTime()) ? iso : d.toLocaleDateString("es-PE", { day: "numeric", month: "long", year: "numeric" });
};

/**
 * Índice de la portada en forma de libro mayor: una fila por sección, con la cifra
 * real que publica su JSON. Cada fuente se pide por separado; una que falle solo
 * oculta su fila, nunca la lista entera.
 */
export function MapaDatos({ kpis }: { kpis: NationalKpis | null }) {
  const [extra, setExtra] = useState<Record<string, Fila | null>>({});

  useEffect(() => {
    const pide = <T,>(clave: string, p: Promise<unknown>, arma: (d: T) => Fila | null) => {
      p.then((d) => setExtra((e) => ({ ...e, [clave]: arma(d as T) })))
       .catch(() => setExtra((e) => ({ ...e, [clave]: null })));
    };
    pide<{ resumen?: { monto_total?: number; n_adjudicaciones?: number } }>("contratos", staticData.contratos(), (d) =>
      n(d.resumen?.monto_total) ? {
        to: "/contratos", cifra: solesM(d.resumen!.monto_total!), titulo: "adjudicados en contratos públicos",
        detalle: `${n(d.resumen?.n_adjudicaciones) ? fmt.format(d.resumen!.n_adjudicaciones!) : ""} adjudicaciones del SEACE, por entidad y proveedor`,
      } : null);
    pide<{ total_locadores?: number; en_planilla?: number }>("ordenes", staticData.ordenes(), (d) =>
      n(d.total_locadores) ? {
        to: "/ordenes", cifra: fmt.format(d.total_locadores!), titulo: "locadores de servicio",
        detalle: n(d.en_planilla) ? `${fmt.format(d.en_planilla!)} figuran también en una planilla pública` : "personas naturales con órdenes de servicio",
      } : null);
    pide<{ total_sanciones?: number; total_personas?: number }>("sanciones", staticData.sanciones(), (d) =>
      n(d.total_sanciones) ? {
        to: "/sanciones", cifra: fmt.format(d.total_sanciones!), titulo: "sanciones vigentes",
        detalle: n(d.total_personas) ? `sobre ${fmt.format(d.total_personas!)} personas, según el registro de SERVIR` : "registro nacional de SERVIR",
      } : null);
    pide<{ summary?: { total?: number } }>("trayectorias", staticData.trayectorias(), (d) =>
      n(d.summary?.total) ? {
        to: "/trayectorias", cifra: fmt.format(d.summary!.total!), titulo: "trayectorias de poder",
        detalle: "cargos de mando que pasan de una institución a otra, 2015 a 2026",
      } : null);
    pide<{ total?: number; meta?: { corte?: string } }>("nuevos", staticData.nuevosFuncionarios(), (d) =>
      n(d.total) ? {
        to: "/nuevos", cifra: fmt.format(d.total!), titulo: "designaciones y altas recientes",
        detalle: d.meta?.corte ? `desde el ${fechaLarga(d.meta.corte)}, con la norma de El Peruano cuando existe` : "designaciones publicadas en El Peruano y altas de planilla",
      } : null);
    pide<{ mediana_nacional?: number }>("salarios", staticData.salarios(), (d) =>
      n(d.mediana_nacional) ? {
        to: "/salarios", cifra: solesEntero(d.mediana_nacional!), titulo: "sueldo mediano publicado",
        detalle: "la mitad de los servidores con sueldo en el portal gana menos que esto",
      } : null);
  }, []);

  const base: (Fila | null)[] = kpis ? [
    { to: "/entidades", cifra: fmt.format(kpis.total_entities), titulo: "entidades del Estado", detalle: "ministerios, reguladores, gobiernos regionales y locales, fuerzas armadas y empresas públicas" },
    { to: "/funcionarios", cifra: fmt.format(kpis.total_funcionarios), titulo: "personas con nombre y sueldo publicado", detalle: `${fmt.format(kpis.total_cargos_clave)} en cargos de dirección o jefatura` },
  ] : [null, null];

  const orden = ["contratos", "salarios", "ordenes", "sanciones", "trayectorias", "nuevos"];
  const filas = [...base, ...orden.map((k) => extra[k])];
  const cargando = filas.filter((f) => f === undefined).length;

  return (
    <section className="mt-14">
      <SectionTitle kicker="Índice">Lo que puedes consultar</SectionTitle>
      <div className="ledger">
        {filas.map((f, i) =>
          f ? (
            <Link key={f.to} to={f.to} className="ledger-row reveal" style={{ "--i": i + 1 } as React.CSSProperties}>
              <span className="display whitespace-nowrap text-3xl text-ink sm:text-[2rem]">{f.cifra}</span>
              <span className="min-w-0">
                <span className="block text-base font-medium text-ink">{f.titulo}</span>
                <span className="block text-sm text-ink-mute">{f.detalle}</span>
              </span>
              <span aria-hidden="true" className="ledger-arrow hidden text-ink-mute sm:block">→</span>
            </Link>
          ) : f === undefined ? (
            <div key={`sk-${i}`} className="ledger-row"><span className="skeleton h-8 w-28" /><span className="skeleton h-5 w-2/3" /></div>
          ) : null,
        )}
      </div>
      {cargando === 0 && filas.every((f) => f === null) && (
        <p className="py-6 text-sm text-ink-mute">Los índices aún no están publicados. Vuelve en el próximo refresco.</p>
      )}
    </section>
  );
}
