import { useEffect, useMemo, useState } from "react";
import ReactECharts from "echarts-for-react";
import type { CostoEstado, CostoSerieMef } from "@/types";
import { fmt, money, Stat } from "@/components/ui";
import { solesM, ejeSoles, solesEntero } from "@/lib/useContadorVivo";
import { esNum, pct1, baseAxis, AMBAR, CIAN, deflactar, poblacionDe } from "./util";

type Metrica = "personal" | "pensiones" | "ambas";
type Vista = "nominal" | "real" | "percapita" | "pct" | "pbi";
const METRICAS: { key: Metrica; label: string }[] = [
  { key: "personal", label: "Personal (2.1)" },
  { key: "pensiones", label: "Pensiones (2.2)" },
  { key: "ambas", label: "Ambas" },
];
const VISTAS: { key: Vista; label: string }[] = [
  { key: "nominal", label: "Nominal" },
  { key: "real", label: "Soles de 2025" },
  { key: "percapita", label: "Por habitante" },
  { key: "pct", label: "% del presupuesto" },
  { key: "pbi", label: "% del PBI" },
];

/** Nominal de personal: serie homogénea (2.1 + CAS) si existe, si no la 2.1 tal cual. */
const personalNominal = (p: CostoSerieMef, homogenea: boolean) =>
  homogenea ? (esNum(p.personal_incl_cas) ? p.personal_incl_cas : null) : esNum(p.personal_devengado) ? p.personal_devengado : null;

function personalReal(d: CostoEstado, p: CostoSerieMef, homogenea: boolean): number | null {
  if (homogenea) return esNum(p.personal_incl_cas_real_2025) ? p.personal_incl_cas_real_2025 : deflactar(d, p.personal_incl_cas, p.anio);
  return esNum(p.personal_real_2025) ? p.personal_real_2025 : deflactar(d, p.personal_devengado, p.anio);
}

/** Valor de un punto para una métrica simple (personal | pensiones) y una vista. */
function valor(d: CostoEstado, p: CostoSerieMef, m: "personal" | "pensiones", vista: Vista, homogenea: boolean): number | null {
  const nominal = m === "personal" ? personalNominal(p, homogenea) : esNum(p.pensiones_devengado) ? p.pensiones_devengado : null;
  if (vista === "nominal") return nominal;
  if (vista === "real") return m === "personal" ? personalReal(d, p, homogenea) : deflactar(d, nominal, p.anio);
  if (vista === "percapita") { const pob = poblacionDe(d, p); return nominal !== null && pob ? nominal / pob : null; }
  if (vista === "pct") return nominal !== null && esNum(p.total_devengado) && p.total_devengado > 0 ? (nominal / p.total_devengado) * 100 : null;
  if (m !== "personal") return null;
  const v = (d.pbi?.serie ?? []).find((x) => x.anio === p.anio)?.remun_pct_pbi;
  return esNum(v) ? v : null;
}

const formato = (vista: Vista, v: number) => (vista === "pct" || vista === "pbi" ? pct1(v) : vista === "percapita" ? solesEntero(v) : solesM(v));

/** Años consecutivos de aumento contando hacia atrás desde el último año completo. */
function consecutivos(vals: (number | null)[]): number {
  let n = 0;
  for (let i = vals.length - 1; i > 0; i--) {
    const a = vals[i], b = vals[i - 1];
    if (a !== null && b !== null && a > b) n++;
    else break;
  }
  return n;
}

const variacionPct = (a: number | null, b: number | null) => (a !== null && b !== null && a > 0 ? ((b - a) / a) * 100 : null);

export function SerieAnual({ d }: { d: CostoEstado }) {
  const [metrica, setMetrica] = useState<Metrica>("personal");
  const [vista, setVista] = useState<Vista>("nominal");

  const serie = useMemo(() => [...(d.serie_mef ?? []).filter((p) => esNum(p.anio))].sort((a, b) => a.anio - b.anio), [d]);
  const homogenea = useMemo(() => serie.some((p) => esNum(p.personal_incl_cas)), [serie]);
  const completos = useMemo(() => serie.filter((p) => !p.parcial), [serie]);
  const parcial = useMemo(() => serie.find((p) => p.parcial) ?? null, [serie]);
  const quiebre = useMemo(() => serie.find((p) => p.quiebre_cas) ?? null, [serie]);
  const mBase: "personal" | "pensiones" = metrica === "pensiones" ? "pensiones" : "personal";

  const vistasDisponibles = useMemo(
    () => VISTAS.filter((v) => (metrica === "ambas" && v.key === "pbi" ? false : serie.some((p) => esNum(valor(d, p, mBase, v.key, homogenea))))),
    [d, serie, metrica, mBase, homogenea],
  );
  useEffect(() => {
    if (vistasDisponibles.length && !vistasDisponibles.some((v) => v.key === vista)) setVista(vistasDisponibles[0].key);
  }, [vistasDisponibles, vista]);
  const hayPensiones = serie.some((p) => esNum(p.pensiones_devengado));

  const completosConDato = completos.filter((p) => valor(d, p, mBase, "nominal", homogenea) !== null);
  const primero = completosConDato[0] ?? null;
  const ultimo = completosConDato.length ? completosConDato[completosConDato.length - 1] : null;

  if (completosConDato.length === 0) {
    return (
      <div className="glass p-6">
        <div className="font-semibold text-ink">Serie anual MEF en construcción</div>
        <p className="mt-1 text-sm text-ink-mute">Cuando la consulta al portal de Transparencia Económica del MEF esté publicada, aquí aparecerá la evolución 2015→2026 del gasto en personal (genérica 2.1).</p>
      </div>
    );
  }

  // KPI: años consecutivos de aumento sobre la métrica seleccionada, nominal y real.
  const nNominal = consecutivos(completos.map((p) => valor(d, p, mBase, "nominal", homogenea)));
  const nReal = consecutivos(completos.map((p) => valor(d, p, mBase, "real", homogenea)));

  // Frase de variación: serie homogénea → un tramo; sin homogénea y con quiebre → dos tramos.
  const tramos: { a: CostoSerieMef; b: CostoSerieMef }[] = [];
  if (primero && ultimo && primero.anio !== ultimo.anio) {
    const qIdx = quiebre && mBase === "personal" && !homogenea ? completosConDato.findIndex((p) => p.anio === quiebre.anio) : -1;
    if (qIdx > 0) {
      tramos.push({ a: primero, b: completosConDato[qIdx - 1] });
      if (qIdx < completosConDato.length - 1) tramos.push({ a: completosConDato[qIdx], b: ultimo });
    } else tramos.push({ a: primero, b: ultimo });
  }
  const frase = (t: { a: CostoSerieMef; b: CostoSerieMef }) => {
    const n = variacionPct(valor(d, t.a, mBase, "nominal", homogenea), valor(d, t.b, mBase, "nominal", homogenea));
    const r = variacionPct(valor(d, t.a, mBase, "real", homogenea), valor(d, t.b, mBase, "real", homogenea));
    const dir = (v: number) => (v >= 0 ? "subió" : "bajó");
    return `Entre ${t.a.anio} y ${t.b.anio} ${mBase === "personal" ? "el gasto devengado en personal" : "el gasto devengado en pensiones"}${n !== null ? ` ${dir(n)} ${pct1(Math.abs(n))} en soles corrientes` : " no tiene comparación nominal"}${r !== null ? ` y ${dir(r)} ${pct1(Math.abs(r))} en soles de ${d.inflacion?.base ?? 2025}` : ""}.`;
  };

  // ── Gráfica ────────────────────────────────────────────────────────────────
  const etiquetas = serie.map((p) => (p.parcial ? `${p.anio} (parcial)` : String(p.anio)));
  const idxParcial = serie.findIndex((p) => p.parcial);
  const lineas = (m: "personal" | "pensiones", color: string, nombre: string) => {
    const vals = serie.map((p) => valor(d, p, m, vista, homogenea));
    const solida = vals.map((v, i) => (serie[i].parcial ? null : v));
    const punteada = vals.map((v, i) => (serie[i].parcial || (idxParcial > 0 && i === idxParcial - 1) ? v : null));
    return [
      { type: "line", name: nombre, data: solida, connectNulls: false, showSymbol: true, symbol: "circle", symbolSize: 7, lineStyle: { width: 2, color }, itemStyle: { color }, areaStyle: { color: color === AMBAR ? "rgba(217,119,6,0.10)" : "rgba(26,163,192,0.10)" } },
      { type: "line", name: `${nombre} (parcial)`, data: punteada, connectNulls: false, showSymbol: true, symbol: "emptyCircle", symbolSize: 7, lineStyle: { width: 2, type: "dashed", color }, itemStyle: { color }, tooltip: { show: false } },
    ];
  };
  const series: Record<string, unknown>[] = [
    ...(metrica !== "pensiones" ? lineas("personal", AMBAR, "Personal (2.1)") : []),
    ...(metrica !== "personal" ? lineas("pensiones", CIAN, "Pensiones (2.2)") : []),
  ];
  if (quiebre && metrica !== "pensiones" && series[0]) {
    series[0].markLine = {
      symbol: "none", silent: true,
      lineStyle: { color: "#aab6c6", type: "dotted", width: 1 },
      label: { color: "#aab6c6", fontSize: 10, formatter: `${quiebre.anio}: CAS pasa de 2.3 a 2.1`, position: "insideEndTop" },
      data: [{ xAxis: etiquetas[serie.findIndex((p) => p.anio === quiebre.anio)] }],
    };
  }
  const option = {
    grid: { left: 8, right: 16, top: 28, bottom: 8, containLabel: true },
    legend: metrica === "ambas" ? { top: 0, textStyle: { color: "#aab6c6", fontSize: 10 }, data: ["Personal (2.1)", "Pensiones (2.2)"] } : undefined,
    tooltip: {
      trigger: "axis",
      formatter: (params: { dataIndex: number; seriesName: string; value: number | null }[] | { dataIndex: number; seriesName: string; value: number | null }) => {
        const arr = Array.isArray(params) ? params : [params];
        const p0 = arr[0];
        if (!p0) return "";
        const pt = serie[p0.dataIndex];
        const filas = arr.filter((x) => x.value !== null && x.value !== undefined && !/\(parcial\)$/.test(x.seriesName))
          .map((x) => `${x.seriesName}: ${formato(vista, x.value as number)}`);
        return `<b>${pt.anio}${pt.parcial ? " (parcial)" : ""}</b><br/>${filas.length ? filas.join("<br/>") : "sin dato"}`;
      },
    },
    xAxis: { type: "category", data: etiquetas, ...baseAxis, splitLine: { show: false }, axisLabel: { ...baseAxis.axisLabel, hideOverlap: true } },
    yAxis: {
      type: "value", scale: true, ...baseAxis,
      axisLabel: { ...baseAxis.axisLabel, formatter: (v: number) => (vista === "pct" || vista === "pbi" ? `${v} %` : vista === "percapita" ? `S/ ${ejeSoles(v)}` : `S/ ${ejeSoles(v)}`) },
    },
    series,
  };

  // Párrafo PBI (si hay serie): rango desde 2017 y cuántos años nominales suben.
  const pbiSerie = (d.pbi?.serie ?? []).filter((x) => x.anio >= 2017 && esNum(x.remun_pct_pbi));
  const pbiMin = pbiSerie.length ? Math.min(...pbiSerie.map((x) => x.remun_pct_pbi as number)) : null;
  const pbiMax = pbiSerie.length ? Math.max(...pbiSerie.map((x) => x.remun_pct_pbi as number)) : null;
  const nominalesPersonal = completos.map((p) => valor(d, p, "personal", "nominal", homogenea));
  const subidas = nominalesPersonal.reduce<number>((acc, v, i) => (i > 0 && v !== null && nominalesPersonal[i - 1] !== null && v > (nominalesPersonal[i - 1] as number) ? acc + 1 : acc), 0);
  const chip = (activo: boolean, color: "amber" | "cyan") =>
    `chip shrink-0 whitespace-nowrap transition-colors ${activo ? (color === "amber" ? "!border-accent-amber/50 !bg-accent-amber/15 !text-accent-amber" : "!border-accent-cyan/50 !bg-accent-cyan/15 !text-accent-cyan") : "hover:!border-surface/20"}`;

  return (
    <>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Stat
          value={<span>{fmt.format(nNominal)} <span className="text-base font-medium text-ink-mute">nominal</span> · {fmt.format(nReal)} <span className="text-base font-medium text-ink-mute">real</span></span>}
          label="Años consecutivos de aumento"
          hint={ultimo ? `${mBase === "personal" ? "personal" : "pensiones"}, hasta ${ultimo.anio} (último año cerrado)` : undefined}
          accent="text-accent-amber"
        />
        <Stat
          value={primero ? formato("nominal", valor(d, primero, mBase, "nominal", homogenea) as number) : "—"}
          label={primero ? `Devengado ${primero.anio}` : "Primer año"}
          hint={mBase === "personal" ? (homogenea ? "nominal, 2.1 + CAS (serie homogénea)" : "nominal, MEF genérica 2.1") : "nominal, MEF genérica 2.2"}
        />
        <Stat
          value={ultimo ? formato("nominal", valor(d, ultimo, mBase, "nominal", homogenea) as number) : "—"}
          label={ultimo ? `Devengado ${ultimo.anio}` : "Último año cerrado"}
          hint={parcial && esNum(mBase === "personal" ? parcial.personal_pim : parcial.pensiones_pim)
            ? `presupuesto modificado ${parcial.anio}: ${solesM((mBase === "personal" ? parcial.personal_pim : parcial.pensiones_pim) as number)}`
            : "último año cerrado"}
        />
      </div>

      <div className="glass mt-4 p-6">
        {hayPensiones && (
          <div className="-mx-1 mb-2 flex gap-2 overflow-x-auto px-1 pb-1 sm:flex-wrap" role="tablist" aria-label="Genérica de gasto">
            {METRICAS.map((m) => (
              <button key={m.key} type="button" role="tab" aria-selected={m.key === metrica} onClick={() => setMetrica(m.key)} className={chip(m.key === metrica, "cyan")}>{m.label}</button>
            ))}
          </div>
        )}
        <div className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1 sm:flex-wrap" role="tablist" aria-label="Vista de la serie">
          {vistasDisponibles.map((v) => (
            <button key={v.key} type="button" role="tab" aria-selected={v.key === vista} onClick={() => setVista(v.key)} className={chip(v.key === vista, "amber")}>{v.label}</button>
          ))}
        </div>
        <ReactECharts key={`${metrica}-${vista}`} option={option} notMerge style={{ height: 300 }} className="mt-3" />
        <p className="mt-2 text-xs text-ink-faint">
          {mBase === "personal"
            ? (homogenea ? "Personal y obligaciones sociales (genérica 2.1) más CAS (2.3.2.8) antes de 2024: serie homogénea." : "Personal y obligaciones sociales (genérica 2.1), devengado.")
            : "Pensiones y otras prestaciones sociales (genérica 2.2), devengado."}{" "}
          Gobierno Nacional + Regional + Local, MEF Consulta Amigable.
          {parcial ? ` ${parcial.anio} es parcial (devengado a la fecha del refresco) y va punteado${esNum(parcial.personal_pim) && mBase === "personal" ? `; su presupuesto modificado es ${solesM(parcial.personal_pim)}` : ""}.` : ""}
          {quiebre && mBase === "personal" ? ` En ${quiebre.anio} el CAS pasó de la genérica 2.3 a la 2.1 (Ley 31953)${homogenea ? "; la serie homogénea ya lo corrige" : "; el salto de ese año es en parte reclasificación"}.` : ""}
          {vista === "real" ? ` Deflactado con IPC Lima Metropolitana del BCRP, base ${d.inflacion?.base ?? 2025}.` : ""}
          {vista === "percapita" ? " Dividido entre la población INEI de cada año." : ""}
          {vista === "pct" ? " Participación sobre el total devengado del presupuesto público." : ""}
          {vista === "pbi" ? ` Remuneraciones del gobierno general como % del PBI, ${d.pbi?.fuente ?? "BCRP"}.` : ""}
        </p>
        {(d.notas_metodologicas ?? []).length > 0 && (
          <ul className="mt-3 list-disc space-y-1 border-t border-surface/[0.06] pl-5 pt-3 text-xs text-ink-mute">
            {(d.notas_metodologicas ?? []).map((n, i) => <li key={i}>{n}</li>)}
          </ul>
        )}
      </div>

      {tramos.length > 0 && (
        <p className="mt-4 text-sm text-ink-soft">
          {tramos.map((t) => frase(t)).join(" ")}{" "}
          {mBase === "personal" ? "Parte de ese aumento es más plazas y parte es mejores remuneraciones; esta serie no los separa." : ""}
          {!homogenea && quiebre && tramos.length === 2 ? ` Los dos tramos no se encadenan por el quiebre de ${quiebre.anio}.` : ""}
        </p>
      )}

      {pbiMin !== null && pbiMax !== null && (
        <p className="mt-2 text-sm text-ink-soft">
          En soles corrientes el gasto en personal subió en {subidas} de los {Math.max(0, nominalesPersonal.length - 1)} años comparables; como porcentaje del PBI se mantiene entre {pct1(pbiMin)} y {pct1(pbiMax)} desde 2017 ({d.pbi?.fuente ?? "BCRP"}).
        </p>
      )}
      {parcial && esNum(parcial.personal_pim) && (
        <p className="mt-1 text-xs text-ink-faint">El punto bajo de {parcial.anio} no es una caída: es ejecución a la fecha. Presupuesto modificado {parcial.anio}: {money(parcial.personal_pim)}.</p>
      )}
    </>
  );
}
