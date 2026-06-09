import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { staticData } from "@/lib/api";
import type { NationalKpis, Meta, EntidadCat } from "@/types";
import { Stat, Bar, SectionTitle, fmt } from "@/components/ui";
import { NetworkHero } from "@/components/NetworkHero";

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
      {/* Hero */}
      <section className="relative overflow-hidden border-b border-white/[0.06]">
        <NetworkHero />
        <div className="relative mx-auto max-w-6xl px-4 pb-12 pt-16">
          <div className="chip mb-4 animate-fade-up">🇵🇪 Plataforma open source de transparencia</div>
          <h1 className="max-w-3xl animate-fade-up text-4xl font-bold leading-[1.05] tracking-tight sm:text-6xl">
            <span className="gradient-text">Mapa nacional</span> de funcionarios,
            entidades y <span className="text-peru-redsoft">redes de poder</span>.
          </h1>
          <p className="mt-5 max-w-2xl animate-fade-up text-lg text-ink-soft">
            Todo el Estado peruano —ministerios, organismos reguladores, gobiernos regionales y
            locales, fuerzas armadas y empresas públicas— en datos públicos, trazables a su fuente.
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Link to="/entidades" className="btn-primary">Explorar entidades →</Link>
            <Link to="/funcionarios" className="btn-ghost">Funcionarios y cargos</Link>
            <a className="btn-ghost" href="https://github.com/unimauro/peru-transparente/blob/main/data/funcionarios.csv" target="_blank" rel="noreferrer">Descargar CSV</a>
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-6xl px-4 py-10">
        {!k ? (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[0, 1, 2, 3].map((i) => <div key={i} className="skeleton h-24" />)}
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Stat value={fmt.format(k.total_entities)} label="Entidades del Estado" hint="catálogo PTE completo" />
              <Stat value={fmt.format(k.total_funcionarios)} label="Funcionarios" hint={`${k.entities_with_data} entidades con datos`} accent="text-accent-cyan" />
              <Stat value={fmt.format(k.total_cargos_clave)} label="Cargos clave" hint="dirección + jefaturas" accent="text-peru-redsoft" />
              <Stat value={`${m ? m.cobertura_pct : 0}%`} label="Cobertura" hint="entidades barridas" accent="text-accent-blue" />
            </div>

            <div className="mt-8 grid gap-5 lg:grid-cols-2">
              <div className="glass p-6">
                <SectionTitle kicker="Universo">Entidades por tipo</SectionTitle>
                {k.por_tipo.map(([t, n]) => (
                  <Bar key={t} label={t} value={n} max={k.por_tipo[0][1]} />
                ))}
              </div>
              <div className="glass p-6">
                <SectionTitle kicker="Personas clave">Cargos hallados por nivel</SectionTitle>
                {k.por_nivel.length ? (
                  k.por_nivel.map(([t, n]) => (
                    <Bar key={t} label={t} value={n} max={Math.max(...k.por_nivel.map((x) => x[1]))} color="from-peru-red to-accent-amber" />
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
                    <Link key={e.id} to={`/entidad/${e.id}`} className="block rounded-lg px-2 py-1 transition-colors hover:bg-white/[0.04]">
                      <div className="flex items-baseline justify-between text-sm">
                        <span className="truncate pr-2 text-ink-soft">
                          <span className="mr-2 text-ink-faint">{i + 1}.</span>{e.nombre}
                        </span>
                        <span className="tabular shrink-0 font-semibold text-accent-cyan">{fmt.format(e.funcionarios)}</span>
                      </div>
                      <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-white/[0.06]">
                        <div className="h-full rounded-full bg-gradient-to-r from-accent-blue to-accent-cyan" style={{ width: `${Math.max(4, (e.funcionarios / top[0].funcionarios) * 100)}%` }} />
                      </div>
                    </Link>
                  ))}
                </div>
                <Link to="/entidades" className="mt-4 inline-block text-sm text-accent-blue hover:underline">Ver todas las entidades →</Link>
              </div>
            )}

            {m && (
              <p className="mt-6 text-xs text-ink-faint">
                Actualizado {new Date(m.actualizado).toLocaleString("es-PE")} · el barrido avanza por
                corridas: las cifras crecen automáticamente.
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
