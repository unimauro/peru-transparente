import { useEffect, useMemo, useRef, useState } from "react";
import { staticData } from "@/lib/api";
import { fmt, Empty } from "@/components/ui";

interface Resumen {
  fuente: string;
  advertencia: string;
  total_sanciones: number;
  total_personas: number;
  por_tipo: [string, number][];
  por_sector: [string, number][];
  top_entidades: [string, number][];
}
interface Match {
  tipo: string; entidad: string; causa: string; fecha_fin: string;
  dni_masked: string; homonimo_posible: boolean;
}
type Indice = { _meta: Record<string, unknown>; index: Record<string, Match[]> };

// Agrupa los tipos largos del RNSSC en familias legibles para la barra.
function familia(tipo: string): string {
  const t = tipo.toUpperCase();
  if (t.includes("IMPEDIMENTO PERMANENTE")) return "Impedimento permanente (D.L. 1295)";
  if (t.includes("DESTITU")) return "Destitución";
  if (t.includes("DOCENTE") || t.includes("29988") || t.includes("ART. 36 CP")) return "Inhabilitación (docente / penal)";
  if (t.includes("SUSPEN")) return "Suspensión";
  if (t.includes("INHABILITA")) return "Inhabilitación";
  if (t.includes("MULTA")) return "Multa";
  if (t.includes("AMONESTA")) return "Amonestación";
  return "Otra";
}

const COLORS = ["#e4572e", "#3b82f6", "#06b6d4", "#f59e0b", "#a855f7", "#22c55e", "#64748b", "#94a3b8"];

function Barra({ data, total }: { data: [string, number][]; total: number }) {
  return (
    <div className="space-y-2">
      {data.map(([label, n], i) => (
        <div key={label} className="flex items-center gap-3">
          <div className="w-48 shrink-0 truncate text-xs text-ink-soft sm:w-56" title={label}>{label}</div>
          <div className="h-4 flex-1 overflow-hidden rounded bg-surface/[0.06]">
            <div className="h-full rounded" style={{ width: `${Math.max(2, (n / total) * 100)}%`, background: COLORS[i % COLORS.length] }} />
          </div>
          <div className="w-14 shrink-0 text-right tabular text-xs text-ink-mute">{fmt.format(n)}</div>
        </div>
      ))}
    </div>
  );
}

export function Sanciones() {
  const [d, setD] = useState<Resumen | null>(null);
  const [q, setQ] = useState("");
  const [idx, setIdx] = useState<Record<string, Match[]>>({});
  const [loadingIdx, setLoadingIdx] = useState(false);
  const shardCache = useRef<Record<string, Record<string, Match[]>>>({});

  useEffect(() => { staticData.sanciones().then((x) => setD(x as Resumen)).catch(() => {}); }, []);

  // El índice va shardeado por inicial; se carga solo el shard de la letra consultada.
  useEffect(() => {
    const nq = q.trim().toUpperCase().normalize("NFKD").replace(/[̀-ͯ]/g, "");
    if (nq.length < 3) return;
    const letra = /[A-Z]/.test(nq[0]) ? nq[0] : "_";
    if (shardCache.current[letra]) { setIdx(shardCache.current[letra]); return; }
    setLoadingIdx(true);
    staticData.sancionesShard(letra)
      .then((x) => { shardCache.current[letra] = (x as Indice).index; setIdx(shardCache.current[letra]); })
      .catch(() => { shardCache.current[letra] = {}; })
      .finally(() => setLoadingIdx(false));
  }, [q]);

  const porFamilia = useMemo(() => {
    if (!d) return [] as [string, number][];
    const m = new Map<string, number>();
    for (const [tipo, n] of d.por_tipo) m.set(familia(tipo), (m.get(familia(tipo)) || 0) + n);
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  }, [d]);

  const resultados = useMemo(() => {
    const nq = q.trim().toUpperCase().normalize("NFKD").replace(/[̀-ͯ]/g, "");
    if (nq.length < 3) return [] as [string, Match[]][];
    return Object.entries(idx).filter(([nombre]) => nombre.includes(nq)).slice(0, 100);
  }, [idx, q]);

  if (!d) return <div className="mx-auto max-w-5xl px-4 py-10"><Empty>Cargando…</Empty></div>;

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <div className="chip mb-3">Sanciones · RNSSC / SERVIR</div>
      <h1 className="text-3xl font-bold tracking-tight text-ink">Servidores sancionados</h1>
      <p className="mt-2 max-w-2xl text-ink-soft">
        Registro Nacional de Sanciones contra Servidores Civiles (RNSSC). Muestra las sanciones
        <b> vigentes</b> al momento de la última actualización: destituciones, inhabilitaciones,
        suspensiones y multas de funcionarios y servidores públicos.
      </p>

      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
        <div className="glass p-4"><div className="tabular text-2xl font-bold text-peru-redsoft">{fmt.format(d.total_sanciones)}</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">sanciones vigentes</div></div>
        <div className="glass p-4"><div className="tabular text-2xl font-bold text-ink">{fmt.format(d.total_personas)}</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">personas</div></div>
        <div className="glass p-4"><div className="tabular text-2xl font-bold text-accent-cyan">{fmt.format(d.por_tipo.length)}</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">tipos de sanción</div></div>
      </div>

      <div className="mt-5 rounded-xl border border-accent-amber/30 bg-accent-amber/[0.06] px-4 py-3 text-[13px] text-ink-soft">
        ⚠️ {d.advertencia}
      </div>

      <div className="mt-6">
        <div className="mb-2 text-xs uppercase tracking-wide text-ink-mute">Por tipo de sanción</div>
        <div className="glass p-4"><Barra data={porFamilia} total={d.total_sanciones} /></div>
      </div>

      <div className="mt-6 grid gap-5 lg:grid-cols-2">
        <div>
          <div className="mb-2 text-xs uppercase tracking-wide text-ink-mute">Por sector (top 10)</div>
          <div className="glass p-4"><Barra data={d.por_sector.slice(0, 10)} total={d.por_sector[0]?.[1] || 1} /></div>
        </div>
        <div>
          <div className="mb-2 text-xs uppercase tracking-wide text-ink-mute">Entidades sancionadoras (top 10)</div>
          <div className="glass p-4"><Barra data={d.top_entidades.slice(0, 10)} total={d.top_entidades[0]?.[1] || 1} /></div>
        </div>
      </div>

      <div className="mt-8">
        <div className="mb-2 text-xs uppercase tracking-wide text-ink-mute">Buscar persona sancionada</div>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          inputMode="search"
          autoComplete="off"
          placeholder="🔎 Buscar por APELLIDO… (ej. Quispe, Vásquez)"
          className="input w-full text-base"
        />
        {loadingIdx && <p className="mt-2 text-xs text-ink-mute">Cargando índice…</p>}
        {q.trim().length >= 3 && !loadingIdx && (
          resultados.length === 0 ? (
            <Empty>Sin coincidencias en el registro.</Empty>
          ) : (
            <div className="glass mt-3 max-h-[520px] divide-y divide-surface/[0.05] overflow-y-auto">
              {resultados.map(([nombre, ms]) => (
                <div key={nombre} className="px-4 py-3">
                  <div className="font-medium text-ink">{nombre}</div>
                  <div className="mt-1 space-y-1">
                    {ms.map((m, i) => (
                      <div key={i} className="flex flex-wrap items-center gap-x-2 text-[12px] text-ink-soft">
                        <span className="rounded bg-peru-red/15 px-1.5 py-0.5 text-[11px] text-peru-redsoft">{familia(m.tipo)}</span>
                        <span className="text-ink-mute">{m.entidad}</span>
                        {m.fecha_fin && <span className="text-ink-faint">· hasta {m.fecha_fin}</span>}
                        <span className="text-ink-faint">· DNI {m.dni_masked}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )
        )}
      </div>

      <p className="mt-5 text-[11px] text-ink-faint">
        Fuente: RNSSC — SERVIR (<a className="underline hover:text-ink-soft" href="https://www.sanciones.gob.pe/rnssc/" target="_blank" rel="noreferrer">sanciones.gob.pe</a>).
        Solo sanciones <b>vigentes</b>. El buscador de este portal cruza por <b>nombre</b>: una coincidencia
        es un <b>homónimo posible</b>, no un hecho confirmado — verifica la identidad (DNI) en la fuente oficial
        antes de afirmar nada. El DNI se muestra enmascarado por privacidad.
      </p>
    </div>
  );
}
