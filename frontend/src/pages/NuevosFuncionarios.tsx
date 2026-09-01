import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { staticData } from "@/lib/api";
import { fmt, money, Empty, LevelBadge, usePaged, Pagination } from "@/components/ui";

interface Nuevo {
  nombre: string;
  cargo: string;
  entidad: string;
  dependencia: string;
  nivel: string;
  fecha: string;
  fuente: "el_peruano" | "planilla";
  confianza: "ALTA" | "POSSIBLE_ALTA";
  fuente_url: string;
  norma: string;
  regimen: string;
  salario: number | null;
  salario_tipo: "planilla" | "referencial" | null;
  salario_rango?: [number, number];
}
interface Data {
  meta: {
    corte: string;
    generado: string;
    provenance: Record<string, string>;
    nota: string;
  };
  total: number;
  oficiales: number;
  altas_planilla: number;
  con_salario: number;
  items: Nuevo[];
}

const fechaLarga = (iso: string) =>
  iso
    ? new Date(iso + "T00:00:00").toLocaleDateString("es-PE", { day: "2-digit", month: "short", year: "numeric" })
    : "—";

export function NuevosFuncionarios() {
  const [d, setD] = useState<Data | null>(null);
  const [q, setQ] = useState("");
  const [fuente, setFuente] = useState<"todos" | "el_peruano" | "planilla">("todos");

  useEffect(() => { staticData.nuevosFuncionarios().then((x) => setD(x as Data)).catch(() => {}); }, []);

  const lista = useMemo(() => {
    if (!d) return [];
    const nq = q.trim().toLowerCase();
    return d.items.filter((it) => {
      if (fuente !== "todos" && it.fuente !== fuente) return false;
      if (!nq) return true;
      return `${it.nombre} ${it.cargo} ${it.entidad} ${it.dependencia}`.toLowerCase().includes(nq);
    });
  }, [d, q, fuente]);

  const { slice, page, pages, setPage, total } = usePaged(lista, 40, `${q}|${fuente}`);

  if (!d) return <div className="mx-auto max-w-5xl px-4 py-10"><Empty>Cargando…</Empty></div>;

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <div className="chip mb-3">Nuevos funcionarios · desde el {fechaLarga(d.meta.corte)}</div>
      <h1 className="text-3xl font-bold tracking-tight text-ink">¿Quién entró al Estado?</h1>
      <p className="mt-2 max-w-2xl text-ink-soft">
        Incorporaciones a cargos públicos a partir del <b>{fechaLarga(d.meta.corte)}</b>: nombre, <b>cargo</b>,{" "}
        <b>dónde</b> (entidad y dependencia) y <b>salario</b>. Dos orígenes: <b>designaciones publicadas en
        El Peruano</b> (con fecha y norma) y <b>altas de planilla</b> detectadas frente al padrón anterior.
      </p>

      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="glass p-4"><div className="tabular text-2xl font-bold text-ink">{fmt.format(d.total)}</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">nuevos</div></div>
        <div className="glass p-4"><div className="tabular text-2xl font-bold text-accent-cyan">{fmt.format(d.oficiales)}</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">designaciones El Peruano</div></div>
        <div className="glass p-4"><div className="tabular text-2xl font-bold text-accent-blue">{fmt.format(d.altas_planilla)}</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">altas de planilla</div></div>
        <div className="glass p-4"><div className="tabular text-2xl font-bold text-accent-amber">{fmt.format(d.con_salario)}</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">con salario</div></div>
      </div>

      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
        <input value={q} onChange={(e) => setQ(e.target.value)} inputMode="search" autoComplete="off" placeholder="🔎 Buscar nombre, cargo o entidad…" className="input w-full text-base sm:flex-1" />
        <div className="flex gap-2">
          {([["todos", "Todos"], ["el_peruano", "El Peruano"], ["planilla", "Altas planilla"]] as const).map(([k, lbl]) => (
            <button
              key={k}
              onClick={() => setFuente(k)}
              className={`rounded-xl border px-3 py-2.5 text-sm font-medium transition ${fuente === k ? "border-peru-red/50 bg-peru-red/15 text-peru-redsoft" : "border-surface/10 bg-surface/[0.02] text-ink-soft hover:text-ink"}`}
            >
              {lbl}
            </button>
          ))}
        </div>
      </div>

      {lista.length === 0 ? (
        <Empty>{fuente === "el_peruano" ? "Aún sin designaciones cargadas de El Peruano — corre el scraper de designaciones." : "Sin resultados."}</Empty>
      ) : (
        <div className="glass mt-5 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface/[0.06] text-left text-xs uppercase tracking-wide text-ink-mute">
                <th className="px-4 py-3">Funcionario</th>
                <th className="px-4 py-3">Dónde</th>
                <th className="px-4 py-3">Designación</th>
                <th className="px-4 py-3 text-right">Salario</th>
              </tr>
            </thead>
            <tbody>
              {slice.map((it, i) => (
                <tr key={`${it.nombre}-${it.entidad}-${i}`} className="border-b border-surface/[0.04] last:border-0">
                  <td className="px-4 py-3">
                    <div className="font-medium text-ink">{it.nombre || "—"}</div>
                    <div className="mt-1 flex flex-wrap items-center gap-1.5">
                      <LevelBadge nivel={it.nivel} />
                      <span className="text-[11px] text-ink-soft">{it.cargo}</span>
                    </div>
                    {it.nombre && (
                      <Link to={`/historico?n=${encodeURIComponent(it.nombre)}`} className="mt-1 inline-block text-[11px] text-accent-blue hover:underline" title="Ver sueldo histórico y cambios de puesto">
                        trayectoria →
                      </Link>
                    )}
                  </td>
                  <td className="px-4 py-3 text-ink-soft">
                    <div className="text-[13px]">{it.entidad || "—"}</div>
                    {it.dependencia && <div className="text-[11px] text-ink-faint">{it.dependencia}</div>}
                  </td>
                  <td className="px-4 py-3">
                    <div className="tabular text-ink">{fechaLarga(it.fecha)}</div>
                    {it.fuente === "el_peruano" ? (
                      <a href={it.fuente_url} target="_blank" rel="noreferrer" className="text-[11px] text-accent-cyan hover:underline">
                        {it.norma || "El Peruano ↗"}
                      </a>
                    ) : (
                      <span className="text-[11px] text-ink-faint" title="Alta detectada por comparación de padrones; sin fecha exacta.">
                        alta de planilla · señal
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {it.salario != null ? (
                      <>
                        <div className="tabular font-semibold text-ink">{money(it.salario)}</div>
                        <div className="text-[10px] text-ink-faint">
                          {it.salario_tipo === "referencial"
                            ? `referencial${it.salario_rango ? ` · S/ ${fmt.format(it.salario_rango[0])}–${fmt.format(it.salario_rango[1])}` : ""}`
                            : "planilla"}
                          {it.regimen ? ` · ${it.regimen}` : ""}
                        </div>
                      </>
                    ) : (
                      <span className="text-[11px] text-ink-faint">sin dato</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {lista.length > 0 && <Pagination page={page} pages={pages} setPage={setPage} total={total} />}

      <p className="mt-4 text-[11px] text-ink-faint">
        {d.meta.nota} Salario <b>referencial</b> = mediana del cargo por entidad y régimen (cuando el nombramiento es tan
        reciente que aún no figura en planilla). Fuentes: El Peruano (Normas Legales) y Portal de Transparencia Estándar.
        Generado el {d.meta.generado}. Solo información pública · trazable a la fuente · sin imputar irregularidades.
      </p>
    </div>
  );
}
