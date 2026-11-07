import { useEffect, useMemo, useState } from "react";
import { staticData } from "@/lib/api";
import { fmt, money, Empty, usePaged, Pagination } from "@/components/ui";

interface Loc {
  id: string; ruc: string; dni: string; nombre: string; n: number; monto: number;
  entidades: number; servicios: string[]; fuente_url?: string;
  en_planilla: boolean; match: "dni" | "nombre" | ""; confianza: string; entidad_planilla: string;
}
interface Data {
  total_locadores: number; total_ordenes: number; monto_total: number;
  en_planilla: number; en_planilla_dni?: number; en_planilla_nombre?: number;
  periodo?: [string, string] | null;
  top: Loc[]; cruces: Loc[];
}

const matchLabel = (l: Loc) => l.match === "dni" ? "coincidencia por DNI" : "coincidencia por nombre (homónimo posible)";

export function Ordenes() {
  const [d, setD] = useState<Data | null>(null);
  const [q, setQ] = useState("");
  const [soloCruces, setSoloCruces] = useState(false);

  useEffect(() => { staticData.ordenes().then((x) => setD(x as Data)).catch(() => {}); }, []);

  const lista = useMemo(() => {
    if (!d) return [];
    const base = soloCruces ? d.cruces : d.top;
    const nq = q.trim().toLowerCase();
    return base.filter((l) => !nq || `${l.nombre} ${l.ruc} ${l.dni}`.toLowerCase().includes(nq));
  }, [d, q, soloCruces]);

  const { slice, page, pages, setPage, total } = usePaged(lista, 40, `${q}|${soloCruces}`);

  if (!d) return <div className="mx-auto max-w-5xl px-4 py-10"><Empty>Cargando…</Empty></div>;

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <div className="chip mb-3">Órdenes de servicio · OCDS/OECE</div>
      <h1 className="text-3xl font-bold tracking-tight text-ink">Locadores del Estado</h1>
      <p className="mt-2 max-w-2xl text-ink-soft">
        Personas naturales que prestan <b>servicios</b> al Estado (locación). Seguimiento de las órdenes
        más recientes del OCDS. Se publican el <b>RUC y el DNI</b> tal como los expone el OECE, con enlace a la
        fuente de cada locador, para permitir el control ciudadano de las contrataciones (ver <a className="underline" href="#/metodologia">Metodología</a>).
      </p>

      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="glass p-4"><div className="tabular text-2xl font-bold text-ink">{fmt.format(d.total_locadores)}</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">locadores</div></div>
        <div className="glass p-4"><div className="tabular text-2xl font-bold text-accent-cyan">{fmt.format(d.total_ordenes)}</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">órdenes</div></div>
        <div className="glass p-4" title="Suma acumulada de todas las órdenes rastreadas en el periodo indicado, no de un solo año."><div className="tabular text-2xl font-bold text-peru-redsoft">{money(d.monto_total)}</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">monto acumulado{d.periodo ? ` · ${d.periodo[0]}–${d.periodo[1]}` : ""}</div></div>
        <div className="glass p-4" title="Locadores que figuran también en la planilla del PTE. Por DNI = misma persona; por nombre = homónimo posible. Es una coincidencia, no una irregularidad."><div className="tabular text-2xl font-bold text-accent-amber">{fmt.format(d.en_planilla)}</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">también en planilla · {fmt.format(d.en_planilla_dni ?? 0)} por DNI · {fmt.format(d.en_planilla_nombre ?? 0)} por nombre</div></div>
      </div>

      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
        <input value={q} onChange={(e) => setQ(e.target.value)} inputMode="search" autoComplete="off" placeholder="🔎 Buscar por nombre, RUC o DNI…" className="input w-full text-base sm:flex-1" />
        <button onClick={() => setSoloCruces((v) => !v)} className={`w-full rounded-xl border px-4 py-3 text-sm font-medium transition sm:w-auto sm:py-2.5 ${soloCruces ? "border-accent-amber/50 bg-accent-amber/15 text-accent-amber" : "border-surface/10 bg-surface/[0.02] text-ink-soft hover:text-ink"}`}>⚠️ Solo cruces con planilla</button>
      </div>

      {lista.length === 0 ? (
        <Empty>{soloCruces ? "Aún sin cruces con planilla en esta muestra." : "Sin resultados."}</Empty>
      ) : (
        <div className="glass mt-5 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface/[0.06] text-left text-xs uppercase tracking-wide text-ink-mute">
                <th className="px-4 py-3">Locador</th>
                <th className="px-4 py-3">RUC</th>
                <th className="px-4 py-3">DNI</th>
                <th className="px-4 py-3">Servicio(s)</th>
                <th className="px-4 py-3 text-right">Órdenes</th>
                <th className="px-4 py-3 text-right">Monto</th>
              </tr>
            </thead>
            <tbody>
              {slice.map((l) => (
                <tr key={l.id} className={`border-b border-surface/[0.04] last:border-0 ${l.en_planilla ? "bg-accent-amber/[0.06]" : ""}`}>
                  <td className="px-4 py-3 font-medium text-ink">
                    {l.nombre}
                    {l.en_planilla && <div className="text-[11px] text-accent-amber">figura también en la planilla de {l.entidad_planilla} ({matchLabel(l)})</div>}
                    {l.fuente_url && <a className="text-[10px] text-accent-blue hover:underline" href={l.fuente_url} target="_blank" rel="noreferrer">fuente OECE ↗</a>}
                  </td>
                  <td className="px-4 py-3 tabular text-ink-mute">{l.ruc}</td>
                  <td className="px-4 py-3 tabular text-ink-mute">{l.dni || "—"}</td>
                  <td className="px-4 py-3 text-ink-soft">{l.servicios.slice(0, 2).map((s, i) => <div key={i} className="truncate text-[11px]">{s}</div>)}{l.entidades > 1 && <span className="text-[10px] text-ink-faint">{l.entidades} entidades</span>}</td>
                  <td className="px-4 py-3 text-right tabular text-ink">{l.n}</td>
                  <td className="px-4 py-3 text-right tabular font-semibold text-peru-redsoft">{money(l.monto)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {lista.length > 0 && <Pagination page={page} pages={pages} setPage={setPage} total={total} />}
      <p className="mt-3 text-[11px] text-ink-faint">
        Fuente: OCDS/OECE (contrataciones abiertas){d.periodo ? `, órdenes de ${d.periodo[0]} a ${d.periodo[1]}` : ""}. El monto es el <b>valor total de cada orden acumulado</b> en ese periodo (no de un año ni mensual).
        "Figura también en la planilla" es una <b>coincidencia</b> con la planilla del PTE: por <b>DNI</b> (misma persona) o por <b>nombre</b> (homónimo posible). No implica irregularidad (la locación puede ser en otra entidad o período). RUC y DNI son los que publica el OECE; rectificaciones: <a className="underline" href="mailto:carlos@cardenas.pe">carlos@cardenas.pe</a>.
      </p>
    </div>
  );
}
