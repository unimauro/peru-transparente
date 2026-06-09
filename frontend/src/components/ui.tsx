import { useEffect, useState, type ReactNode } from "react";

export const fmt = new Intl.NumberFormat("es-PE");

/** Paginación client-side para listas grandes (renderiza solo la página actual). */
export function usePaged<T>(items: T[], pageSize: number, resetKey: unknown) {
  const [page, setPage] = useState(0);
  useEffect(() => setPage(0), [resetKey]);
  const pages = Math.max(1, Math.ceil(items.length / pageSize));
  const p = Math.min(page, pages - 1);
  return {
    slice: items.slice(p * pageSize, p * pageSize + pageSize),
    page: p, pages, setPage, total: items.length,
  };
}

export function Pagination({ page, pages, setPage, total }: { page: number; pages: number; setPage: (n: number) => void; total: number }) {
  if (pages <= 1) return <p className="mt-3 text-xs text-ink-faint">{fmt.format(total)} resultados</p>;
  return (
    <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm">
      <span className="text-ink-mute">Página <b className="text-ink">{page + 1}</b> de {pages} · {fmt.format(total)} resultados</span>
      <div className="flex items-center gap-2">
        <button disabled={page === 0} onClick={() => setPage(page - 1)} className="btn-ghost disabled:cursor-not-allowed disabled:opacity-40">← Anterior</button>
        <button disabled={page >= pages - 1} onClick={() => setPage(page + 1)} className="btn-ghost disabled:cursor-not-allowed disabled:opacity-40">Siguiente →</button>
      </div>
    </div>
  );
}
export const money = (n: number | string) => {
  const v = typeof n === "string" ? parseFloat(n) : n;
  return isNaN(v) ? "—" : new Intl.NumberFormat("es-PE", { style: "currency", currency: "PEN", maximumFractionDigits: 0 }).format(v);
};

export function Stat({ value, label, hint, accent }: { value: ReactNode; label: string; hint?: string; accent?: string }) {
  return (
    <div className="glass glass-hover animate-fade-up p-5">
      <div className={`tabular text-3xl font-bold tracking-tight ${accent ?? "text-ink"}`}>{value}</div>
      <div className="mt-1 text-[11px] font-medium uppercase tracking-wider text-ink-mute">{label}</div>
      {hint && <div className="mt-1.5 text-xs text-ink-faint">{hint}</div>}
    </div>
  );
}

export function Bar({ label, value, max, color = "from-accent-blue to-accent-cyan" }: { label: string; value: number; max: number; color?: string }) {
  const pct = Math.max(3, Math.round((value / Math.max(max, 1)) * 100));
  return (
    <div className="mb-3 last:mb-0">
      <div className="flex items-baseline justify-between text-sm">
        <span className="truncate pr-2 text-ink-soft">{label}</span>
        <span className="tabular text-ink-mute">{fmt.format(value)}</span>
      </div>
      <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-surface/[0.06]">
        <div className={`h-full rounded-full bg-gradient-to-r ${color} transition-all duration-700`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function LevelBadge({ nivel }: { nivel: string }) {
  const key = nivel.toLowerCase();
  const tone =
    /ministr|titular/.test(key) ? "border-peru-red/40 bg-peru-red/15 text-peru-redsoft"
    : /vice/.test(key) ? "border-accent-violet/40 bg-accent-violet/15 text-accent-violet"
    : /secretari|gerente general/.test(key) ? "border-accent-cyan/40 bg-accent-cyan/15 text-accent-cyan"
    : /director|gerente/.test(key) ? "border-accent-blue/40 bg-accent-blue/15 text-accent-blue"
    : /jefe/.test(key) ? "border-accent-amber/40 bg-accent-amber/15 text-accent-amber"
    : "border-surface/10 bg-surface/5 text-ink-mute";
  return <span className={`inline-block rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${tone}`}>{nivel}</span>;
}

export function SectionTitle({ children, kicker }: { children: ReactNode; kicker?: string }) {
  return (
    <div className="mb-4">
      {kicker && <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-peru-redsoft/80">{kicker}</div>}
      <h2 className="text-lg font-semibold text-ink">{children}</h2>
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="py-16 text-center text-sm text-ink-mute">{children}</div>;
}
