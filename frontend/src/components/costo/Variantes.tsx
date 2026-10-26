import ReactECharts from "echarts-for-react";
import type { CostoEstado } from "@/types";
import { fmt, SectionTitle } from "@/components/ui";
import { solesM, solesEntero, enteroMiles, ejeSoles } from "@/lib/useContadorVivo";
import { esNum, esc, baseAxis, AMBAR, CIAN, VIOLETA } from "./util";

type Fila = { nombre: string; n: number | null; masa: number | null; prom: number | null };

/** Barras horizontales de masa mensual por categoría (régimen / nivel / sector), con n y promedio en el tooltip. */
function Barras({ filas, color, periodo }: { filas: Fila[]; color: string; periodo?: string | null }) {
  const datos = [...filas].filter((r) => esNum(r.masa)).sort((a, b) => (a.masa as number) - (b.masa as number));
  if (!datos.length) return null;
  const option = {
    grid: { left: 8, right: 24, top: 8, bottom: 24, containLabel: true },
    tooltip: {
      trigger: "axis", axisPointer: { type: "shadow" },
      formatter: (params: { dataIndex: number }[] | { dataIndex: number }) => {
        const p = Array.isArray(params) ? params[0] : params;
        const r = datos[p.dataIndex];
        if (!r) return "";
        return `<b>${esc(r.nombre)}</b><br/>Masa mensual: ${solesM(r.masa as number)}<br/>Plazas: ${esNum(r.n) ? enteroMiles(r.n) : "—"}<br/>Promedio: ${esNum(r.prom) ? solesEntero(r.prom) : esNum(r.n) && r.n > 0 ? solesEntero((r.masa as number) / r.n) : "—"}`;
      },
    },
    xAxis: { type: "value", ...baseAxis, axisLabel: { ...baseAxis.axisLabel, formatter: (v: number) => `S/ ${ejeSoles(v)}` } },
    yAxis: { type: "category", data: datos.map((r) => r.nombre), ...baseAxis, axisLabel: { ...baseAxis.axisLabel, width: 150, overflow: "truncate" } },
    series: [{ type: "bar", data: datos.map((r) => r.masa), itemStyle: { color, borderRadius: [0, 4, 4, 0] }, barWidth: "60%" }],
  };
  return (
    <>
      <p className="-mt-2 mb-2 text-xs text-ink-mute">Pasa el cursor o toca una barra para ver plazas y promedio.{periodo ? ` Período: ${periodo}.` : ""}</p>
      <ReactECharts option={option} notMerge style={{ height: Math.max(200, datos.length * 30 + 50) }} />
    </>
  );
}

function Dato({ k, v }: { k: string; v: string }) {
  return <div className="flex justify-between gap-2"><dt className="text-ink-mute">{k}</dt><dd className="tabular text-ink">{v}</dd></div>;
}

export function Variantes({ d }: { d: CostoEstado }) {
  const air = d.planilla_mensual?.airhsp ?? null;
  const act = air?.activos ?? null;
  const pte = d.planilla_mensual?.pte ?? null;
  const loc = d.planilla_mensual?.locadores ?? null;
  const conActivos = esNum(act?.masa_mensual);

  const masaA = conActivos ? (act!.masa_mensual as number) : esNum(air?.masa_mensual) ? (air!.masa_mensual as number) : null;
  const regA = conActivos ? act?.registros : air?.servidores;
  const promA = conActivos && esNum(act?.prom) ? act!.prom : masaA !== null && esNum(regA) && regA > 0 ? masaA / regA : null;

  const regimenes: Fila[] = ((conActivos ? act?.por_regimen : air?.por_regimen) ?? []).map((r) => ({ nombre: r.regimen, n: r.n, masa: r.masa, prom: r.prom }));
  const niveles: Fila[] = (act?.por_nivel ?? []).map((r) => ({ nombre: r.nivel, n: r.n, masa: r.masa, prom: r.prom }));
  const sectores: Fila[] = [...(act?.por_sector ?? [])].filter((r) => esNum(r.masa)).sort((a, b) => (b.masa as number) - (a.masa as number)).slice(0, 12)
    .map((r) => ({ nombre: r.sector, n: r.n, masa: r.masa, prom: r.prom }));

  // Universo real de locación de servicios (MEF 2.3.2.9) del último año cerrado, si viene en la serie.
  const locMef = [...(d.serie_mef ?? [])].filter((p) => !p.parcial && esNum(p.locacion_23_devengado)).sort((a, b) => b.anio - a.anio)[0] ?? null;

  return (
    <section className="mt-12">
      <SectionTitle kicker="Las variantes">Tres formas de medir la planilla</SectionTitle>
      <p className="-mt-2 mb-4 text-sm text-ink-mute">No son sumables entre sí: cada una cubre un universo distinto y un período distinto.</p>

      <div className="grid gap-4 md:grid-cols-2">
        <article className="glass p-5">
          <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-accent-amber">{conActivos ? "AIRHSP · remuneraciones de activos" : "AIRHSP · total registrado"}</div>
          <div className="tabular mt-2 text-2xl font-bold text-ink">{masaA !== null ? solesM(masaA) : "—"}</div>
          <div className="text-xs text-ink-mute">al mes{air?.periodo ? ` · ${air.periodo}` : ""}</div>
          <dl className="mt-3 space-y-1 text-sm">
            <Dato k={conActivos ? "Plazas activas ocupadas" : "Registros"} v={esNum(regA) ? enteroMiles(regA) : "—"} />
            <Dato k={conActivos ? "Promedio activos" : "Promedio"} v={promA !== null ? solesEntero(promA) : "—"} />
            {conActivos && esNum(act?.costo_anual) && <Dato k="Costo anual" v={solesM(act!.costo_anual as number)} />}
            {conActivos && esNum(air?.total_registros) && <Dato k="Total de registros AIRHSP" v={enteroMiles(air!.total_registros as number)} />}
          </dl>
          <p className="mt-3 text-xs text-ink-faint">
            {conActivos
              ? `Personal activo con plaza ocupada en Gobierno Nacional y Regional${air?.cobertura ? ` (${air.cobertura})` : ""}; incluye docentes, salud, FF.AA. y PNP que el PTE no publica. Pensiones aparte.`
              : "Incluye pensionistas y sobrevivientes registrados en AIRHSP; el desglose activos/pensiones no está disponible en este refresco."}{" "}
            Fuente: {air?.fuente ?? "AIRHSP — MEF"}.
          </p>
        </article>

        <article className="glass p-5">
          <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-accent-cyan">PTE · planilla nominal publicada</div>
          <div className="tabular mt-2 text-2xl font-bold text-ink">{esNum(pte?.masa_mensual) ? solesM(pte!.masa_mensual as number) : "—"}</div>
          <div className="text-xs text-ink-mute">al mes · último mes publicado por entidad{pte?.periodo ? ` (${pte.periodo})` : ""}</div>
          <dl className="mt-3 space-y-1 text-sm">
            <Dato k="Con nombre y sueldo publicado" v={esNum(pte?.servidores_con_sueldo) ? fmt.format(pte!.servidores_con_sueldo as number) : "—"} />
            <Dato k="Promedio" v={esNum(pte?.masa_mensual) && esNum(pte?.servidores_con_sueldo) && (pte!.servidores_con_sueldo as number) > 0 ? solesEntero((pte!.masa_mensual as number) / (pte!.servidores_con_sueldo as number)) : "—"} />
          </dl>
          <p className="mt-3 text-xs text-ink-faint">Solo lo que cada entidad publica persona por persona en su portal de transparencia; la cobertura es parcial y crece con el barrido, por eso no sirve para comparar años. Fuente: {pte?.fuente ?? "PTE"}.</p>
        </article>
      </div>

      {regimenes.length > 0 && (
        <div className="glass mt-4 p-5">
          <SectionTitle kicker={conActivos ? "Activos por régimen" : "AIRHSP por régimen"}>Masa mensual según régimen laboral</SectionTitle>
          <Barras filas={regimenes} color={AMBAR} periodo={air?.periodo} />
        </div>
      )}
      {(niveles.length > 0 || sectores.length > 0) && (
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          {niveles.length > 0 && (
            <div className="glass p-5">
              <SectionTitle kicker="Activos por nivel">Nacional vs. regional</SectionTitle>
              <Barras filas={niveles} color={CIAN} periodo={air?.periodo} />
            </div>
          )}
          {sectores.length > 0 && (
            <div className="glass p-5">
              <SectionTitle kicker="Activos por sector">Los 12 sectores con mayor masa</SectionTitle>
              <Barras filas={sectores} color={VIOLETA} periodo={air?.periodo} />
            </div>
          )}
        </div>
      )}

      {(loc || locMef) && (
        <article className="glass mt-4 border-dashed p-5">
          <div className="flex flex-wrap items-center gap-2">
            <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-accent-violet">Locadores · órdenes de servicio</div>
            <span className="chip text-[10px]">Muestra OCDS, cobertura parcial; no es el universo de locadores</span>
          </div>
          <div className="mt-3 grid gap-4 sm:grid-cols-2">
            {loc && (
              <div>
                <div className="tabular text-xl font-bold text-ink">{esNum(loc.monto_total) ? solesM(loc.monto_total) : "—"}</div>
                <div className="text-xs text-ink-mute">monto total de órdenes{loc.periodo ? ` · ${loc.periodo}` : ""}</div>
                <dl className="mt-2 space-y-1 text-sm">
                  <Dato k="Órdenes" v={esNum(loc.ordenes) ? fmt.format(loc.ordenes) : "—"} />
                  {esNum(loc.locadores) && <Dato k="Personas (locadores)" v={fmt.format(loc.locadores)} />}
                  <Dato k="Monto por orden" v={esNum(loc.monto_total) && esNum(loc.ordenes) && loc.ordenes > 0 ? solesEntero(loc.monto_total / loc.ordenes) : "—"} />
                </dl>
                <p className="mt-2 text-xs text-ink-faint">{loc.nota ?? "Monto total de órdenes de servicio; la duración del contrato no está informada, por eso no se convierte a costo mensual."}{loc.cobertura ? ` Cobertura: ${loc.cobertura}.` : ""} Fuente: {loc.fuente ?? "OECE/OCDS"}.</p>
              </div>
            )}
            {locMef && (
              <div>
                <div className="tabular text-xl font-bold text-ink">{solesM(locMef.locacion_23_devengado as number)}</div>
                <div className="text-xs text-ink-mute">universo MEF {locMef.anio}, devengado anual</div>
                <p className="mt-2 text-xs text-ink-faint">Específica 2.3.2.9 "Locación de servicios por persona natural", Gobierno Nacional + Regional + Local, último año cerrado. Es el universo real de locadores que el presupuesto registra; la muestra OCDS de la izquierda es solo una fracción.</p>
              </div>
            )}
          </div>
        </article>
      )}
    </section>
  );
}
