import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { staticData } from "@/lib/api";
import { fmt, Empty, usePaged, Pagination } from "@/components/ui";

interface Aut {
  nombre: string; cargo: string; email: string; telefono: string;
  url: string; institucion: string; id_entidad: string;
}

export function Autoridades() {
  const [items, setItems] = useState<Aut[]>([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    staticData.autoridades()
      .then((d) => setItems((d as { items: Aut[] }).items))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const nq = q.trim().toLowerCase();
    return items.filter((a) => !nq || `${a.nombre} ${a.cargo} ${a.institucion}`.toLowerCase().includes(nq));
  }, [items, q]);

  const { slice, page, pages, setPage, total } = usePaged(filtered, 50, q);

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <div className="chip mb-3">Directorio · gob.pe</div>
      <h1 className="text-3xl font-bold tracking-tight text-ink">Autoridades del Estado</h1>
      <p className="mt-2 max-w-2xl text-ink-soft">
        Rectores, ministros, viceministros, superintendentes, jefes y gerentes — con cargo, correo y
        teléfono oficial. Complementa la planilla del PTE con lo que muchas entidades no publican ahí.
      </p>
      <div className="mt-3 chip">{fmt.format(items.length)} autoridades · 385 entidades</div>

      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Buscar nombre, cargo o institución… (ej. rector, ministra, San Marcos)"
        className="input mt-4"
      />

      {loading ? (
        <div className="mt-5 space-y-2">{[...Array(8)].map((_, i) => <div key={i} className="skeleton h-16" />)}</div>
      ) : filtered.length === 0 ? (
        <Empty>Sin resultados.</Empty>
      ) : (
        <div className="mt-5 grid gap-2 sm:grid-cols-2">
          {slice.map((a, i) => (
            <div key={i} className="glass p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="truncate font-medium text-ink">{a.nombre}</div>
                  <div className="truncate text-xs text-accent-cyan">{a.cargo}</div>
                </div>
                <a href={a.url} target="_blank" rel="noreferrer" className="shrink-0 text-accent-blue">↗</a>
              </div>
              <Link to={`/entidad/${a.id_entidad}`} className="mt-1 block truncate text-[11px] text-ink-mute hover:text-ink">
                {a.institucion}
              </Link>
              {a.email && <div className="mt-1 truncate text-[11px] text-ink-faint">{a.email}{a.telefono ? ` · ${a.telefono}` : ""}</div>}
            </div>
          ))}
        </div>
      )}
      {!loading && filtered.length > 0 && <Pagination page={page} pages={pages} setPage={setPage} total={total} />}
    </div>
  );
}
