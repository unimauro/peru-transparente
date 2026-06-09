import { useEffect, useMemo, useState } from "react";
import { staticData } from "@/lib/api";
import type { FuncionarioItem } from "@/types";
import { fmt, money, LevelBadge, Empty } from "@/components/ui";

const MESES = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Set", "Oct", "Nov", "Dic"];

export function Funcionarios() {
  const [items, setItems] = useState<FuncionarioItem[]>([]);
  const [q, setQ] = useState("");
  const [soloClave, setSoloClave] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    staticData.funcionariosSample()
      .then((d) => setItems((d as { items: FuncionarioItem[] }).items))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const nq = q.trim().toLowerCase();
    return items
      .filter((f) => (!soloClave || f.nivel !== "Profesional/Apoyo"))
      .filter((f) => !nq || `${f.nombre} ${f.cargo} ${f.entidad} ${f.dependencia}`.toLowerCase().includes(nq))
      .slice(0, 400);
  }, [items, q, soloClave]);

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <div className="chip mb-3">Muestra · {fmt.format(items.length)} registros</div>
      <h1 className="text-3xl font-bold tracking-tight text-ink">Funcionarios y cargos</h1>
      <p className="mt-2 max-w-2xl text-ink-soft">
        Cada persona mapeada a su período, cargo, dependencia, remuneración y URL fuente.
      </p>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar nombre, cargo, entidad o dependencia…" className="input flex-1" />
        <button
          onClick={() => setSoloClave((v) => !v)}
          className={`rounded-xl border px-4 py-2.5 text-sm font-medium transition ${
            soloClave ? "border-peru-red/50 bg-peru-red/15 text-peru-redsoft" : "border-surface/10 bg-surface/[0.02] text-ink-soft hover:text-ink"
          }`}
        >
          ⭐ Solo cargos clave
        </button>
      </div>

      {loading ? (
        <div className="mt-5 space-y-2">{[...Array(8)].map((_, i) => <div key={i} className="skeleton h-14" />)}</div>
      ) : filtered.length === 0 ? (
        <Empty>Sin resultados.</Empty>
      ) : (
        <div className="glass mt-5 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface/[0.06] text-left text-xs uppercase tracking-wide text-ink-mute">
                <th className="px-4 py-3">Persona</th>
                <th className="px-4 py-3">Cargo</th>
                <th className="px-4 py-3">Entidad / Dependencia</th>
                <th className="px-4 py-3">Período</th>
                <th className="px-4 py-3 text-right">Ingreso</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((f, i) => (
                <tr key={i} className="border-b border-surface/[0.04] last:border-0 transition-colors hover:bg-surface/[0.03]">
                  <td className="px-4 py-3 font-medium text-ink">{f.nombre}</td>
                  <td className="px-4 py-3">
                    <div className="text-ink-soft">{f.cargo}</div>
                    <div className="mt-1"><LevelBadge nivel={f.nivel} /></div>
                  </td>
                  <td className="px-4 py-3 text-ink-mute">
                    <div className="text-ink-soft">{f.entidad}</div>
                    <div className="text-[11px]">{f.dependencia}</div>
                  </td>
                  <td className="px-4 py-3 text-ink-mute">{MESES[+f.mes] || f.mes} {f.anio}</td>
                  <td className="tabular px-4 py-3 text-right text-ink">{money(f.total)}</td>
                  <td className="px-4 py-3 text-right"><a href={f.url} target="_blank" rel="noreferrer" className="text-accent-blue">↗</a></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="mt-3 text-xs text-ink-faint">Mostrando {filtered.length} filas · datos públicos del PTE, trazables a la fuente.</p>
    </div>
  );
}
