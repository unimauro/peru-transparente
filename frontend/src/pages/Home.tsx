import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { staticData } from "@/lib/api";
import type { NationalKpis, Meta, EntidadCat } from "@/types";
import { Bar, SectionTitle, fmt } from "@/components/ui";
import { HeroCosto } from "@/components/HeroCosto";
import { MapaDatos } from "@/components/MapaDatos";
import { Evolucion } from "@/components/Evolucion";

export function Home() {
  const [k, setK] = useState<NationalKpis | null>(null);
  const [m, setM] = useState<Meta | null>(null);
  const [top, setTop] = useState<EntidadCat[]>([]);
  useEffect(() => {
    staticData.nationalKpis().then((d) => setK(d as NationalKpis)).catch(() => {});
    staticData.meta().then((d) => setM(d as Meta)).catch(() => {});
    staticData.entidades()
      .then((d) => setTop((d as { items: EntidadCat[] }).items.filter((e) => e.funcionarios > 0).slice(0, 12)))
      .catch(() => {});
  }, []);

  return (
    <div>
      <HeroCosto />

      <div className="mx-auto max-w-6xl px-4 pb-10">
        <MapaDatos kpis={k} />

        {/* Evolución temporal de las cifras: trae su propio SectionTitle y no renderiza nada si falta historico_serie.json */}
        <Evolucion />

        {k && (
          <>
            {/* Progreso del barrido (3 estados) + qué es el PTE */}
            <div className="glass mt-10 p-6">
              <div className="mb-2 flex items-baseline justify-between">
                <SectionTitle kicker="Cobertura">Avance del barrido nacional</SectionTitle>
                <span className="tabular text-sm font-semibold text-accent-blue">{m ? m.cobertura_pct : 0}%</span>
              </div>
              {(() => {
                const t = k.total_entities;
                const cd = k.entities_with_data;
                const sd = k.entities_no_data ?? 0;
                const pd = k.entities_pending ?? (t - cd - sd);
                const pct = (x: number) => `${(x / t) * 100}%`;
                return (
                  <>
                    <div className="flex h-3 w-full overflow-hidden rounded-full bg-surface/[0.06]">
                      <div className="bg-accent-cyan" style={{ width: pct(cd) }} title="con datos" />
                      <div className="bg-ink-faint/60" style={{ width: pct(sd) }} title="sin datos publicados" />
                    </div>
                    <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-sm">
                      <span className="text-ink-soft"><span className="text-accent-cyan">●</span> {fmt.format(cd)} entidades con personal publicado</span>
                      <span className="text-ink-soft"><span className="text-ink-faint">●</span> {fmt.format(sd)} barridas sin personal publicado</span>
                      <span className="text-ink-mute"><span className="text-ink-faint">○</span> {fmt.format(pd)} pendientes</span>
                    </div>
                  </>
                );
              })()}
              <p className="mt-4 border-t border-surface/[0.06] pt-3 text-xs text-ink-mute">
                La fuente de la planilla es el <b className="text-ink-soft">Portal de Transparencia Estándar</b> (transparencia.gob.pe), donde cada entidad
                publica su personal, presupuesto y contrataciones. Las entidades "sin personal publicado" existen pero no suben ese rubro,
                y eso también es un dato de transparencia.
              </p>
            </div>

            <div className="mt-6 grid gap-5 lg:grid-cols-2">
              <div className="glass p-6">
                <SectionTitle kicker="Universo">Entidades por tipo</SectionTitle>
                {k.por_tipo.map(([t, x]) => (
                  <Bar key={t} label={t} value={x} max={k.por_tipo[0][1]} />
                ))}
              </div>
              <div className="glass p-6">
                <SectionTitle kicker="Personas clave">Cargos hallados por nivel</SectionTitle>
                {k.por_nivel.length ? (
                  k.por_nivel.map(([t, x]) => (
                    <Bar key={t} label={t} value={x} max={Math.max(...k.por_nivel.map((y) => y[1]))} color="from-peru-red to-accent-amber" />
                  ))
                ) : (
                  <p className="text-sm text-ink-mute">Descargando…</p>
                )}
              </div>
            </div>

            {top.length > 0 && (
              <div className="glass mt-5 p-6">
                <SectionTitle kicker="Ranking">Entidades con más funcionarios</SectionTitle>
                <div className="space-y-3">
                  {top.map((e, i) => (
                    <Link key={e.id} to={`/entidad/${e.id}`} className="block rounded-lg px-2 py-1 transition-colors hover:bg-surface/[0.04]">
                      <div className="flex items-baseline justify-between text-sm">
                        <span className="truncate pr-2 text-ink-soft">
                          <span className="mr-2 text-ink-faint">{i + 1}.</span>{e.nombre}
                        </span>
                        <span className="tabular shrink-0 font-semibold text-accent-cyan">{fmt.format(e.funcionarios)}</span>
                      </div>
                      <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-surface/[0.06]">
                        <div className="h-full rounded-full bg-gradient-to-r from-accent-blue to-accent-cyan" style={{ width: `${Math.max(4, (e.funcionarios / top[0].funcionarios) * 100)}%` }} />
                      </div>
                    </Link>
                  ))}
                </div>
                <Link to="/entidades" className="mt-4 inline-block text-sm text-accent-blue hover:underline">Ver todas las entidades</Link>
              </div>
            )}

            <div className="glass mt-5 flex flex-col gap-3 p-6 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <div className="text-base font-semibold text-ink">Todo esto también se puede descargar</div>
                <p className="mt-1 text-sm text-ink-mute">Planilla completa en CSV, JSON de cada sección y código abierto bajo AGPL-3.0. Datos CC BY 4.0.</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <a className="btn-ghost" href="https://github.com/unimauro/peru-transparente/raw/main/data/funcionarios.csv.gz" target="_blank" rel="noreferrer">Descargar CSV</a>
                <a className="btn-ghost" href="https://github.com/unimauro/peru-transparente" target="_blank" rel="noreferrer">Ver el código</a>
                <Link className="btn-ghost" to="/metodologia">Metodología</Link>
              </div>
            </div>

            {m && (
              <p className="mt-6 text-xs text-ink-faint">
                Planilla descargada del PTE el {new Date(m.planilla_capturada ?? m.actualizado).toLocaleDateString("es-PE")}.
                JSON regenerado el {new Date(m.actualizado).toLocaleDateString("es-PE")}. Las cifras cambian solo cuando
                hay un nuevo refresco, no de forma continua.
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
