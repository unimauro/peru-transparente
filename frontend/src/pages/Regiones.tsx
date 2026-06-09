import { useEffect, useMemo, useState } from "react";
import { staticData } from "@/lib/api";
import { fmt, money, SectionTitle } from "@/components/ui";

interface Region {
  region: string;
  entidades: number;
  con_datos: number;
  personal: number;
  planilla_mensual: number;
}

type Metric = "personal" | "planilla_mensual" | "entidades";
const METRICS: { key: Metric; label: string }[] = [
  { key: "personal", label: "Personal" },
  { key: "planilla_mensual", label: "Planilla mensual (aprox.)" },
  { key: "entidades", label: "N° de entidades" },
];

export function Regiones() {
  const [items, setItems] = useState<Region[]>([]);
  const [metric, setMetric] = useState<Metric>("personal");

  useEffect(() => {
    staticData.regiones().then((d) => setItems((d as { items: Region[] }).items)).catch(() => {});
  }, []);

  const sorted = useMemo(() => [...items].sort((a, b) => b[metric] - a[metric]), [items, metric]);
  const max = sorted.length ? sorted[0][metric] : 1;
  const totalPlanilla = items.reduce((s, r) => s + r.planilla_mensual, 0);
  const totalPersonal = items.reduce((s, r) => s + r.personal, 0);

  const val = (r: Region) =>
    metric === "planilla_mensual" ? money(r[metric]) : fmt.format(r[metric]);

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <div className="chip mb-3">Distribución territorial</div>
      <h1 className="text-3xl font-bold tracking-tight text-ink">Personal y planilla por región</h1>
      <p className="mt-2 max-w-2xl text-ink-soft">
        Cómo se distribuye el personal público y su planilla mensual por región del Perú.
      </p>

      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
        <div className="glass p-4">
          <div className="tabular text-2xl font-bold text-accent-cyan">{fmt.format(totalPersonal)}</div>
          <div className="text-[11px] uppercase tracking-wider text-ink-mute">personal indexado</div>
        </div>
        <div className="glass p-4">
          <div className="tabular text-2xl font-bold text-peru-redsoft">{money(totalPlanilla)}</div>
          <div className="text-[11px] uppercase tracking-wider text-ink-mute">planilla mensual aprox.</div>
        </div>
        <div className="glass p-4">
          <div className="tabular text-2xl font-bold text-ink">{money(totalPlanilla * 12)}</div>
          <div className="text-[11px] uppercase tracking-wider text-ink-mute">≈ anual</div>
        </div>
      </div>

      <div className="mt-6 flex flex-wrap gap-2">
        {METRICS.map((m) => (
          <button
            key={m.key}
            onClick={() => setMetric(m.key)}
            className={`rounded-full border px-3 py-1.5 text-xs font-medium transition ${
              metric === m.key ? "border-accent-blue/50 bg-accent-blue/15 text-accent-blue" : "border-surface/10 bg-surface/[0.03] text-ink-soft hover:text-ink"
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      <div className="glass mt-5 p-5">
        {sorted.map((r) => (
          <div key={r.region} className="mb-3 last:mb-0">
            <div className="flex items-baseline justify-between text-sm">
              <span className="text-ink-soft">{r.region}</span>
              <span className="tabular font-semibold text-ink">{val(r)}</span>
            </div>
            <div className="mt-1.5 h-2.5 overflow-hidden rounded-full bg-surface/[0.06]">
              <div
                className="h-full rounded-full bg-gradient-to-r from-accent-blue to-accent-cyan transition-all duration-500"
                style={{ width: `${Math.max(2, (r[metric] / max) * 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      <div className="mt-5 glass p-5">
        <SectionTitle kicker="Cómo leerlo">Notas honestas</SectionTitle>
        <ul className="list-inside list-disc space-y-1 text-sm text-ink-soft">
          <li><b>Planilla ≠ presupuesto.</b> Es la suma de ingresos mensuales reportados en el PTE (aprox.), no el presupuesto total de la entidad.</li>
          <li><b>"Nacional (Lima)"</b> agrupa ministerios y organismos nacionales (sede en Lima) y entidades cuyo nombre no revela su región.</li>
          <li>La región se infiere del <b>nombre</b> de la entidad. Geocodificación precisa por ubigeo (INEI) está en el roadmap.</li>
        </ul>
      </div>
    </div>
  );
}
