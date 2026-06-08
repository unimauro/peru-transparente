import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { staticData } from "@/lib/api";
import type { NationalKpis } from "@/types";

const fmt = new Intl.NumberFormat("es-PE");
const money = new Intl.NumberFormat("es-PE", { style: "currency", currency: "PEN", maximumFractionDigits: 0 });

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-gray-800 bg-peru-panel p-4">
      <div className="tabular text-2xl font-semibold text-white">{value}</div>
      <div className="text-xs uppercase tracking-wide text-gray-400">{label}</div>
    </div>
  );
}

export function Home() {
  const [kpis, setKpis] = useState<NationalKpis | null>(null);
  useEffect(() => {
    staticData.nationalKpis().then(setKpis as (k: unknown) => void).catch(() => setKpis(null));
  }, []);

  return (
    <div className="mx-auto max-w-5xl px-4 py-12">
      <h1 className="text-3xl font-bold text-white">
        Perú Transparente <span className="text-peru-red">·</span>
      </h1>
      <p className="mt-2 max-w-2xl text-gray-300">
        Mapa nacional de funcionarios, entidades públicas, empresas estatales y redes de poder.
        Datos públicos, trazables a su fuente y exportables.
      </p>

      <div className="mt-8 flex gap-2">
        <input
          className="w-full rounded-md border border-gray-700 bg-peru-panel px-4 py-3 text-gray-100 placeholder-gray-500"
          placeholder='Busca un funcionario, entidad, empresa o contrato…'
        />
        <button className="rounded-md bg-peru-red px-5 font-medium text-white">Buscar</button>
      </div>

      {kpis && (
        <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          <Kpi label="Entidades" value={fmt.format(kpis.total_entities)} />
          <Kpi label="Funcionarios" value={fmt.format(kpis.total_persons)} />
          <Kpi label="Empresas FONAFE" value={fmt.format(kpis.total_companies)} />
          <Kpi label="Contratos" value={fmt.format(kpis.total_contracts)} />
          <Kpi label="Monto contratado" value={money.format(kpis.total_contract_amount)} />
        </div>
      )}

      <nav className="mt-10 flex flex-wrap gap-3 text-sm">
        <Link to="/entidades" className="rounded border border-gray-700 px-4 py-2 hover:bg-peru-panel">Entidades</Link>
        <Link to="/grafo" className="rounded border border-gray-700 px-4 py-2 hover:bg-peru-panel">Grafo de Poder</Link>
        <Link to="/dashboards" className="rounded border border-gray-700 px-4 py-2 hover:bg-peru-panel">Dashboards</Link>
        <Link to="/metodologia" className="rounded border border-gray-700 px-4 py-2 hover:bg-peru-panel">Metodología y fuentes</Link>
      </nav>
    </div>
  );
}
