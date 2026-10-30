import { useEffect, useState } from "react";
import { staticData } from "@/lib/api";
import { safeUrl } from "@/lib/safeUrl";
import type { CostoEstado } from "@/types";
import { Stat, SectionTitle, Empty, FuenteLink } from "@/components/ui";
import { useContadorVivo, solesVivo, solesM, solesEntero, enteroMiles, solesPorSegundo } from "@/lib/useContadorVivo";
import { esNum } from "@/components/costo/util";
import { Variantes } from "@/components/costo/Variantes";
import { SerieAnual } from "@/components/costo/SerieAnual";
import { Headcount } from "@/components/costo/Headcount";

const compacto = (v: number) => new Intl.NumberFormat("es-PE", { notation: "compact", maximumFractionDigits: 2 }).format(v);

export function Costo() {
  const [d, setD] = useState<CostoEstado | null>(null);
  const [estado, setEstado] = useState<"cargando" | "ok" | "error">("cargando");

  useEffect(() => {
    staticData.costoEstado()
      .then((x) => { setD(x as CostoEstado); setEstado("ok"); })
      .catch(() => setEstado("error"));
  }, []);

  const air = d?.planilla_mensual?.airhsp ?? null;
  const act = air?.activos ?? null;
  const pen = air?.pensiones ?? null;
  const conActivos = esNum(act?.masa_mensual);
  const masa = conActivos ? (act!.masa_mensual as number) : esNum(air?.masa_mensual) ? (air!.masa_mensual as number) : null;
  const habitantes = esNum(d?.poblacion?.habitantes) ? (d!.poblacion!.habitantes as number) : null;
  const { valor: vivo, pausado, alternar } = useContadorVivo(masa);

  if (estado === "cargando") return <div className="mx-auto max-w-5xl px-4 py-10"><Empty>Cargando costo del Estado…</Empty></div>;
  if (estado === "error" || !d) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-10">
        <h1 className="text-3xl font-bold tracking-tight text-ink">¿Cuánto cuesta el Estado en personal?</h1>
        <Empty>Los datos de costo aún no están publicados. Vuelve en el próximo refresco.</Empty>
      </div>
    );
  }

  const costoAnual = conActivos && esNum(act?.costo_anual) ? (act!.costo_anual as number) : masa !== null ? masa * 12 : null;
  const plazas = conActivos ? act?.registros : air?.servidores;
  const con = d.conciliacion ?? null;
  const hayConciliacion = con && [con.airhsp_activos_anual, con.mef_21_devengado_2025, con.airhsp_pensiones_anual, con.mef_22_devengado_2025].some(esNum);
  const fuentes = d.fuentes ?? [];
  const baseIpc = d.inflacion?.base ?? 2025;
  const haySerie = (d.serie_mef ?? []).some((p) => !p.parcial && (esNum(p.personal_devengado) || esNum(p.personal_incl_cas)));

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      {/* ── HERO ────────────────────────────────────────────────────────────── */}
      <div className="chip mb-3">Costo del Estado</div>
      <h1 className="text-3xl font-bold tracking-tight text-ink">¿Cuánto cuesta el Estado en personal?</h1>
      <p className="mt-2 max-w-2xl text-ink-soft">
        Lo que el Estado peruano paga cada mes en remuneraciones, en todas sus variantes, con la fuente y el período de cada cifra.
      </p>

      {masa !== null && vivo !== null ? (
        <>
          <div className="glass mt-6 p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="text-[11px] font-medium uppercase tracking-wider text-ink-mute">Desde que abriste esta página, las remuneraciones públicas costaron</div>
                <div className="tabular mt-1 break-all text-4xl font-bold tracking-tight text-accent-amber sm:text-5xl" aria-live="off">{solesVivo(vivo)}</div>
              </div>
              <button type="button" onClick={alternar} className="btn-ghost shrink-0" aria-pressed={pausado}>
                {pausado ? "▶ Reanudar" : "❚❚ Pausar"}
              </button>
            </div>
            <p className="mt-3 text-sm text-ink-soft">
              {conActivos
                ? <>Ritmo de {air?.periodo ?? "dic-2025"}, solo personal activo con plaza ocupada en Gobierno Nacional y Regional (AIRHSP-MEF). No incluye municipalidades, EsSalud ni empresas públicas. Las pensiones se muestran aparte.</>
                : <>Ritmo de {air?.periodo ?? "dic-2025"} según AIRHSP-MEF; incluye pensionistas y sobrevivientes registrados en AIRHSP porque este refresco no trae el desglose de activos.</>}
            </p>
            <p className="mt-1 text-xs text-ink-faint">Prorrateo uniforme de la masa mensual (× 12 ÷ 31 536 000 segundos): ilustra el ritmo, no es un medidor de caja.</p>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat value={solesM(masa)} label="Al mes" hint={`remuneraciones${conActivos ? " de activos" : ""}, ${air?.periodo ?? "AIRHSP"}`} accent="text-accent-amber" />
            <Stat value={costoAnual !== null ? solesM(costoAnual) : "—"} label="Al año" hint={conActivos && esNum(act?.costo_anual) ? "costo anual AIRHSP: remuneraciones + aguinaldos + aportes del empleador" : "masa mensual × 12"} />
            <Stat value={solesEntero(solesPorSegundo(masa))} label="Por segundo" hint="masa mensual × 12 ÷ 31 536 000 s" accent="text-accent-cyan" />
            <Stat
              value={habitantes ? solesEntero(masa / habitantes) : "—"}
              label="Por habitante al mes"
              hint={habitantes ? `÷ ${compacto(habitantes)} hab. (INEI${d.poblacion?.anio ? ` ${d.poblacion.anio}` : ""})` : "sin dato de población"}
            />
          </div>
          <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat value={esNum(plazas) ? enteroMiles(plazas) : "—"} label={conActivos ? "Plazas activas ocupadas" : "Registros AIRHSP"} hint={conActivos ? "GN + GR, AIRHSP" : "incluye pensionistas"} />
            {conActivos && esNum(air?.total_registros) && <Stat value={enteroMiles(air!.total_registros as number)} label="Registros AIRHSP en total" hint="activos + pensiones + formativa + vacantes" />}
            {esNum(air?.formativa?.registros) && <Stat value={enteroMiles(air!.formativa!.registros as number)} label="Modalidades formativas" hint={esNum(air?.formativa?.masa_mensual) ? `${solesM(air!.formativa!.masa_mensual as number)} al mes` : "practicantes, residentes"} />}
            {esNum(air?.vacantes?.plazas) && <Stat value={enteroMiles(air!.vacantes!.plazas as number)} label="Plazas vacantes" hint={esNum(air?.vacantes?.masa_mensual) ? `${solesM(air!.vacantes!.masa_mensual as number)} presupuestados al mes` : "sin ocupar"} />}
          </div>
        </>
      ) : (
        <Empty>La masa mensual AIRHSP no está disponible en este refresco.</Empty>
      )}

      {/* ── PENSIONES ───────────────────────────────────────────────────────── */}
      {pen && esNum(pen.masa_mensual) && (
        <section className="mt-12">
          <SectionTitle kicker="Pensiones">Lo que el Estado paga a quienes ya no trabajan</SectionTitle>
          <div className="glass p-6">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Stat value={solesM(pen.masa_mensual)} label="Pensiones al mes" hint={air?.periodo ?? "AIRHSP"} accent="text-accent-cyan" />
              <Stat value={esNum(pen.costo_anual) ? solesM(pen.costo_anual) : solesM(pen.masa_mensual * 12)} label="Al año" hint={esNum(pen.costo_anual) ? "costo anual AIRHSP" : "masa mensual × 12"} />
              <Stat value={esNum(pen.registros) ? enteroMiles(pen.registros) : "—"} label="Beneficiarios" hint="pensionistas y sobrevivientes" />
              <Stat value={esNum(pen.prom) ? solesEntero(pen.prom) : esNum(pen.registros) && pen.registros > 0 ? solesEntero(pen.masa_mensual / pen.registros) : "—"} label="Pensión promedio" hint="al mes" />
            </div>
            {(pen.detalle ?? []).length > 0 && (
              <table className="mt-4 w-full text-sm">
                <thead><tr className="text-left text-[11px] uppercase tracking-wider text-ink-mute"><th className="pb-2 font-medium">Tipo</th><th className="pb-2 text-right font-medium">Beneficiarios</th><th className="pb-2 text-right font-medium">Masa mensual</th></tr></thead>
                <tbody>
                  {(pen.detalle ?? []).map((t, i) => (
                    <tr key={`${t.tipo}-${i}`} className="border-t border-surface/[0.06]">
                      <td className="py-1.5 text-ink-soft">{t.tipo}</td>
                      <td className="tabular py-1.5 text-right text-ink">{esNum(t.n) ? enteroMiles(t.n) : "—"}</td>
                      <td className="tabular py-1.5 text-right text-ink">{esNum(t.masa) ? solesM(t.masa) : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <p className="mt-3 text-xs text-ink-faint">Registros de pensionistas y sobrevivientes en AIRHSP (regímenes a cargo del Tesoro, GN+GR). No incluye ONP ni AFP. Fuente: {air?.fuente ?? "AIRHSP — MEF"}.</p>
          </div>
        </section>
      )}

      {/* ── VARIANTES ───────────────────────────────────────────────────────── */}
      <Variantes d={d} />

      {/* ── QUÉ CUBRE CADA FUENTE ───────────────────────────────────────────── */}
      <section className="mt-12">
        <SectionTitle kicker="Cobertura">Qué cubre cada fuente</SectionTitle>
        <div className="glass overflow-x-auto p-5">
          <table className="w-full min-w-[520px] text-sm">
            <thead><tr className="text-left text-[11px] uppercase tracking-wider text-ink-mute"><th className="pb-2 font-medium">Fuente</th><th className="pb-2 font-medium">Cubre</th><th className="pb-2 font-medium">No cubre</th><th className="pb-2 font-medium">Sirve para</th></tr></thead>
            <tbody className="align-top">
              <tr className="border-t border-surface/[0.06]"><td className="py-2 font-medium text-ink">AIRHSP</td><td className="py-2 text-ink-soft">Gobierno Nacional + Regional{air?.cobertura ? ` (${air.cobertura})` : ""}; plazas, pensiones, formativa</td><td className="py-2 text-ink-soft">Municipalidades, EsSalud, empresas públicas</td><td className="py-2 text-ink-soft">Costo mensual actual; la más completa para GN y GR</td></tr>
              <tr className="border-t border-surface/[0.06]"><td className="py-2 font-medium text-ink">MEF genérica 2.1</td><td className="py-2 text-ink-soft">GN + GR + Gobiernos Locales, devengado anual</td><td className="py-2 text-ink-soft">FONAFE, EsSalud</td><td className="py-2 text-ink-soft">Serie comparable 2015→hoy (con quiebre CAS 2024)</td></tr>
              <tr className="border-t border-surface/[0.06]"><td className="py-2 font-medium text-ink">PTE</td><td className="py-2 text-ink-soft">Entidades que publican planilla con nombre (646 en el barrido)</td><td className="py-2 text-ink-soft">Docentes, FF.AA., PNP, entidades que no publican</td><td className="py-2 text-ink-soft">Ver quién cobra cuánto, no totales</td></tr>
              <tr className="border-t border-surface/[0.06]"><td className="py-2 font-medium text-ink">OCDS (locadores)</td><td className="py-2 text-ink-soft">Órdenes de servicio publicadas{d.planilla_mensual?.locadores?.cobertura ? ` (${d.planilla_mensual.locadores.cobertura})` : ""}</td><td className="py-2 text-ink-soft">La mayor parte de locadores</td><td className="py-2 text-ink-soft">Muestra, no universo</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* ── CONTADOR DE AÑOS ────────────────────────────────────────────────── */}
      <section className="mt-12">
        <SectionTitle kicker="El contador de años">¿Cada año cuesta más?</SectionTitle>
        {haySerie ? <SerieAnual d={d} /> : (
          <div className="glass p-6">
            <div className="font-semibold text-ink">Serie anual MEF en construcción</div>
            <p className="mt-1 text-sm text-ink-mute">Cuando la consulta al portal de Transparencia Económica del MEF esté publicada, aquí aparecerá la evolución 2015→2026 del gasto en personal (genérica 2.1).</p>
          </div>
        )}
      </section>

      {/* ── HEADCOUNT ───────────────────────────────────────────────────────── */}
      <Headcount d={d} />

      {/* ── CONCILIACIÓN ────────────────────────────────────────────────────── */}
      {hayConciliacion && con && (
        <section className="mt-12">
          <SectionTitle kicker="Conciliación">¿Cuadran las fuentes?</SectionTitle>
          <div className="glass p-5 text-sm text-ink-soft">
            <p>
              {esNum(con.airhsp_activos_anual) ? <>AIRHSP activos <b className="tabular text-ink">{solesM(con.airhsp_activos_anual)}</b> al año (GN+GR)</> : null}
              {esNum(con.airhsp_activos_anual) && esNum(con.mef_21_devengado_2025) ? " · " : null}
              {esNum(con.mef_21_devengado_2025) ? <>MEF genérica 2.1 <b className="tabular text-ink">{solesM(con.mef_21_devengado_2025)}</b> (2025, incluye municipalidades)</> : null}
              {(esNum(con.airhsp_activos_anual) || esNum(con.mef_21_devengado_2025)) && (esNum(con.airhsp_pensiones_anual) || esNum(con.mef_22_devengado_2025)) ? " · " : null}
              {esNum(con.airhsp_pensiones_anual) ? <>pensiones AIRHSP <b className="tabular text-ink">{solesM(con.airhsp_pensiones_anual)}</b></> : null}
              {esNum(con.airhsp_pensiones_anual) && esNum(con.mef_22_devengado_2025) ? " ≈ " : null}
              {esNum(con.mef_22_devengado_2025) ? <>MEF 2.2 <b className="tabular text-ink">{solesM(con.mef_22_devengado_2025)}</b> (2025)</> : null}.
            </p>
            {con.nota && <p className="mt-2 text-xs text-ink-faint">{con.nota}</p>}
          </div>
        </section>
      )}

      {/* ── METODOLOGÍA Y FUENTES ───────────────────────────────────────────── */}
      <section className="mt-12">
        <SectionTitle kicker="Metodología y fuentes">Cómo leer estas cifras</SectionTitle>
        <div className="glass p-6">
          <ul className="list-disc space-y-2 pl-5 text-sm text-ink-soft">
            <li><b className="text-ink">La planilla PTE no es comparable entre años.</b> Su cobertura crece con cada barrido y depende de lo que cada entidad publica; un aumento puede ser solo más entidades cumpliendo.</li>
            <li><b className="text-ink">El AIRHSP es la fuente más completa para Gobierno Nacional y Regional.</b> Registra las plazas financiadas con fondos públicos de esos dos niveles, incluidas las que el PTE no publica (docentes, FF.AA., PNP); no cubre municipalidades, EsSalud ni empresas públicas.</li>
            <li><b className="text-ink">La serie comparable es la genérica 2.1 del MEF</b> (personal y obligaciones sociales, devengado), consultada año por año en Transparencia Económica. En 2024 el CAS pasó de la genérica 2.3 a la 2.1 (Ley 31953); la serie homogénea suma el CAS a los años anteriores. El año en curso es parcial.</li>
            <li><b className="text-ink">Soles de {baseIpc}:</b> deflactor IPC Lima Metropolitana del BCRP, base {baseIpc}. Por habitante: población INEI de cada año. Ninguna cifra separa cuánto es más plazas y cuánto es mejores remuneraciones, salvo la serie AIRHSP de plazas y promedio.</li>
          </ul>

          {fuentes.length > 0 && (
            <>
              <div className="mt-5 text-[11px] font-medium uppercase tracking-wider text-ink-mute">Fuentes</div>
              <ul className="mt-2 space-y-1.5 break-words text-sm">
                {fuentes.map((f, i) => (
                  <li key={`${f.nombre}-${i}`} className="text-ink-soft">
                    <FuenteLink url={f.url} className="font-medium text-accent-cyan hover:underline" fallbackClassName="font-medium text-ink" fallback={f.nombre}>
                      {f.nombre} ↗
                    </FuenteLink>
                    {f.nota ? <span className="text-ink-mute"> — {f.nota}</span> : null}
                  </li>
                ))}
                {safeUrl(d.pbi?.url) && <li className="text-ink-soft"><FuenteLink url={d.pbi?.url} className="font-medium text-accent-cyan hover:underline">{d.pbi?.fuente ?? "BCRP, remuneraciones % PBI"} ↗</FuenteLink></li>}
              </ul>
            </>
          )}
          <p className="mt-4 text-xs text-ink-faint">
            Datos generados el {new Date(d.generated_at).toLocaleDateString("es-PE", { day: "2-digit", month: "short", year: "numeric" })}. Solo información pública, trazable a la fuente.
          </p>
        </div>
      </section>
    </div>
  );
}
