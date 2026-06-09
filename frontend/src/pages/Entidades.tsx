import { useEffect, useMemo, useState } from "react";
import { staticData } from "@/lib/api";
import type { EntidadCat } from "@/types";

const fmt = new Intl.NumberFormat("es-PE");

export function Entidades() {
  const [items, setItems] = useState<EntidadCat[]>([]);
  const [q, setQ] = useState("");
  const [tipo, setTipo] = useState("");

  useEffect(() => {
    staticData.entidades().then((d) => setItems((d as { items: EntidadCat[] }).items)).catch(() => {});
  }, []);

  const tipos = useMemo(() => [...new Set(items.map((e) => e.tipo))].sort(), [items]);
  const filtered = useMemo(() => {
    const nq = q.trim().toLowerCase();
    return items
      .filter((e) => (!tipo || e.tipo === tipo) && (!nq || e.nombre.toLowerCase().includes(nq)))
      .slice(0, 500);
  }, [items, q, tipo]);

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="text-2xl font-semibold text-white">Entidades del Estado</h1>
      <p className="mt-1 text-sm text-gray-400">
        Catálogo completo del Portal de Transparencia ({fmt.format(items.length)} entidades, incluye militares y empresas públicas).
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Buscar entidad… (ej. Ejército, Petroperú, Municipalidad)"
          className="flex-1 rounded-md border border-gray-700 bg-peru-panel px-3 py-2 text-gray-100 placeholder-gray-500"
        />
        <select value={tipo} onChange={(e) => setTipo(e.target.value)}
          className="rounded-md border border-gray-700 bg-peru-panel px-3 py-2 text-gray-200">
          <option value="">Todos los tipos</option>
          {tipos.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>

      <div className="mt-4 overflow-hidden rounded-lg border border-gray-800">
        <table className="w-full text-sm">
          <thead className="bg-peru-panel text-left text-gray-400">
            <tr>
              <th className="px-3 py-2">Entidad</th>
              <th className="px-3 py-2">Tipo</th>
              <th className="px-3 py-2 text-right">Funcionarios</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((e) => (
              <tr key={e.id} className="border-t border-gray-800 hover:bg-peru-panel/50">
                <td className="px-3 py-2 text-gray-100">{e.nombre}</td>
                <td className="px-3 py-2 text-gray-400">{e.tipo}</td>
                <td className="tabular px-3 py-2 text-right">
                  {e.funcionarios ? (
                    <span className="text-conf-high">{fmt.format(e.funcionarios)}</span>
                  ) : (
                    <span className="text-gray-600">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-xs text-gray-500">
        Mostrando {filtered.length} de {fmt.format(items.length)}. "—" = aún no barrida (el scraping avanza por corridas).
      </p>
    </div>
  );
}
