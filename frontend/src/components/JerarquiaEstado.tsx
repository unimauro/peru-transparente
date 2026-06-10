import { useEffect, useState } from "react";
import { staticData } from "@/lib/api";
import { fmt, money } from "@/components/ui";

interface Pliego { pliego: string; n: number; masa: number }
interface Sector { sector: string; n: number; masa: number; pliegos: Pliego[] }

export function JerarquiaEstado() {
  const [items, setItems] = useState<Sector[]>([]);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    staticData.jerarquia().then((d) => setItems((d as { items: Sector[] }).items)).catch(() => {});
  }, []);

  if (!items.length) return null;
  const max = items[0].n;

  return (
    <div className="glass mt-5 p-5">
      <div className="mb-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-accent-cyan/80">Estructura del Estado · AIRHSP</div>
      <h2 className="text-lg font-semibold text-ink">Sector → Pliego (jerarquía real)</h2>
      <p className="mb-3 mt-1 text-[11px] text-ink-faint">
        La relación <b>funcional/jerárquica</b> oficial: cada pliego (entidad) pertenece a un sector. Clic para expandir.
        Incluye docentes y FF.AA. (agregado, sin nombres).
      </p>
      <div className="space-y-1.5">
        {items.map((s) => {
          const isOpen = open === s.sector;
          return (
            <div key={s.sector} className="overflow-hidden rounded-lg border border-surface/[0.06]">
              <button onClick={() => setOpen(isOpen ? null : s.sector)} className="w-full px-3 py-2 text-left transition-colors hover:bg-surface/[0.04]">
                <div className="flex items-center justify-between gap-3">
                  <span className="flex min-w-0 items-center gap-2">
                    <span className={`text-ink-mute transition-transform ${isOpen ? "rotate-90" : ""}`}>▸</span>
                    <span className="truncate text-sm font-medium text-ink">{s.sector}</span>
                  </span>
                  <span className="shrink-0 text-xs text-ink-mute"><span className="tabular font-semibold text-ink">{fmt.format(s.n)}</span> · {money(s.masa)}/mes</span>
                </div>
                <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-surface/[0.06]">
                  <div className="h-full rounded-full bg-gradient-to-r from-accent-cyan to-accent-blue" style={{ width: `${Math.max(2, (s.n / max) * 100)}%` }} />
                </div>
              </button>
              {isOpen && (
                <div className="border-t border-surface/[0.06] px-3 py-2">
                  {s.pliegos.map((p) => (
                    <div key={p.pliego} className="flex items-center justify-between gap-2 py-0.5 text-xs">
                      <span className="min-w-0 truncate text-ink-soft">{p.pliego}</span>
                      <span className="shrink-0 text-ink-mute"><span className="tabular">{fmt.format(p.n)}</span> · {money(p.masa)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
