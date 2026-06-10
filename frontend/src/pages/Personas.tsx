import { useEffect, useRef, useState } from "react";
import { staticData } from "@/lib/api";
import { fmt, money, Empty } from "@/components/ui";
import { PersonaGrafo } from "@/components/PersonaGrafo";
import { RedInstitucional } from "@/components/RedInstitucional";

type Ap = [string, string, string, string, number]; // id_entidad, abrev, cargo, regimen, sueldo
type Persona = [string, number, Ap[]];               // nombre, n_entidades, apariciones

export function Personas() {
  const [red, setRed] = useState<Persona[]>([]);
  const [q, setQ] = useState("");
  const [results, setResults] = useState<Persona[] | null>(null);
  const [sel, setSel] = useState<Persona | null>(null);
  const [loadingShard, setLoadingShard] = useState(false);
  const [vista, setVista] = useState<"buscar" | "red">("buscar");
  const cache = useRef<Record<string, Persona[]>>({});

  useEffect(() => {
    staticData.personasRed().then((d) => setRed((d as { items: Persona[] }).items)).catch(() => {});
  }, []);

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
        Busca a cualquier persona en todo el Estado y mira <b>en cuántas entidades aparece</b> (por nombre).
        Aparecer en 2+ no implica doble empleo: casi siempre es <b>rotación</b> (cambió de trabajo) u <b>homónimos</b>.
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
                  {p[1] >= 2 && <span className="shrink-0 rounded-md bg-peru-red/15 px-2 py-0.5 text-[11px] text-peru-redsoft">{p[1]} entidades</span>}
                </button>
              ))}
            </div>
          )}
        </div>

        <div>
          {sel ? (
            <div className="glass p-4">
              <div className="mb-2 font-semibold text-ink">{sel[0]}</div>
              <PersonaGrafo nombre={sel[0]} apariciones={sel[2]} />
              <div className="mt-3 space-y-1.5">
                {sel[2].map((a, i) => (
                  <div key={i} className="flex items-center justify-between gap-2 text-sm">
                    <span className="min-w-0 truncate text-ink-soft"><span className="text-accent-blue">{a[1]}</span> · {a[2]}</span>
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
