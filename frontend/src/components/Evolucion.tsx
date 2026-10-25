import { useEffect, useMemo, useState } from "react";
import ReactECharts from "echarts-for-react";
import { staticData } from "@/lib/api";
import type { HistoricoSerie } from "@/types";
import { fmt, money, SectionTitle } from "@/components/ui";

// Mismos tonos que los gráficos de Salarios para mantener coherencia visual.
const ink = "#aab6c6", grid = "rgba(255,255,255,0.06)";
const esMonto = (key: string) => /_monto$/.test(key);
const fecha = (iso: string) => {
  const d = new Date(`${iso}T00:00:00`);
  return isNaN(d.getTime()) ? iso : d.toLocaleDateString("es-PE", { day: "2-digit", month: "short", year: "numeric" });
};

/**
 * Evolución de las cifras del portal a lo largo de los refrescos publicados.
 * Si el JSON no existe o viene vacío, no renderiza nada.
 */
export function Evolucion() {
  const [data, setData] = useState<HistoricoSerie | null>(null);
  const [metrica, setMetrica] = useState<string>("funcionarios");

  useEffect(() => {
    staticData.historicoSerie()
      .then((d) => {
        const h = d as HistoricoSerie;
        if (h && Array.isArray(h.serie) && h.serie.length > 0 && h.campos) setData(h);
      })
      .catch(() => { /* sin histórico aún: la sección simplemente no aparece */ });
  }, []);

  // Métricas con al menos un valor numérico (las totalmente null no se ofrecen).
  const disponibles = useMemo(() => {
    if (!data) return [] as string[];
    return Object.keys(data.campos).filter((k) =>
      data.serie.some((p) => typeof p[k] === "number" && Number.isFinite(p[k] as number)),
    );
  }, [data]);

  // Métrica inicial: la primera que realmente se MUEVE en la serie (funcionarios es
  // constante desde jun-2026 porque la planilla PTE se refresca a mano, no a diario).
  const [inicializada, setInicializada] = useState(false);
  useEffect(() => {
    if (!data || !disponibles.length) return;
    if (!inicializada) {
      const seMueve = disponibles.find((k) => {
        const vals = data.serie.map((p) => p[k]).filter((v): v is number => typeof v === "number");
        return vals.length > 1 && Math.min(...vals) !== Math.max(...vals);
      });
      setMetrica(seMueve ?? disponibles[0]);
      setInicializada(true);
      return;
    }
    if (!disponibles.includes(metrica)) setMetrica(disponibles[0]);
  }, [data, disponibles, metrica, inicializada]);

  const puntos = useMemo(() => {
    if (!data) return [] as { fecha: string; valor: number | null }[];
    return data.serie.map((p) => {
      const v = p[metrica];
      return { fecha: p.fecha, valor: typeof v === "number" && Number.isFinite(v) ? v : null };
    });
  }, [data, metrica]);

  if (!data || disponibles.length === 0) return null;

  const monto = esMonto(metrica);
  const formatea = (v: number) => (monto ? money(v) : fmt.format(v));
  const label = data.campos[metrica] ?? metrica;

  const reales = puntos.filter((p) => p.valor !== null) as { fecha: string; valor: number }[];
  const primero = reales[0];
  const ultimo = reales[reales.length - 1];
  const delta = primero && ultimo ? ultimo.valor - primero.valor : 0;
  const pct = primero && primero.valor !== 0 ? (delta / primero.valor) * 100 : null;
  const signo = delta > 0 ? "+" : "";
  const tono = delta > 0 ? "text-accent-green" : delta < 0 ? "text-peru-redsoft" : "text-ink-soft";

  const option = {
    grid: { left: 8, right: 16, top: 24, bottom: 8, containLabel: true },
    tooltip: {
      trigger: "axis",
      formatter: (params: { value: [string, number | null] }[] | { value: [string, number | null] }) => {
        const p = Array.isArray(params) ? params[0] : params;
        if (!p || !p.value) return "";
        const [f, v] = p.value;
        return `<b>${fecha(f)}</b><br/>${label}: ${v === null ? "sin dato" : formatea(v)}`;
      },
    },
    xAxis: {
      type: "time",
      axisLine: { lineStyle: { color: grid } },
      axisLabel: { color: ink, fontSize: 10, hideOverlap: true, formatter: (v: number) => new Date(v).toLocaleDateString("es-PE", { day: "2-digit", month: "short" }) },
      splitLine: { show: false },
    },
    yAxis: {
      type: "value",
      scale: true,
      axisLine: { lineStyle: { color: grid } },
      splitLine: { lineStyle: { color: grid } },
      axisLabel: {
        color: ink, fontSize: 10,
        formatter: (v: number) => (monto ? `S/ ${new Intl.NumberFormat("es-PE", { notation: "compact", maximumFractionDigits: 1 }).format(v)}` : new Intl.NumberFormat("es-PE", { notation: "compact", maximumFractionDigits: 1 }).format(v)),
      },
    },
    series: [{
      type: "line",
      name: label,
      data: puntos.map((p) => [p.fecha, p.valor]),
      connectNulls: false,
      showSymbol: true,
      symbol: "circle",
      symbolSize: 7,
      lineStyle: { width: 2, color: monto ? "#d97706" : "#1aa3c0" },
      itemStyle: { color: monto ? "#d97706" : "#1aa3c0" },
      areaStyle: { color: monto ? "rgba(217,119,6,0.10)" : "rgba(26,163,192,0.10)" },
    }],
  };

  return (
    <section className="mt-8">
      <SectionTitle kicker="Evolución">Evolución de las cifras</SectionTitle>
      <p className="-mt-2 mb-3 text-xs text-ink-mute">Cada punto es un refresco publicado; los huecos son días sin actualización.</p>
    <div className="glass p-6">
      {/* Selector de métrica */}
      <div className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1 sm:flex-wrap" role="tablist" aria-label="Métrica">
        {disponibles.map((k) => {
          const activo = k === metrica;
          return (
            <button
              key={k}
              type="button"
              role="tab"
              aria-selected={activo}
              onClick={() => setMetrica(k)}
              className={`chip shrink-0 whitespace-nowrap transition-colors ${activo ? "!border-accent-cyan/50 !bg-accent-cyan/15 !text-accent-cyan" : "hover:!border-surface/20"}`}
            >
              {data.campos[k] ?? k}
            </button>
          );
        })}
      </div>

      <ReactECharts key={metrica} option={option} notMerge style={{ height: 260 }} className="mt-3" />

      {/* Mini-resumen */}
      {primero && ultimo && (
        <div className="mt-3 grid grid-cols-2 gap-3 border-t border-surface/[0.06] pt-4 sm:grid-cols-4">
          <div>
            <div className="text-[11px] font-medium uppercase tracking-wider text-ink-mute">Primer dato</div>
            <div className="tabular mt-0.5 font-semibold text-ink">{formatea(primero.valor)}</div>
            <div className="text-xs text-ink-faint">{fecha(primero.fecha)}</div>
          </div>
          <div>
            <div className="text-[11px] font-medium uppercase tracking-wider text-ink-mute">Último dato</div>
            <div className="tabular mt-0.5 font-semibold text-ink">{formatea(ultimo.valor)}</div>
            <div className="text-xs text-ink-faint">{fecha(ultimo.fecha)}</div>
          </div>
          <div>
            <div className="text-[11px] font-medium uppercase tracking-wider text-ink-mute">Variación</div>
            <div className={`tabular mt-0.5 font-semibold ${tono}`}>{signo}{formatea(delta)}</div>
            <div className="text-xs text-ink-faint">entre primer y último refresco</div>
          </div>
          <div>
            <div className="text-[11px] font-medium uppercase tracking-wider text-ink-mute">Variación %</div>
            <div className={`tabular mt-0.5 font-semibold ${tono}`}>
              {pct === null ? "—" : `${signo}${pct.toLocaleString("es-PE", { maximumFractionDigits: 1 })}%`}
            </div>
            <div className="text-xs text-ink-faint">{fmt.format(reales.length)} {reales.length === 1 ? "refresco con dato" : "refrescos con dato"}</div>
          </div>
        </div>
      )}
    </div>
    </section>
  );
}
