import { useEffect, useMemo, useState } from "react";
import { historicoApi, type HistEstado, type HistPersona, type HistTrayectoria } from "@/lib/api";
import { fmt, money, Empty } from "@/components/ui";

const MESES = ["", "ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "set", "oct", "nov", "dic"];
const periodo = (anio: number, mes: number) => (mes >= 1 && mes <= 12 ? `${MESES[mes]} ${anio}` : `${anio}`);

export function Historico() {
  const [estado, setEstado] = useState<HistEstado | null>(null);
  const [caido, setCaido] = useState(false);
  const [q, setQ] = useState("");
  const [items, setItems] = useState<HistPersona[]>([]);
  const [buscando, setBuscando] = useState(false);
  const [sel, setSel] = useState<string | null>(null);
  const [selNombre, setSelNombre] = useState("");
  const [tray, setTray] = useState<HistTrayectoria | null>(null);
  const [cargandoTray, setCargandoTray] = useState(false);

  useEffect(() => {
    historicoApi.estado().then((x) => setEstado(x)).catch(() => setCaido(true));
  }, []);

  // búsqueda con debounce
  useEffect(() => {
    const nq = q.trim();
    if (nq.length < 2) { setItems([]); return; }
    setBuscando(true);
    const t = setTimeout(() => {
      historicoApi.personas(nq, 40)
        .then((x) => setItems(x.items))
        .catch(() => { setItems([]); setCaido(true); })
        .finally(() => setBuscando(false));
    }, 300);
    return () => clearTimeout(t);
  }, [q]);

  const abrir = (p: HistPersona) => {
    setSel(p.persona_norm);
    setSelNombre(p.persona);
    setTray(null);
    setCargandoTray(true);
    historicoApi.persona(p.persona)
      .then((x) => setTray(x))
      .catch(() => setTray(null))
      .finally(() => setCargandoTray(false));
  };

  const totales = useMemo(() => {
    if (!tray) return null;
    const conMonto = tray.periodos.filter((x) => x.total != null);
    if (!conMonto.length) return null;
    const montos = conMonto.map((x) => x.total as number);
    return { min: Math.min(...montos), max: Math.max(...montos), n: tray.periodos.length };
  }, [tray]);

  if (caido && !estado) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-10">
        <div className="chip mb-3">Histórico</div>
        <h1 className="text-3xl font-bold tracking-tight text-ink">Trayectoria histórica</h1>
        <Empty>El servicio de histórico no está disponible ahora mismo. Intenta de nuevo en unos minutos.</Empty>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <div className="chip mb-3">Histórico · planilla del Estado {estado ? `${estado.resumen.anio_min}–${estado.resumen.anio_max}` : ""}</div>
      <h1 className="text-3xl font-bold tracking-tight text-ink">Trayectoria en el Estado</h1>
      <p className="mt-2 max-w-2xl text-ink-soft">
        Busca a una persona y mira su <b>sueldo a lo largo del tiempo</b>, en qué <b>entidades</b> trabajó y sus{" "}
        <b>cambios de cargo</b>. Serie histórica de planilla pública servida en vivo desde la base del proyecto.
      </p>

      {estado && (
        <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="glass p-4"><div className="tabular text-2xl font-bold text-ink">{fmt.format(estado.resumen.personas)}</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">personas</div></div>
          <div className="glass p-4"><div className="tabular text-2xl font-bold text-accent-cyan">{fmt.format(estado.resumen.planilla_filas)}</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">registros de planilla</div></div>
          <div className="glass p-4"><div className="tabular text-2xl font-bold text-accent-blue">{estado.resumen.anio_min}–{estado.resumen.anio_max}</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">periodo</div></div>
          <div className="glass p-4"><div className="tabular text-2xl font-bold text-accent-amber">{fmt.format(estado.resumen.designaciones)}</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">designaciones</div></div>
        </div>
      )}

      <div className="mt-6">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          inputMode="search"
          autoComplete="off"
          placeholder="🔎 Buscar persona por nombre (apellidos, nombres)…"
          className="input w-full text-base"
        />
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
        {/* resultados */}
        <div>
          {q.trim().length < 2 ? (
            <Empty>Escribe al menos 2 letras del nombre.</Empty>
          ) : buscando ? (
            <Empty>Buscando…</Empty>
          ) : items.length === 0 ? (
            <Empty>Sin coincidencias.</Empty>
          ) : (
            <div className="glass divide-y divide-surface/[0.05] overflow-hidden">
              {items.map((p) => (
                <button
                  key={p.persona_norm}
                  onClick={() => abrir(p)}
                  className={`block w-full px-4 py-3 text-left transition hover:bg-surface/[0.04] ${sel === p.persona_norm ? "bg-surface/[0.06]" : ""}`}
                >
                  <div className="font-medium text-ink">{p.persona}</div>
                  <div className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[11px] text-ink-soft">
                    <span>{p.entidad || "—"}</span>
                    {p.cargo && <span className="text-ink-faint">· {p.cargo}</span>}
                    <span className="text-ink-faint">· {periodo(p.anio, p.mes)}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* detalle */}
        <div>
          {!sel ? (
            <Empty>Selecciona una persona para ver su trayectoria.</Empty>
          ) : cargandoTray ? (
            <Empty>Cargando trayectoria…</Empty>
          ) : !tray || tray.periodos.length === 0 ? (
            <Empty>Sin registros de trayectoria.</Empty>
          ) : (
            <div className="space-y-5">
              <div className="glass p-4">
                <div className="text-lg font-bold text-ink">{selNombre || sel}</div>
                {totales && (
                  <div className="mt-1 text-[12px] text-ink-soft">
                    {totales.n} periodos · sueldo entre <b className="tabular">{money(totales.min)}</b> y{" "}
                    <b className="tabular">{money(totales.max)}</b>
                  </div>
                )}
              </div>

              {tray.cambios_puesto.length > 0 && (
                <div className="glass p-4">
                  <div className="mb-2 text-[11px] uppercase tracking-wider text-ink-mute">Cambios de puesto</div>
                  <ol className="space-y-2">
                    {tray.cambios_puesto.map((c, i) => (
                      <li key={i} className="text-[13px]">
                        <span className="tabular text-ink-faint">{c.periodo?.slice(0, 7)}</span>{" "}
                        <span className="text-ink-soft">{c.cargo_prev}</span>
                        <span className="mx-1 text-accent-cyan">→</span>
                        <span className="text-ink">{c.cargo_actual}</span>
                        {c.cambio_entidad && (
                          <div className="ml-14 text-[11px] text-ink-faint">{c.entidad_prev || "—"} → {c.entidad_actual || "—"}</div>
                        )}
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              <div className="glass overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-surface/[0.06] text-left text-xs uppercase tracking-wide text-ink-mute">
                      <th className="px-4 py-3">Periodo</th>
                      <th className="px-4 py-3">Entidad / cargo</th>
                      <th className="px-4 py-3 text-right">Sueldo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...tray.periodos].reverse().map((p, i) => (
                      <tr key={i} className="border-b border-surface/[0.04] last:border-0">
                        <td className="px-4 py-3 tabular text-ink-soft">{periodo(p.anio, p.mes)}</td>
                        <td className="px-4 py-3">
                          <div className="text-[13px] text-ink">{p.entidad || "—"}</div>
                          <div className="mt-0.5 flex flex-wrap items-center gap-1.5">
                            <span className="text-[11px] text-ink-soft">{p.cargo || "—"}</span>
                            {p.regimen && <span className="text-[10px] text-ink-faint">· {p.regimen}</span>}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right tabular font-semibold text-ink">
                          {p.total != null ? money(p.total) : <span className="text-[11px] font-normal text-ink-faint">—</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>

      <p className="mt-6 text-[11px] text-ink-faint">
        Fuente: planilla del Portal de Transparencia Estándar (remuneraciones públicas), serie {estado ? `${estado.resumen.anio_min}–${estado.resumen.anio_max}` : "histórica"}.
        Los cambios de puesto se infieren comparando periodos consecutivos (rotación/ascenso/traslado);
        no imputan irregularidad alguna. Solo información pública · trazable a la fuente.
      </p>
    </div>
  );
}
