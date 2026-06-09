import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { staticData } from "@/lib/api";
import type { EntidadCat } from "@/types";
import { fmt, Empty } from "@/components/ui";

// Filtros rápidos por palabra clave (categorías que el usuario suele buscar).
const QUICK: { label: string; rx: RegExp | null }[] = [
  { label: "Todos", rx: null },
  { label: "UNI", rx: /universidad nacional de ingenier|\(uni\)/i },
  { label: "Universidades", rx: /universidad/i },
  { label: "Educación", rx: /colegio|instituto|escuela|educativ|pedag|ugel|magisterio|eespp|cetpro|educaci/i },
  { label: "Salud", rx: /hospital|salud|essalud|diresa|geresa|minsa|sanidad|materno|seguro social/i },
  { label: "Fiscalías/Justicia", rx: /fiscal|ministerio p[uú]blico|corte|judicial|magistratura|justicia|inpe|tribunal/i },
  { label: "Ministerios", rx: /ministerio|presidencia del consejo/i },
  { label: "Reguladores", rx: /osinergmin|osiptel|ositran|sunass|sutran|sunedu|superintendencia|indecopi|regulador/i },
  { label: "Empresas públicas", rx: /S\.?A\.?|empresa|petro|electro|sedapal|essalud|banco|fonafe/i },
  { label: "Fuerzas Armadas", rx: /ej[eé]rcito|marina|fuerza a[eé]rea|fap|defensa|comando conjunto|militar|polic/i },
  { label: "Municipalidades", rx: /municipalidad|gobierno regional|regional/i },
];

export function Entidades() {
  const [items, setItems] = useState<EntidadCat[]>([]);
  const [q, setQ] = useState("");
  const [quick, setQuick] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    staticData.entidades()
      .then((d) => setItems((d as { items: EntidadCat[] }).items))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const nq = q.trim().toLowerCase();
    const rx = QUICK[quick].rx;
    return items
      .filter((e) => (!rx || rx.test(e.nombre)) && (!nq || e.nombre.toLowerCase().includes(nq)))
      .slice(0, 600);
  }, [items, q, quick]);

  const conDatos = items.filter((e) => e.funcionarios).length;

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <div className="chip mb-3">Catálogo · {fmt.format(items.length)} entidades</div>
      <h1 className="text-3xl font-bold tracking-tight text-ink">Entidades del Estado</h1>
      <p className="mt-2 max-w-2xl text-ink-soft">
        Todo el universo del Portal de Transparencia: ministerios, organismos reguladores, fuerzas
        armadas, empresas públicas y gobiernos regionales/locales. {fmt.format(conDatos)} ya con personal descargado.
      </p>

      <div className="mt-6 flex flex-wrap gap-2">
        {QUICK.map((qk, i) => (
          <button
            key={qk.label}
            onClick={() => setQuick(i)}
            className={`rounded-full border px-3 py-1.5 text-xs font-medium transition ${
              quick === i ? "border-peru-red/50 bg-peru-red/15 text-peru-redsoft" : "border-surface/10 bg-surface/[0.03] text-ink-soft hover:border-surface/20 hover:text-ink"
            }`}
          >
            {qk.label}
          </button>
        ))}
      </div>

      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Buscar entidad… (ej. Ejército, Petroperú, OSIPTEL, Municipalidad de Lima)"
        className="input mt-4"
      />

      {loading ? (
        <div className="mt-5 space-y-2">{[...Array(8)].map((_, i) => <div key={i} className="skeleton h-12" />)}</div>
      ) : filtered.length === 0 ? (
        <Empty>Sin resultados para tu búsqueda.</Empty>
      ) : (
        <div className="glass mt-5 divide-y divide-surface/[0.05] overflow-hidden">
          {filtered.map((e) => {
            const inner = (
              <>
                <div className="min-w-0">
                  <div className="truncate font-medium text-ink">{e.nombre}</div>
                  <div className="text-xs text-ink-mute">{e.tipo}</div>
                </div>
                <div className="shrink-0 text-right">
                  {e.funcionarios ? (
                    <>
                      <div className="tabular font-semibold text-accent-cyan">{fmt.format(e.funcionarios)}</div>
                      <div className="text-[10px] uppercase tracking-wide text-ink-faint">funcionarios →</div>
                    </>
                  ) : (
                    <span className="text-xs text-ink-faint">aún no barrida</span>
                  )}
                </div>
              </>
            );
            return e.funcionarios ? (
              <Link key={e.id} to={`/entidad/${e.id}`} className="flex items-center justify-between gap-4 px-4 py-3 transition-colors hover:bg-surface/[0.04]">
                {inner}
              </Link>
            ) : (
              <div key={e.id} className="flex items-center justify-between gap-4 px-4 py-3 opacity-70">{inner}</div>
            );
          })}
        </div>
      )}
      <p className="mt-3 text-xs text-ink-faint">Mostrando {filtered.length} de {fmt.format(items.length)}.</p>
    </div>
  );
}
