import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { staticData } from "@/lib/api";
import type { NationalKpis, Meta } from "@/types";

const fmt = new Intl.NumberFormat("es-PE");

function Kpi({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-gray-800 bg-peru-panel p-4">
      <div className="tabular text-3xl font-semibold text-white">{value}</div>
      <div className="text-xs uppercase tracking-wide text-gray-400">{label}</div>
      {hint && <div className="mt-1 text-[11px] text-gray-500">{hint}</div>}
    </div>
  );
}

export function Home() {
  const [k, setK] = useState<NationalKpis | null>(null);
  const [m, setM] = useState<Meta | null>(null);
  useEffect(() => {
    staticData.nationalKpis().then((d) => setK(d as NationalKpis)).catch(() => {});
    staticData.meta().then((d) => setM(d as Meta)).catch(() => {});
  }, []);

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="text-3xl font-bold text-white">
        Perú Transparente <span className="text-peru-red">·</span>
      </h1>
      <p className="mt-2 max-w-2xl text-gray-300">
        Mapa nacional de funcionarios, entidades públicas, empresas estatales y redes de poder.
        Datos públicos del Estado peruano, trazables a su fuente.
      </p>

      {k && (
        <>
          <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Kpi label="Entidades del Estado" value={fmt.format(k.total_entities)} hint="catálogo PTE completo" />
            <Kpi label="Funcionarios descargados" value={fmt.format(k.total_funcionarios)} hint={`${k.entities_with_data} entidades con datos`} />
            <Kpi label="Cargos clave" value={fmt.format(k.total_cargos_clave)} hint="dirección + jefaturas" />
            <Kpi label="Cobertura" value={`${m ? m.cobertura_pct : 0}%`} hint="entidades con personal" />
          </div>

          <div className="mt-8 grid gap-6 md:grid-cols-2">
            <div className="rounded-lg border border-gray-800 bg-peru-panel p-4">
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-300">Entidades por tipo</h2>
              {k.por_tipo.map(([t, n]) => (
                <Bar key={t} label={t} value={n} max={k.por_tipo[0][1]} />
              ))}
            </div>
            <div className="rounded-lg border border-gray-800 bg-peru-panel p-4">
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-300">Cargos clave hallados</h2>
              {k.por_nivel.length ? (
                k.por_nivel.map(([t, n]) => (
                  <Bar key={t} label={t} value={n} max={Math.max(...k.por_nivel.map((x) => x[1]))} color="bg-peru-red" />
                ))
              ) : (
                <p className="text-sm text-gray-500">Descargando…</p>
              )}
            </div>
          </div>
        </>
      )}

      <nav className="mt-10 flex flex-wrap gap-3 text-sm">
        <Link to="/entidades" className="rounded bg-peru-red px-4 py-2 font-medium text-white">Ver entidades →</Link>
        <Link to="/funcionarios" className="rounded border border-gray-700 px-4 py-2 hover:bg-peru-panel">Funcionarios y cargos</Link>
        <a href="https://github.com/unimauro/peru-transparente/blob/main/data/funcionarios.csv" className="rounded border border-gray-700 px-4 py-2 hover:bg-peru-panel" target="_blank" rel="noreferrer">Descargar CSV</a>
      </nav>

      {m && (
        <p className="mt-6 text-xs text-gray-500">
          Última actualización: {new Date(m.actualizado).toLocaleString("es-PE")} ·
          Fuente: Portal de Transparencia Estándar · El barrido continúa: las cifras crecen en cada corrida.
        </p>
      )}
    </div>
  );
}

function Bar({ label, value, max, color = "bg-blue-600" }: { label: string; value: number; max: number; color?: string }) {
  return (
    <div className="mb-2">
      <div className="flex justify-between text-xs text-gray-300">
        <span className="truncate pr-2">{label}</span>
        <span className="tabular text-gray-400">{new Intl.NumberFormat("es-PE").format(value)}</span>
      </div>
      <div className="mt-1 h-2 rounded bg-gray-800">
        <div className={`h-2 rounded ${color}`} style={{ width: `${Math.max(3, (value / max) * 100)}%` }} />
      </div>
    </div>
  );
}
