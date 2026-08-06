import { Fragment, useEffect, useMemo, useState } from "react";
import { staticData } from "@/lib/api";
import { fmt, money, Empty, usePaged, Pagination } from "@/components/ui";

// ── tipos de los JSON generados por scripts/build_contratos.py ────────────
interface Meta { fuente: string; nota: string; generado: string; meses: string[]; n_adjudicaciones: number; monto_total: number; }
interface ProvMini { proveedor: string; ruc: string | null; tipo: string; monto: number; n: number; }
interface Resumen {
  _meta: Meta;
  resumen: { monto_total: number; n_adjudicaciones: number;
    por_tipo: Record<string, { monto: number; n: number; pct_monto: number }>; };
  por_anio: { anio: string; monto: number; n: number }[];
  top_entidades: { entidad: string; ruc: string; sector: string; monto: number; n: number }[];
  top_proveedores: ProvMini[];
}
interface Entidad {
  entidad: string; ruc: string; sector: string; monto_total: number; n_adjudicaciones: number;
  top_proveedores: ProvMini[];
}
interface Proveedor {
  proveedor: string; ruc: string | null; tipo: string; monto_total: number; n: number;
  n_entidades: number; concentracion: number;
  entidades: { entidad: string; monto: number; n: number }[];
}

const TIPO_LABEL: Record<string, string> = { juridica: "Persona jurídica", natural: "Persona natural", consorcio: "Consorcio" };
const TIPO_COLOR: Record<string, string> = { juridica: "text-accent-cyan", natural: "text-accent-amber", consorcio: "text-peru-redsoft" };

export function Contratos() {
  const [d, setD] = useState<Resumen | null>(null);
  const [modo, setModo] = useState<"entidad" | "proveedor">("entidad");
  const [ents, setEnts] = useState<Entidad[] | null>(null);
  const [provs, setProvs] = useState<Proveedor[] | null>(null);
  const [q, setQ] = useState("");
  const [abierto, setAbierto] = useState<string | null>(null);

  useEffect(() => { staticData.contratos().then((x) => setD(x as Resumen)).catch(() => {}); }, []);
  // carga perezosa del shard según el modo activo
  useEffect(() => {
    if (modo === "entidad" && !ents) staticData.contratosPorEntidad().then((x) => setEnts((x as { entidades: Entidad[] }).entidades)).catch(() => {});
    if (modo === "proveedor" && !provs) staticData.contratosPorProveedor().then((x) => setProvs((x as { proveedores: Proveedor[] }).proveedores)).catch(() => {});
  }, [modo, ents, provs]);

  const lista = useMemo<(Entidad | Proveedor)[]>(() => {
    const nq = q.trim().toLowerCase();
    if (modo === "entidad") {
      return (ents || []).filter((e) => !nq || `${e.entidad} ${e.sector}`.toLowerCase().includes(nq));
    }
    return (provs || []).filter((p) => !nq || `${p.proveedor} ${p.ruc || ""}`.toLowerCase().includes(nq));
  }, [modo, ents, provs, q]);

  const { slice, page, pages, setPage, total } = usePaged(lista, 30, `${modo}|${q}`);

  if (!d) return <div className="mx-auto max-w-5xl px-4 py-10"><Empty>Cargando…</Empty></div>;

  const t = d.resumen.por_tipo;
  const cargandoShard = (modo === "entidad" && !ents) || (modo === "proveedor" && !provs);

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <div className="chip mb-3">Contrataciones · OCDS/OECE (SEACE)</div>
      <h1 className="text-3xl font-bold tracking-tight text-ink">Contratos del Estado</h1>
      <p className="mt-2 max-w-2xl text-ink-soft">
        Adjudicaciones del Estado peruano: <b>quién compra</b> (entidad) y <b>quién vende</b> (proveedor),
        con montos y concentración. Los importes son el <b>valor adjudicado</b> —no necesariamente pagado.
      </p>
      <div className="mt-2 inline-flex items-center gap-1.5 rounded-lg border border-surface/10 bg-surface/[0.03] px-2.5 py-1 text-[12px] text-ink-mute">
        📅 Periodo: <b className="text-ink-soft">{d._meta.meses[0]} a {d._meta.meses[d._meta.meses.length - 1]}</b> · adjudicado (no pagado)
      </div>

      {/* KPIs globales */}
      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="glass p-4"><div className="tabular text-2xl font-bold text-peru-redsoft">{money(d.resumen.monto_total)}</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">adjudicado</div></div>
        <div className="glass p-4"><div className="tabular text-2xl font-bold text-ink">{fmt.format(d.resumen.n_adjudicaciones)}</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">adjudicaciones</div></div>
        <div className="glass p-4"><div className="tabular text-2xl font-bold text-accent-cyan">{t.juridica?.pct_monto ?? 0}%</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">a persona jurídica</div></div>
        <div className="glass p-4"><div className="tabular text-2xl font-bold text-accent-amber">{(t.natural?.pct_monto ?? 0)}%</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">a persona natural</div></div>
      </div>

      {/* barra de composición por tipo de proveedor */}
      <div className="glass mt-3 flex overflow-hidden rounded-xl">
        {["juridica", "natural", "consorcio"].map((k) => t[k] && t[k].pct_monto > 0 && (
          <div key={k} title={`${TIPO_LABEL[k]}: ${money(t[k].monto)} (${t[k].pct_monto}%)`}
            className={`h-2 ${k === "juridica" ? "bg-accent-cyan" : k === "natural" ? "bg-accent-amber" : "bg-peru-redsoft"}`}
            style={{ width: `${t[k].pct_monto}%` }} />
        ))}
      </div>

      {/* selector de modo */}
      <div className="mt-6 flex gap-2">
        {(["entidad", "proveedor"] as const).map((m) => (
          <button key={m} onClick={() => { setModo(m); setQ(""); setAbierto(null); }}
            className={`rounded-xl border px-4 py-2 text-sm font-medium transition ${modo === m ? "border-accent-cyan/50 bg-accent-cyan/15 text-accent-cyan" : "border-surface/10 bg-surface/[0.02] text-ink-soft hover:text-ink"}`}>
            {m === "entidad" ? "🏛️ Entidades compradoras" : "🏢 Proveedores"}
          </button>
        ))}
      </div>

      <input value={q} onChange={(e) => setQ(e.target.value)} inputMode="search" autoComplete="off"
        placeholder={modo === "entidad" ? "🔎 Buscar entidad o región…" : "🔎 Buscar proveedor o RUC…"}
        className="input mt-3 w-full text-base" />

      {cargandoShard ? (
        <Empty>Cargando…</Empty>
      ) : lista.length === 0 ? (
        <Empty>Sin resultados.</Empty>
      ) : modo === "entidad" ? (
        <div className="glass mt-5 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface/[0.06] text-left text-xs uppercase tracking-wide text-ink-mute">
                <th className="px-4 py-3">Entidad compradora</th>
                <th className="px-4 py-3">Región</th>
                <th className="px-4 py-3 text-right">Adjud.</th>
                <th className="px-4 py-3 text-right">Monto</th>
              </tr>
            </thead>
            <tbody>
              {(slice as Entidad[]).map((e) => {
                const key = `${e.entidad}|${e.ruc}`;
                const open = abierto === key;
                return (
                  <Fragment key={key}>
                    <tr onClick={() => setAbierto(open ? null : key)}
                      className="cursor-pointer border-b border-surface/[0.04] last:border-0 hover:bg-surface/[0.03]">
                      <td className="px-4 py-3 font-medium text-ink">{open ? "▾ " : "▸ "}{e.entidad}</td>
                      <td className="px-4 py-3 text-ink-mute">{e.sector}</td>
                      <td className="px-4 py-3 text-right tabular text-ink">{fmt.format(e.n_adjudicaciones)}</td>
                      <td className="px-4 py-3 text-right tabular font-semibold text-peru-redsoft">{money(e.monto_total)}</td>
                    </tr>
                    {open && (
                      <tr className="bg-surface/[0.02]"><td colSpan={4} className="px-4 py-3">
                        <div className="text-[11px] uppercase tracking-wider text-ink-mute">Principales proveedores</div>
                        <div className="mt-1 divide-y divide-surface/[0.04]">
                          {e.top_proveedores.map((p, i) => (
                            <div key={i} className="flex items-center justify-between gap-3 py-1.5 text-[13px]">
                              <span className="text-ink-soft">{p.proveedor} <span className={`text-[10px] ${TIPO_COLOR[p.tipo] || ""}`}>· {TIPO_LABEL[p.tipo] || p.tipo}{p.ruc ? ` · ${p.ruc}` : ""}</span></span>
                              <span className="tabular font-medium text-peru-redsoft">{money(p.monto)}</span>
                            </div>
                          ))}
                        </div>
                      </td></tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="glass mt-5 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface/[0.06] text-left text-xs uppercase tracking-wide text-ink-mute">
                <th className="px-4 py-3">Proveedor</th>
                <th className="px-4 py-3 text-right">Entid.</th>
                <th className="px-4 py-3 text-right">Concentr.</th>
                <th className="px-4 py-3 text-right">Monto</th>
              </tr>
            </thead>
            <tbody>
              {(slice as Proveedor[]).map((p) => {
                const key = `${p.proveedor}|${p.ruc}`;
                const open = abierto === key;
                return (
                  <Fragment key={key}>
                    <tr onClick={() => setAbierto(open ? null : key)}
                      className="cursor-pointer border-b border-surface/[0.04] last:border-0 hover:bg-surface/[0.03]">
                      <td className="px-4 py-3 font-medium text-ink">{open ? "▾ " : "▸ "}{p.proveedor}
                        <div className={`text-[10px] ${TIPO_COLOR[p.tipo] || "text-ink-faint"}`}>{TIPO_LABEL[p.tipo] || p.tipo}{p.ruc ? ` · RUC ${p.ruc}` : ""}</div>
                      </td>
                      <td className="px-4 py-3 text-right tabular text-ink">{fmt.format(p.n_entidades)}</td>
                      <td className="px-4 py-3 text-right tabular">
                        <span className={p.concentracion >= 80 ? "text-accent-amber" : "text-ink-mute"}>{p.concentracion}%</span>
                      </td>
                      <td className="px-4 py-3 text-right tabular font-semibold text-peru-redsoft">{money(p.monto_total)}</td>
                    </tr>
                    {open && (
                      <tr className="bg-surface/[0.02]"><td colSpan={4} className="px-4 py-3">
                        <div className="text-[11px] uppercase tracking-wider text-ink-mute">Entidades que le adjudicaron ({fmt.format(p.n)} adjudicaciones)</div>
                        <div className="mt-1 divide-y divide-surface/[0.04]">
                          {p.entidades.map((e, i) => (
                            <div key={i} className="flex items-center justify-between gap-3 py-1.5 text-[13px]">
                              <span className="text-ink-soft">{e.entidad}</span>
                              <span className="tabular font-medium text-peru-redsoft">{money(e.monto)}</span>
                            </div>
                          ))}
                        </div>
                      </td></tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {lista.length > 0 && <Pagination page={page} pages={pages} setPage={setPage} total={total} />}

      <p className="mt-3 text-[11px] text-ink-faint">
        Fuente: {d._meta.fuente} · meses {d._meta.meses[0]} a {d._meta.meses[d._meta.meses.length - 1]} · generado {d._meta.generado}.
        {" "}Los montos son <b>valor adjudicado</b> en el SEACE, no necesariamente pagado ni devengado.
        La <b>concentración</b> es el % del monto de un proveedor que proviene de su comprador principal
        (señal de dependencia de un solo cliente, no de irregularidad). El RUC de personas naturales se
        omite por contener el DNI; solo se publica el RUC de personas jurídicas.
      </p>
    </div>
  );
}
