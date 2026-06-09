import { useEffect, useMemo, useState } from "react";

interface MapData { viewBox: string; paths: Record<string, string> }

function na(s: string) {
  return s.normalize("NFKD").replace(/[̀-ͯ]/g, "").toUpperCase().trim();
}

export function PeruMap({
  values, label, format,
}: {
  values: Record<string, number>; // region (normalizado) → valor
  label: string;
  format: (n: number) => string;
}) {
  const [map, setMap] = useState<MapData | null>(null);
  const [hover, setHover] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/peru_map.json`)
      .then((r) => r.json())
      .then(setMap)
      .catch(() => {});
  }, []);

  const norm = useMemo(() => {
    const m: Record<string, number> = {};
    for (const [k, v] of Object.entries(values)) m[na(k)] = v;
    return m;
  }, [values]);
  const max = useMemo(() => Math.max(1, ...Object.values(norm)), [norm]);

  if (!map) return <div className="skeleton h-[420px] w-full rounded-xl" />;

  const color = (dep: string) => {
    const v = norm[dep] ?? 0;
    if (!v) return "rgb(var(--surface) / 0.05)";
    const t = Math.sqrt(v / max); // escala suave
    // azul → cian → rojo según intensidad
    const r = Math.round(30 + t * 195);
    const g = Math.round(60 + t * 80);
    const b = Math.round(120 - t * 40);
    return `rgb(${r} ${g} ${b})`;
  };

  return (
    <div className="relative">
      <svg viewBox={map.viewBox} className="mx-auto h-[460px] w-auto max-w-full">
        {Object.entries(map.paths).map(([dep, d]) => (
          <path
            key={dep}
            d={d}
            fill={color(dep)}
            stroke="rgb(var(--bg-base))"
            strokeWidth={1}
            className="cursor-pointer transition-opacity hover:opacity-80"
            onMouseEnter={() => setHover(dep)}
            onMouseLeave={() => setHover(null)}
          />
        ))}
      </svg>
      {hover && (
        <div className="pointer-events-none absolute left-1/2 top-2 -translate-x-1/2 rounded-lg border border-surface/10 bg-bg-deep px-3 py-1.5 text-sm shadow-glow">
          <span className="font-medium text-ink">{hover.charAt(0) + hover.slice(1).toLowerCase()}</span>
          <span className="ml-2 tabular text-accent-cyan">{format(norm[hover] ?? 0)}</span>
          <span className="ml-1 text-[11px] text-ink-mute">{label}</span>
        </div>
      )}
      <p className="mt-2 text-center text-[11px] text-ink-faint">
        Pasa el cursor por cada región. Color = intensidad del valor. "Nacional (Lima)" no se mapea (sede en Lima / región no determinada por nombre).
      </p>
    </div>
  );
}
