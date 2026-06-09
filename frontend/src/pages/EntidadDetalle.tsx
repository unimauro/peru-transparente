import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { staticData } from "@/lib/api";
import { fmt, money, LevelBadge, Empty } from "@/components/ui";

interface Persona { nombre: string; cargo: string; nivel: string; regimen: string; total: string; url: string }
interface Dep { dependencia: string; n: number; clave: number; personas: Persona[] }
interface Detalle { id: string; nombre: string; tipo: string; periodo: string; total: number; clave: number; dependencias: Dep[] }

export function EntidadDetalle() {
  const { id } = useParams();
  const [d, setD] = useState<Detalle | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    if (!id) return;
    staticData.entidad(id).then((x) => { setD(x as Detalle); setOpen((x as Detalle).dependencias[0]?.dependencia ?? null); }).catch(() => setErr(true));
  }, [id]);

  if (err) return <div className="mx-auto max-w-4xl px-4 py-16"><Empty>Esta entidad aún no ha sido barrida. <Link to="/entidades" className="text-accent-blue underline">Ver entidades</Link></Empty></div>;
  if (!d) return <div className="mx-auto max-w-4xl px-4 py-10 space-y-3">{[...Array(6)].map((_, i) => <div key={i} className="skeleton h-12" />)}</div>;

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <Link to="/entidades" className="text-sm text-ink-mute hover:text-ink">← Entidades</Link>
      <div className="mt-2 chip">{d.tipo}</div>
      <h1 className="mt-2 text-3xl font-bold tracking-tight text-ink">{d.nombre}</h1>
      <div className="mt-3 flex flex-wrap gap-2 text-sm">
        <span className="chip">👥 {fmt.format(d.total)} servidores públicos</span>
        <span className="chip">⭐ {fmt.format(d.clave)} funcionarios/directivos (jefe ↑)</span>
        <span className="chip">🏛️ {d.dependencias.length} dependencias</span>
        <span className="chip">📅 período {d.periodo}</span>
      </div>

      <h2 className="mb-3 mt-8 text-sm font-semibold uppercase tracking-[0.2em] text-peru-redsoft/80">Organigrama por dependencias</h2>
      <div className="space-y-2">
        {d.dependencias.map((dep) => {
          const isOpen = open === dep.dependencia;
          return (
            <div key={dep.dependencia} className="glass overflow-hidden">
              <button
                onClick={() => setOpen(isOpen ? null : dep.dependencia)}
                className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition-colors hover:bg-surface/[0.04]"
              >
                <div className="flex min-w-0 items-center gap-3">
                  <span className={`text-ink-mute transition-transform ${isOpen ? "rotate-90" : ""}`}>▸</span>
                  <span className="truncate font-medium text-ink">{dep.dependencia}</span>
                </div>
                <div className="flex shrink-0 items-center gap-2 text-xs">
                  {dep.clave > 0 && <span className="rounded-md bg-peru-red/15 px-2 py-0.5 text-peru-redsoft">{dep.clave} clave</span>}
                  <span className="tabular text-ink-mute">{dep.n} pers.</span>
                </div>
              </button>
              {isOpen && (
                <div className="border-t border-surface/[0.06]">
                  <table className="w-full text-sm">
                    <tbody>
                      {dep.personas.map((p, i) => (
                        <tr key={i} className="border-t border-surface/[0.04] first:border-0">
                          <td className="px-4 py-2 text-ink">{p.nombre}</td>
                          <td className="px-4 py-2">
                            <div className="text-ink-soft">{p.cargo}</div>
                            <div className="mt-0.5"><LevelBadge nivel={p.nivel} /> <span className="text-[10px] text-ink-faint">{p.regimen}</span></div>
                          </td>
                          <td className="tabular px-4 py-2 text-right text-ink-soft">{money(p.total)}</td>
                          <td className="px-4 py-2 text-right"><a href={p.url} target="_blank" rel="noreferrer" className="text-accent-blue">↗</a></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
