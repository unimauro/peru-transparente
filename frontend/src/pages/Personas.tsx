import { useEffect, useRef, useState } from "react";
import { staticData } from "@/lib/api";
import { fmt, money, Empty } from "@/components/ui";
import { PersonaGrafo } from "@/components/PersonaGrafo";
import { RedInstitucional } from "@/components/RedInstitucional";

type Ap = [string, string, string, string, number, string]; // id, abrev, cargo, regimen, sueldo, año
type Persona = [string, number, Ap[]];                       // nombre, n_entidades, apariciones
interface Sancion {
  tipo: string; entidad: string; causa: string; fecha_fin: string;
  dni_masked: string; homonimo_posible: boolean;
}
interface Dj { entidad: string; cargo: string; fecha: string; codigo: string; }

export function Personas() {
  const [red, setRed] = useState<Persona[]>([]);
  const [q, setQ] = useState("");
  const [results, setResults] = useState<Persona[] | null>(null);
  const [sel, setSel] = useState<Persona | null>(null);
  const [loadingShard, setLoadingShard] = useState(false);
  const [vista, setVista] = useState<"buscar" | "red">("buscar");
  // Índices sanción/DJ shardeados por letra (clave = mismo nombre normalizado que este
  // buscador). Cruce por nombre → homónimo posible, no hecho confirmado.
  const [sanciones, setSanciones] = useState<Record<string, Sancion[]>>({});
  const [dj, setDj] = useState<Record<string, Dj[]>>({});
  const cache = useRef<Record<string, Persona[]>>({});
  const sanCache = useRef<Record<string, Record<string, Sancion[]>>>({});
  const djCache = useRef<Record<string, Record<string, Dj[]>>>({});

  useEffect(() => {
    staticData.personasRed().then((d) => setRed((d as { items: Persona[] }).items)).catch(() => {});
  }, []);

  // Carga los shards de señales (sanción/DJ) para la letra de la búsqueda, en paralelo
  // al shard de personas. Todas las coincidencias comparten inicial (el buscador filtra
  // dentro del shard de esa letra), así que un solo shard por letra basta para la lista.
  useEffect(() => {
    const nq = q.trim().toUpperCase().normalize("NFKD").replace(/[̀-ͯ]/g, "");
    if (nq.length < 2) return;
    const letra = /[A-Z]/.test(nq[0]) ? nq[0] : "_";
    if (sanCache.current[letra]) { setSanciones(sanCache.current[letra]); }
    else staticData.sancionesShard(letra)
      .then((d) => { sanCache.current[letra] = (d as { index: Record<string, Sancion[]> }).index; setSanciones(sanCache.current[letra]); })
      .catch(() => { sanCache.current[letra] = {}; });
    if (djCache.current[letra]) { setDj(djCache.current[letra]); }
    else staticData.djShard(letra)
      .then((d) => { djCache.current[letra] = (d as { index: Record<string, Dj[]> }).index; setDj(djCache.current[letra]); })
      .catch(() => { djCache.current[letra] = {}; });
  }, [q]);

  const sancionSel = (sel && sanciones[sel[0]]) || null;
  const djSel = (sel && dj[sel[0]]) || null;

  useEffect(() => {
    const nq = q.trim().toUpperCase().normalize("NFKD").replace(/[̀-ͯ]/g, "");
    if (nq.length < 2) { setResults(null); return; }
    const letra = /[A-Z]/.test(nq[0]) ? nq[0] : "_";
    const run = (shard: Persona[]) => setResults(shard.filter((p) => p[0].includes(nq)).slice(0, 200));
    if (cache.current[letra]) { run(cache.current[letra]); return; }
    setLoadingShard(true);
    staticData.personasShard(letra)
      .then((d) => { cache.current[letra] = (d as { items: Persona[] }).items; run(cache.current[letra]); })
      .catch(() => setResults([]))
      .finally(() => setLoadingShard(false));
  }, [q]);

  const lista = results ?? red;
  const titulo = results ? `${fmt.format(lista.length)} resultados` : `${fmt.format(red.length)} personas en 2+ entidades (redes de poder)`;

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <div className="chip mb-3">Buscador global · grafo de poder</div>
      <h1 className="text-3xl font-bold tracking-tight text-ink">Personas</h1>
      <p className="mt-2 max-w-2xl text-ink-soft">
        Busca a cualquier persona y mira su <b>trayectoria</b> en el Estado (2026 + histórico 2015–2024).
        Aparecer en 2+ entidades casi siempre es <b>rotación</b> en el tiempo, no doble empleo.
      </p>

      <div className="mt-4 flex gap-2">
        <button onClick={() => setVista("buscar")} className={`rounded-full border px-4 py-1.5 text-sm font-medium transition ${vista === "buscar" ? "border-peru-red/50 bg-peru-red/15 text-peru-redsoft" : "border-surface/10 bg-surface/[0.03] text-ink-soft hover:text-ink"}`}>🔍 Buscar persona</button>
        <button onClick={() => setVista("red")} className={`rounded-full border px-4 py-1.5 text-sm font-medium transition ${vista === "red" ? "border-peru-red/50 bg-peru-red/15 text-peru-redsoft" : "border-surface/10 bg-surface/[0.03] text-ink-soft hover:text-ink"}`}>🕸️ Red institucional</button>
      </div>

      {vista === "red" ? (
        <div className="mt-5">
          <div className="mb-2 text-xs uppercase tracking-wide text-ink-mute">Entidades conectadas por personal compartido (80 más conectadas)</div>
          <RedInstitucional />
        </div>
      ) : (
      <>
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Buscar por APELLIDO… (ej. Llanos, Sánchez Ferrer, Talledo)"
        className="input mt-4"
      />
      {loadingShard && <p className="mt-2 text-xs text-ink-mute">Cargando índice…</p>}

      <div className="mt-5 grid gap-5 lg:grid-cols-[1fr,1.1fr]">
        <div>
          <div className="mb-2 text-xs uppercase tracking-wide text-ink-mute">{titulo}</div>
          {lista.length === 0 ? (
            <Empty>{results ? "Sin resultados (prueba por apellido)." : "Cargando…"}</Empty>
          ) : (
            <div className="glass max-h-[520px] divide-y divide-surface/[0.05] overflow-y-auto">
              {lista.slice(0, 200).map((p, i) => (
                <button
                  key={i}
                  onClick={() => setSel(p)}
                  className={`flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left transition-colors hover:bg-surface/[0.04] ${sel === p ? "bg-surface/[0.05]" : ""}`}
                >
                  <span className="min-w-0 truncate text-sm text-ink">{p[0]}</span>
                  <span className="flex shrink-0 items-center gap-1">
                    {sanciones[p[0]] && <span className="rounded-md bg-accent-amber/20 px-1.5 py-0.5 text-[11px] text-accent-amber" title="Coincidencia por nombre en el RNSSC (homónimo posible)">⚠️ sanción</span>}
                    {dj[p[0]] && <span className="rounded-md bg-accent-green/15 px-1.5 py-0.5 text-[11px] text-accent-green" title="Declaró DJ de Intereses (CGR 2022, homónimo posible)">📋 DJ</span>}
                    {p[1] >= 2 && <span className="rounded-md bg-peru-red/15 px-2 py-0.5 text-[11px] text-peru-redsoft">{p[1]} entidades</span>}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        <div>
          {sel ? (
            <div className="glass p-4">
              <div className="mb-2 font-semibold text-ink">{sel[0]}</div>
              {sancionSel && (
                <div className="mb-3 rounded-lg border border-accent-amber/30 bg-accent-amber/[0.07] p-3">
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-accent-amber">⚠️ Posible sanción (RNSSC)</div>
                  <div className="mt-1.5 space-y-1">
                    {sancionSel.map((s, i) => (
                      <div key={i} className="text-[12px] text-ink-soft">
                        <span className="font-medium text-ink">{s.tipo.length > 60 ? s.tipo.slice(0, 60) + "…" : s.tipo}</span>
                        <span className="text-ink-mute"> · {s.entidad}</span>
                        {s.fecha_fin && <span className="text-ink-faint"> · hasta {s.fecha_fin}</span>}
                        <span className="text-ink-faint"> · DNI {s.dni_masked}</span>
                      </div>
                    ))}
                  </div>
                  <div className="mt-1.5 text-[10px] text-ink-faint">
                    Coincidencia por <b>nombre</b> con el <a className="underline" href="/sanciones">RNSSC</a> — homónimo posible, verifica identidad en la fuente oficial.
                  </div>
                </div>
              )}
              {djSel && (
                <div className="mb-3 rounded-lg border border-accent-green/25 bg-accent-green/[0.06] p-3">
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-accent-green">📋 Declaró DJ de Intereses (CGR)</div>
                  <div className="mt-1.5 space-y-1">
                    {djSel.map((s, i) => (
                      <div key={i} className="text-[12px] text-ink-soft">
                        <span className="font-medium text-ink">{s.cargo || "—"}</span>
                        <span className="text-ink-mute"> · {s.entidad}</span>
                        {s.fecha && <span className="text-ink-faint"> · {s.fecha}</span>}
                      </div>
                    ))}
                  </div>
                  <div className="mt-1.5 text-[10px] text-ink-faint">
                    Declarar es una <b>obligación cumplida</b> (señal positiva). Dataset abierto CGR jul–dic 2022 · coincidencia por nombre.
                  </div>
                </div>
              )}
              <PersonaGrafo nombre={sel[0]} apariciones={sel[2]} />
              <div className="mb-1 mt-3 text-[11px] font-semibold uppercase tracking-wide text-accent-cyan/80">Trayectoria (línea de tiempo)</div>
              <div className="space-y-1.5">
                {[...sel[2]].sort((x, y) => (y[5] || "").localeCompare(x[5] || "")).map((a, i) => (
                  <div key={i} className="flex items-center justify-between gap-2 text-sm">
                    <span className="flex min-w-0 items-center gap-2">
                      <span className="shrink-0 rounded bg-surface/10 px-1.5 py-0.5 text-[10px] tabular text-ink-mute">{a[5] || "—"}</span>
                      <span className="min-w-0 truncate text-ink-soft"><span className="text-accent-blue">{a[1]}</span> · {a[2]}</span>
                    </span>
                    <span className="shrink-0 text-ink-mute">{a[3]} · {money(a[4])}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="glass flex h-full min-h-[300px] items-center justify-center p-6 text-center text-sm text-ink-mute">
              Selecciona una persona para ver su <b className="mx-1 text-ink-soft">grafo de poder</b> (en qué entidades aparece).
            </div>
          )}
        </div>
      </div>
      </>
      )}
    </div>
  );
}
