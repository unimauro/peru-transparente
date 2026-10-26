import ReactECharts from "echarts-for-react";
import type { CostoEstado, CostoHeadcount } from "@/types";
import { SectionTitle } from "@/components/ui";
import { solesEntero, enteroMiles, solesM } from "@/lib/useContadorVivo";
import { esNum, pct1, baseAxis, AMBAR, CIAN } from "./util";

/** Serie AIRHSP 2017→2025: plazas activas (barras) y remuneración promedio real (línea). Null si falta. */
export function Headcount({ d }: { d: CostoEstado }) {
  const serie: CostoHeadcount[] = [...(d.headcount_airhsp ?? [])].filter((p) => esNum(p.anio) && esNum(p.activos)).sort((a, b) => a.anio - b.anio);
  if (serie.length < 2) return null;

  const etiqueta = (p: CostoHeadcount) => (p.mes === 11 ? `${p.anio} (nov)` : String(p.anio));
  const hayReal = serie.some((p) => esNum(p.prom_real_2025));
  const primero = serie[0], ultimo = serie[serie.length - 1];
  const varPlazas = (primero.activos as number) > 0 ? (((ultimo.activos as number) - (primero.activos as number)) / (primero.activos as number)) * 100 : null;
  const varReal = esNum(primero.prom_real_2025) && esNum(ultimo.prom_real_2025) && primero.prom_real_2025 > 0
    ? ((ultimo.prom_real_2025 - primero.prom_real_2025) / primero.prom_real_2025) * 100 : null;
  const dir = (v: number) => (v >= 0 ? "+" : "−");

  const option = {
    grid: { left: 8, right: 8, top: 28, bottom: 8, containLabel: true },
    legend: { top: 0, textStyle: { color: "#aab6c6", fontSize: 10 } },
    tooltip: {
      trigger: "axis",
      formatter: (params: { dataIndex: number }[] | { dataIndex: number }) => {
        const p = Array.isArray(params) ? params[0] : params;
        const h = serie[p.dataIndex];
        if (!h) return "";
        return `<b>${etiqueta(h)}</b><br/>Plazas activas: ${enteroMiles(h.activos as number)}`
          + (esNum(h.masa_mensual) ? `<br/>Masa mensual: ${solesM(h.masa_mensual)}` : "")
          + (esNum(h.prom) ? `<br/>Promedio nominal: ${solesEntero(h.prom)}` : "")
          + (esNum(h.prom_real_2025) ? `<br/>Promedio en soles de ${d.inflacion?.base ?? 2025}: ${solesEntero(h.prom_real_2025)}` : "");
      },
    },
    xAxis: { type: "category", data: serie.map(etiqueta), ...baseAxis, splitLine: { show: false } },
    yAxis: [
      { type: "value", name: "plazas", nameTextStyle: { color: "#aab6c6", fontSize: 10 }, ...baseAxis, axisLabel: { ...baseAxis.axisLabel, formatter: (v: number) => (v >= 1e6 ? `${(v / 1e6).toLocaleString("es-PE", { maximumFractionDigits: 2 })} M` : enteroMiles(v)) } },
      ...(hayReal ? [{ type: "value", name: "S/ prom. real", nameTextStyle: { color: "#aab6c6", fontSize: 10 }, scale: true, ...baseAxis, splitLine: { show: false }, axisLabel: { ...baseAxis.axisLabel, formatter: (v: number) => enteroMiles(v) } }] : []),
    ],
    series: [
      { type: "bar", name: "Plazas activas", data: serie.map((p) => p.activos), itemStyle: { color: AMBAR, borderRadius: [4, 4, 0, 0] }, barWidth: "55%" },
      ...(hayReal ? [{ type: "line", name: `Promedio real (soles de ${d.inflacion?.base ?? 2025})`, yAxisIndex: 1, data: serie.map((p) => (esNum(p.prom_real_2025) ? p.prom_real_2025 : null)), symbol: "circle", symbolSize: 7, lineStyle: { width: 2, color: CIAN }, itemStyle: { color: CIAN } }] : []),
    ],
  };

  return (
    <section className="mt-12">
      <SectionTitle kicker="Plazas y remuneración">¿Crece la gente o crece el sueldo?</SectionTitle>
      <div className="glass p-6">
        <ReactECharts option={option} notMerge style={{ height: 280 }} />
        {varPlazas !== null && (
          <p className="mt-3 text-sm text-ink-soft">
            {varReal !== null && Math.abs(varPlazas) > Math.abs(varReal)
              ? <>Lo que crece más rápido es el número de plazas ({dir(varPlazas)}{pct1(Math.abs(varPlazas))} {primero.anio}→{ultimo.anio}) que la remuneración promedio real ({dir(varReal)}{pct1(Math.abs(varReal))}).</>
              : varReal !== null
                ? <>La remuneración promedio real ({dir(varReal)}{pct1(Math.abs(varReal))} {primero.anio}→{ultimo.anio}) crece más rápido que el número de plazas ({dir(varPlazas)}{pct1(Math.abs(varPlazas))}).</>
                : <>Las plazas activas variaron {dir(varPlazas)}{pct1(Math.abs(varPlazas))} entre {primero.anio} y {ultimo.anio}.</>}
          </p>
        )}
        <p className="mt-2 text-xs text-ink-faint">
          AIRHSP — MEF, personal activo con plaza ocupada (GN+GR), corte de diciembre de cada año{serie.some((p) => p.mes === 11) ? " (noviembre donde se indica)" : ""}.
          {hayReal ? ` Promedio deflactado con IPC BCRP base ${d.inflacion?.base ?? 2025}.` : ""}
        </p>
      </div>
    </section>
  );
}
