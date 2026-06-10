import { useEffect, useState } from "react";
import ReactECharts from "echarts-for-react";
import { staticData } from "@/lib/api";
import { fmt, money, SectionTitle, Empty } from "@/components/ui";

interface Stat { categoria?: string; regimen?: string; n: number; mediana: number; p25: number; p75: number; max: number }
interface Sal {
  total_con_sueldo: number; mediana_nacional: number; promedio_nacional: number;
  hist_labels: string[]; hist: number[];
  top: { sueldo: number; nombre: string; cargo: string; entidad: string }[];
  por_categoria: Stat[]; por_regimen: Stat[];
}

const ink = "#aab6c6", grid = "rgba(255,255,255,0.06)";
const baseAxis = { axisLine: { lineStyle: { color: grid } }, axisLabel: { color: ink, fontSize: 10 }, splitLine: { lineStyle: { color: grid } } };

export function Salarios() {
  const [d, setD] = useState<Sal | null>(null);
  useEffect(() => { staticData.salarios().then((x) => setD(x as Sal)).catch(() => {}); }, []);

  if (!d) return <div className="mx-auto max-w-5xl px-4 py-10"><Empty>Cargando dashboard…</Empty></div>;

  const histOpt = {
    grid: { left: 40, right: 10, top: 10, bottom: 30 },
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: d.hist_labels, ...baseAxis },
    yAxis: { type: "value", ...baseAxis },
    series: [{ type: "bar", data: d.hist, itemStyle: { color: "#4f8cff" }, barWidth: "70%" }],
  };
  const catOpt = {
    grid: { left: 150, right: 20, top: 10, bottom: 24 },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: (v: number) => money(v) },
    xAxis: { type: "value", ...baseAxis },
    yAxis: { type: "category", data: [...d.por_categoria].reverse().map((c) => c.categoria), ...baseAxis },
    series: [{ type: "bar", data: [...d.por_categoria].reverse().map((c) => c.mediana), itemStyle: { color: "#1aa3c0" }, barWidth: "60%" }],
  };

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <div className="chip mb-3">Dashboard salarial</div>
      <h1 className="text-3xl font-bold tracking-tight text-ink">Sueldos del Estado</h1>
      <p className="mt-2 max-w-2xl text-ink-soft">Distribución y comparación de remuneraciones reales (PTE). Sobre {fmt.format(d.total_con_sueldo)} servidores con sueldo &gt; 0.</p>

      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
        <div className="glass p-4"><div className="tabular text-2xl font-bold text-accent-cyan">{money(d.mediana_nacional)}</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">mediana nacional</div></div>
        <div className="glass p-4"><div className="tabular text-2xl font-bold text-ink">{money(d.promedio_nacional)}</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">promedio</div></div>
        <div className="glass p-4"><div className="tabular text-2xl font-bold text-peru-redsoft">{money(d.top[0].sueldo)}</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">sueldo máximo</div></div>
      </div>

      <div className="mt-6 grid gap-5 lg:grid-cols-2">
        <div className="glass p-5">
          <SectionTitle kicker="Distribución">¿Cuánto gana el Estado?</SectionTitle>
          <ReactECharts option={histOpt} style={{ height: 260 }} />
        </div>
        <div className="glass p-5">
          <SectionTitle kicker="Comparación">Sueldo mediano por tipo de entidad</SectionTitle>
          <ReactECharts option={catOpt} style={{ height: 260 }} />
        </div>
      </div>

      <div className="mt-6 glass p-5">
        <SectionTitle kicker="Por tipo de empleo">Mediana por régimen</SectionTitle>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {d.por_regimen.map((r) => (
            <div key={r.regimen} className="rounded-lg border border-surface/10 bg-surface/[0.03] p-3">
              <div className="flex items-baseline justify-between"><span className="text-sm text-ink-soft">{r.regimen}</span><span className="tabular font-semibold text-ink">{money(r.mediana)}</span></div>
              <div className="text-[11px] text-ink-mute">{fmt.format(r.n)} · p25 {money(r.p25)} · p75 {money(r.p75)}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-6 glass p-5">
        <SectionTitle kicker="Ranking">Top 40 sueldos</SectionTitle>
        <p className="mb-3 text-[11px] text-ink-faint">⚠️ El "total mensual" puede incluir pagos extraordinarios (CTS, gratificación), no solo el sueldo base. Verifica en la fuente.</p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <tbody>
              {d.top.map((t, i) => (
                <tr key={i} className="border-b border-surface/[0.04] last:border-0">
                  <td className="px-2 py-1.5 text-ink-faint">{i + 1}</td>
                  <td className="px-2 py-1.5 text-ink">{t.nombre}</td>
                  <td className="px-2 py-1.5 text-ink-mute">{t.cargo} · <span className="text-ink-soft">{t.entidad}</span></td>
                  <td className="tabular px-2 py-1.5 text-right font-semibold text-peru-redsoft">{money(t.sueldo)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
