import { useEffect, useMemo, useState } from "react";
import { staticData } from "@/lib/api";
import { fmt, money, Empty, usePaged, Pagination } from "@/components/ui";

interface Loc {
  ruc: string; dni: string; nombre: string; n: number; monto: number;
  entidades: number; servicios: string[]; en_planilla: boolean; entidad_planilla: string;
}
interface Data {
  total_locadores: number; total_ordenes: number; monto_total: number; en_planilla: number;
  top: Loc[]; cruces: Loc[];
}

export function Ordenes() {
  const [d, setD] = useState<Data | null>(null);
  const [q, setQ] = useState("");
  const [soloCruces, setSoloCruces] = useState(false);

  useEffect(() => { staticData.ordenes().then((x) => setD(x as Data)).catch(() => {}); }, []);

  const lista = useMemo(() => {
    if (!d) return [];
    const base = soloCruces ? d.cruces : d.top;
    const nq = q.trim().toLowerCase();
    return base.filter((l) => !nq || `${l.nombre} ${l.dni} ${l.ruc}`.toLowerCase().includes(nq));
  }, [d, q, soloCruces]);

  const { slice, page, pages, setPage, total } = usePaged(lista, 40, `${q}|${soloCruces}`);

  if (!d) return <div className="mx-auto max-w-5xl px-4 py-10"><Empty>Cargando…</Empty></div>;

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <div className="chip mb-3">Órdenes de servicio · OCDS/OECE</div>
      <h1 className="text-3xl font-bold tracking-tight text-ink">Locadores del Estado</h1>
      <p className="mt-2 max-w-2xl text-ink-soft">
        Personas naturales que prestan <b>servicios</b> al Estado (locación). El <b>RUC contiene el DNI</b>,
        lo que permite rastrearlas. Seguimiento de los contratos más recientes del OCDS.
      </p>

      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="glass p-4"><div className="tabular text-2xl font-bold text-ink">{fmt.format(d.total_locadores)}</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">locadores</div></div>
        <div className="glass p-4"><div className="tabular text-2xl font-bold text-accent-cyan">{fmt.format(d.total_ordenes)}</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">órdenes</div></div>
        <div className="glass p-4"><div className="tabular text-2xl font-bold text-peru-redsoft">{money(d.monto_total)}</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">monto total</div></div>
        <div className="glass p-4"><div className="tabular text-2xl font-bold text-accent-amber">{fmt.format(d.en_planilla)}</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">también en planilla ⚠️</div></div>
      </div>

      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
        <input value={q} onChange={(e) => setQ(e.target.value)} inputMode="search" autoComplete="off" placeholder="🔎 Buscar nombre, DNI o RUC…" className="input w-full text-base sm:flex-1" />
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
                <th className="px-4 py-3">DNI / RUC</th>
                <th className="px-4 py-3">Servicio(s)</th>
                <th className="px-4 py-3 text-right">Órdenes</th>
                <th className="px-4 py-3 text-right">Monto</th>
              </tr>
            </thead>
            <tbody>
              {slice.map((l) => (
                <tr key={l.ruc} className={`border-b border-surface/[0.04] last:border-0 ${l.en_planilla ? "bg-accent-amber/[0.06]" : ""}`}>
                  <td className="px-4 py-3 font-medium text-ink">
                    {l.nombre}
                    {l.en_planilla && <div className="text-[11px] text-accent-amber">⚠️ también en planilla: {l.entidad_planilla}</div>}
                  </td>
                  <td className="px-4 py-3 tabular text-ink-mute">{l.dni}<div className="text-[10px] text-ink-faint">{l.ruc}</div></td>
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
        Fuente: OCDS/OECE (contrataciones abiertas), ventana reciente. El monto es el <b>valor total del contrato</b> (puede abarcar varios meses), no mensual.
        "También en planilla" es una <b>señal por coincidencia de nombre</b> — no implica irregularidad (la locación puede ser en otra entidad/período).
      </p>
    </div>
  );
}
