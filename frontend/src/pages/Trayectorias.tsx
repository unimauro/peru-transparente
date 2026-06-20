import { useEffect, useMemo, useState } from "react";
import { staticData } from "@/lib/api";
import { fmt, Empty, usePaged, Pagination } from "@/components/ui";

interface Paso { anio: string; abrev: string; cargo: string; nivel: string }
interface Tray {
  nombre: string; n_inst: number; n_cargos: number; span: [string, string]; pico: string; trace: Paso[];
}
interface Data {
  summary: { total: number; alto: number; ge3: number; picos: Record<string, number> };
  nota: string; items: Tray[];
}

const ALTO = new Set(["Ministro", "Viceministro", "Secretario General", "Presidente Ejecutivo"]);

// Color del badge por nivel (cúpula en rojo, mando medio en cian/ámbar).
function nivelClass(n: string): string {
  if (n === "Ministro" || n === "Viceministro") return "bg-peru-red/15 text-peru-redsoft";
  if (n === "Secretario General" || n === "Presidente Ejecutivo" || n === "Gerente General") return "bg-accent-amber/15 text-accent-amber";
  return "bg-accent-cyan/10 text-accent-cyan";
}

export function Trayectorias() {
  const [d, setD] = useState<Data | null>(null);
  const [q, setQ] = useState("");
  const [soloAlto, setSoloAlto] = useState(false);

  useEffect(() => { staticData.trayectorias().then((x) => setD(x as Data)).catch(() => {}); }, []);

  const lista = useMemo(() => {
    const nq = q.trim().toLowerCase();
    // Solo-búsqueda: no se lista a nadie hasta que se escriba (≥2 caracteres).
    if (!d || nq.length < 2) return [];
    return d.items.filter((t) =>
      (!soloAlto || ALTO.has(t.pico)) &&
      (t.nombre.toLowerCase().includes(nq) || t.trace.some((p) => p.abrev.toLowerCase().includes(nq))),
    );
  }, [d, q, soloAlto]);

  const buscando = q.trim().length >= 2;

  const { slice, page, pages, setPage, total } = usePaged(lista, 20, `${q}|${soloAlto}`);

  if (!d) return <div className="mx-auto max-w-5xl px-4 py-10"><Empty>Cargando…</Empty></div>;

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <div className="chip mb-3">Trayectorias de poder · PTE 2015–2026</div>
      <h1 className="text-3xl font-bold tracking-tight text-ink">Quién pasó por dónde</h1>
      <p className="mt-2 max-w-2xl text-ink-soft">
        <b>Busca un nombre o una institución</b> para ver el recorrido de quienes ocuparon
        <b> cargos de mando</b> (gerente, director, jefe, hasta ministro) en <b>más de una institución</b>
        del Estado a lo largo del tiempo. No se publica un listado: la información se consulta por búsqueda.
      </p>

      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="glass p-4"><div className="tabular text-2xl font-bold text-ink">{fmt.format(d.summary.total)}</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">con mando en ≥2 instituciones</div></div>
        <div className="glass p-4"><div className="tabular text-2xl font-bold text-peru-redsoft">{fmt.format(d.summary.alto)}</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">llegaron a la cúpula</div></div>
        <div className="glass p-4"><div className="tabular text-2xl font-bold text-accent-amber">{fmt.format(d.summary.ge3)}</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">mando en 3+ instituciones</div></div>
        <div className="glass p-4"><div className="tabular text-2xl font-bold text-accent-cyan">{fmt.format((d.summary.picos["Ministro"] || 0) + (d.summary.picos["Viceministro"] || 0))}</div><div className="text-[11px] uppercase tracking-wider text-ink-mute">ministros / viceministros</div></div>
      </div>

      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          inputMode="search"
          autoComplete="off"
          placeholder="🔎 Buscar persona o institución (ej. MEF, MINSA)…"
          className="input w-full text-base sm:flex-1"
        />
        <button onClick={() => setSoloAlto((v) => !v)} className={`w-full rounded-xl border px-4 py-3 text-sm font-medium transition sm:w-auto sm:py-2.5 ${soloAlto ? "border-peru-red/50 bg-peru-red/15 text-peru-redsoft" : "border-surface/10 bg-surface/[0.02] text-ink-soft hover:text-ink"}`}>👑 Solo cúpula (ministro/viceministro)</button>
      </div>

      {!buscando ? (
        <Empty>🔎 Escribe un nombre o una institución (ej. <b>MEF</b>, <b>MINSA</b>) para consultar.</Empty>
      ) : lista.length === 0 ? (
        <Empty>Sin resultados para “{q.trim()}”.</Empty>
      ) : (
        <div className="mt-5 space-y-3">
          {slice.map((t) => (
            <div key={t.nombre + t.span[0]} className="glass p-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <div className="font-semibold text-ink">{t.nombre}</div>
                <div className="flex items-center gap-2 text-[11px] text-ink-mute">
                  <span className={`rounded-full px-2 py-0.5 font-medium ${nivelClass(t.pico)}`}>pico: {t.pico}</span>
                  <span className="tabular">{t.n_inst} instituciones</span>
                  <span className="tabular">{t.span[0]}–{t.span[1]}</span>
                </div>
              </div>
              {/* línea de tiempo del recorrido */}
              <ol className="mt-3 space-y-1.5 border-l border-surface/10 pl-4">
                {t.trace.map((p, i) => (
                  <li key={i} className="relative text-sm">
                    <span className="absolute -left-[1.07rem] top-1.5 h-2 w-2 rounded-full bg-accent-cyan" />
                    <span className="tabular font-semibold text-ink">{p.anio}</span>{" "}
                    <span className="font-medium text-ink-soft">{p.abrev}</span>{" "}
                    <span className={`ml-1 rounded px-1.5 py-0.5 text-[10px] ${nivelClass(p.nivel)}`}>{p.nivel}</span>
                    <span className="ml-1 text-[12px] text-ink-mute">{p.cargo}</span>
                  </li>
                ))}
              </ol>
            </div>
          ))}
        </div>
      )}
      {lista.length > 0 && <Pagination page={page} pages={pages} setPage={setPage} total={total} />}

      <p className="mt-4 text-[11px] text-ink-faint">
        {d.nota} La coincidencia es por <b>nombre completo</b>; casos de homonimia son posibles. Cobertura: fotos PTE de 2015, 2018, 2021, 2024 y 2026 (hay años intermedios sin captura aún).
      </p>
    </div>
  );
}
