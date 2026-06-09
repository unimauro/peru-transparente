import { useEffect, useMemo, useState } from "react";
import { staticData } from "@/lib/api";
import type { FuncionarioItem } from "@/types";

const fmt = new Intl.NumberFormat("es-PE");
const MESES = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Set", "Oct", "Nov", "Dic"];

export function Funcionarios() {
  const [items, setItems] = useState<FuncionarioItem[]>([]);
  const [q, setQ] = useState("");
  const [soloClave, setSoloClave] = useState(false);

  useEffect(() => {
    staticData.funcionariosSample().then((d) => setItems((d as { items: FuncionarioItem[] }).items)).catch(() => {});
  }, []);

  const filtered = useMemo(() => {
    const nq = q.trim().toLowerCase();
    return items
      .filter((f) => (!soloClave || f.nivel !== "Profesional/Apoyo"))
      .filter((f) => !nq || `${f.nombre} ${f.cargo} ${f.entidad} ${f.dependencia}`.toLowerCase().includes(nq))
      .slice(0, 400);
  }, [items, q, soloClave]);

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <h1 className="text-2xl font-semibold text-white">Funcionarios y cargos</h1>
      <p className="mt-1 text-sm text-gray-400">
        Personas mapeadas a su período, cargo, dependencia, remuneración y URL fuente. Muestra de {fmt.format(items.length)} registros descargados.
      </p>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Buscar nombre, cargo, entidad o dependencia…"
          className="flex-1 rounded-md border border-gray-700 bg-peru-panel px-3 py-2 text-gray-100 placeholder-gray-500"
        />
        <label className="flex items-center gap-2 text-sm text-gray-300">
          <input type="checkbox" checked={soloClave} onChange={(e) => setSoloClave(e.target.checked)} />
          Solo cargos clave
        </label>
      </div>

      <div className="mt-4 overflow-x-auto rounded-lg border border-gray-800">
        <table className="w-full text-sm">
          <thead className="bg-peru-panel text-left text-gray-400">
            <tr>
              <th className="px-3 py-2">Nombre</th>
              <th className="px-3 py-2">Cargo</th>
              <th className="px-3 py-2">Entidad / Dependencia</th>
              <th className="px-3 py-2">Período</th>
              <th className="px-3 py-2 text-right">Ingreso S/</th>
              <th className="px-3 py-2">Fuente</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((f, i) => (
              <tr key={i} className="border-t border-gray-800 hover:bg-peru-panel/50">
                <td className="px-3 py-2 text-gray-100">{f.nombre}</td>
                <td className="px-3 py-2">
                  <span className={f.nivel !== "Profesional/Apoyo" ? "text-peru-red" : "text-gray-300"}>{f.cargo}</span>
                  <div className="text-[11px] text-gray-500">{f.regimen}</div>
                </td>
                <td className="px-3 py-2 text-gray-400">
                  <div className="text-gray-300">{f.entidad}</div>
                  <div className="text-[11px]">{f.dependencia}</div>
                </td>
                <td className="px-3 py-2 text-gray-400">{MESES[+f.mes] || f.mes} {f.anio}</td>
                <td className="tabular px-3 py-2 text-right text-gray-200">{f.total}</td>
                <td className="px-3 py-2">
                  <a href={f.url} target="_blank" rel="noreferrer" className="text-blue-400 underline">PTE↗</a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-xs text-gray-500">Mostrando {filtered.length} filas. Datos públicos del PTE · trazables a la fuente.</p>
    </div>
  );
}
