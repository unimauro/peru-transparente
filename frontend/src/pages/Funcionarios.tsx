import { useEffect, useMemo, useState } from "react";
import { staticData } from "@/lib/api";
import type { FuncionarioItem, NationalKpis } from "@/types";
import { fmt, money, LevelBadge, Empty, usePaged, Pagination } from "@/components/ui";

const MESES = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Set", "Oct", "Nov", "Dic"];

const ICON: Record<string, string> = {
  "Ministro": "👑", "Viceministro": "🎖️", "Presidente Ejecutivo": "🏛️",
  "Secretario General": "📋", "Gerente General": "🏢", "Director/a": "🧭",
  "Gerente": "📊", "Jefe/a": "🗂️",
};

interface Airhsp {
  periodo: string; total: number; masa_mensual: number;
  por_regimen: { regimen: string; n: number; prom: number; masa: number }[];
}

export function Funcionarios() {
  const [items, setItems] = useState<FuncionarioItem[]>([]);
  const [kpis, setKpis] = useState<NationalKpis | null>(null);
  const [airhsp, setAirhsp] = useState<Airhsp | null>(null);
  const [q, setQ] = useState("");
  const [soloClave, setSoloClave] = useState(false);
  const [nivel, setNivel] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    staticData.funcionariosSample()
      .then((d) => setItems((d as { items: FuncionarioItem[] }).items))
      .catch(() => {})
      .finally(() => setLoading(false));
    staticData.nationalKpis().then((d) => setKpis(d as NationalKpis)).catch(() => {});
    staticData.airhsp().then((d) => setAirhsp(d as Airhsp)).catch(() => {});
  }, []);

  const filtered = useMemo(() => {
    const nq = q.trim().toLowerCase();
    return items
      .filter((f) => (!nivel || f.nivel === nivel))
      .filter((f) => (!soloClave || f.nivel !== "Profesional/Apoyo"))
      .filter((f) => !nq || `${f.nombre} ${f.cargo} ${f.entidad} ${f.dependencia}`.toLowerCase().includes(nq));
  }, [items, q, soloClave, nivel]);

  const { slice, page, pages, setPage, total } = usePaged(filtered, 50, `${q}|${soloClave}|${nivel}`);

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <div className="chip mb-3">Muestra · {fmt.format(items.length)} registros</div>
      <h1 className="text-3xl font-bold tracking-tight text-ink">Servidores públicos</h1>
      <p className="mt-2 max-w-2xl text-ink-soft">
        Todo el personal del Estado mapeado a su período, cargo, dependencia, remuneración y URL fuente.
        Los <b className="text-peru-redsoft">funcionarios</b> son los cargos de mando (de jefe ↑).
      </p>

      {/* Resumen del dataset completo (antes del buscador) */}
      {kpis && (
        <div className="mt-6 glass p-5">
          <div className="flex flex-wrap items-end gap-x-8 gap-y-3">
            <div>
              <div className="tabular text-3xl font-bold text-ink">{fmt.format(kpis.total_funcionarios)}</div>
              <div className="text-[11px] uppercase tracking-wider text-ink-mute">servidores públicos (total)</div>
            </div>
            <div>
              <div className="tabular text-3xl font-bold text-peru-redsoft">{fmt.format(kpis.total_cargos_clave)}</div>
              <div className="text-[11px] uppercase tracking-wider text-ink-mute">funcionarios y directivos · de jefe ↑</div>
            </div>
            <div>
              <div className="tabular text-3xl font-bold text-accent-cyan">
                {((kpis.total_cargos_clave / Math.max(kpis.total_funcionarios, 1)) * 100).toFixed(1)}%
              </div>
              <div className="text-[11px] uppercase tracking-wider text-ink-mute">son cargos de mando</div>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {kpis.por_nivel.map(([lvl, n]) => {
              const active = nivel === lvl;
              return (
                <button
                  key={lvl}
                  onClick={() => setNivel(active ? "" : lvl)}
                  className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm transition ${
                    active ? "border-peru-red/50 bg-peru-red/15 text-peru-redsoft" : "border-surface/10 bg-surface/[0.04] text-ink-soft hover:border-surface/25 hover:text-ink"
                  }`}
                  title={`Filtrar por ${lvl}`}
                >
                  <span>{ICON[lvl] ?? "•"}</span>
                  <span>{lvl}</span>
                  <span className="tabular font-semibold text-ink">{fmt.format(n)}</span>
                </button>
              );
            })}
            {nivel && (
              <button onClick={() => setNivel("")} className="rounded-lg border border-surface/10 px-3 py-1.5 text-sm text-ink-mute hover:text-ink">✕ quitar filtro</button>
            )}
          </div>
          <p className="mt-3 text-[11px] text-ink-faint">
            {nivel
              ? `Filtrando la tabla por “${nivel}”. Clic de nuevo para quitar.`
              : `Cifras del dataset completo (${fmt.format(kpis.entities_with_data)} entidades con datos). Clic en un nivel para filtrar la tabla.`}
          </p>
        </div>
      )}

      {airhsp && (
        <div className="mt-5 glass p-5">
          <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-accent-violet/80">Panorama nacional · AIRHSP (MEF)</div>
              <h2 className="text-lg font-semibold text-ink">Todo el Estado por tipo de empleo</h2>
            </div>
            <div className="text-right">
              <div className="tabular text-2xl font-bold text-accent-violet">{fmt.format(airhsp.total)}</div>
              <div className="text-[11px] text-ink-mute">servidores · {airhsp.periodo}</div>
            </div>
          </div>
          <div className="space-y-2">
            {airhsp.por_regimen.map((r) => {
              const max = Math.max(...airhsp.por_regimen.map((x) => x.n));
              return (
                <div key={r.regimen}>
                  <div className="flex items-baseline justify-between text-sm">
                    <span className="text-ink-soft">{r.regimen}</span>
                    <span className="text-ink-mute"><span className="tabular font-semibold text-ink">{fmt.format(r.n)}</span> · prom {money(r.prom)}</span>
                  </div>
                  <div className="mt-1 h-2 overflow-hidden rounded-full bg-surface/[0.06]">
                    <div className="h-full rounded-full bg-gradient-to-r from-accent-violet to-accent-blue" style={{ width: `${Math.max(2, (r.n / max) * 100)}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
          <p className="mt-3 text-[11px] text-ink-faint">
            Fuente: AIRHSP — MEF (planilla oficial agregada, <b>sin nombres</b>). Cubre lo que el PTE no publica: <b>docentes</b> (Carreras Especiales) y <b>FF.AA./Policía</b>. La tabla nominal de abajo es del PTE (con nombres).
          </p>
        </div>
      )}

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
              {slice.map((f, i) => (
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
      {!loading && filtered.length > 0 && <Pagination page={page} pages={pages} setPage={setPage} total={total} />}
      <p className="mt-3 text-xs text-ink-faint">Datos públicos del PTE, trazables a la fuente. Para ver todo el personal de una entidad, ábrela en Entidades.</p>
    </div>
  );
}
